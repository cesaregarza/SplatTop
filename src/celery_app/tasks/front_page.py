import logging
from time import perf_counter

import numpy as np
import orjson
import pandas as pd
from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    MODES,
    MODES_SNAKE_CASE,
    RACE_TO_5000_REDIS_KEY,
    REGIONS,
)
from shared_lib.monitoring import (
    DATA_PULL_DURATION,
    DATA_PULL_ROWS,
    metrics_enabled,
)
from shared_lib.queries.front_page_queries import (
    LEADERBOARD_MAIN_QUERY,
    RACE_TO_5000_CURRENT_QUERY,
    RACE_TO_5000_HISTORICAL_QUERY,
)
from shared_lib.queries.player_queries import CURRENT_SEASON_QUERY
from shared_lib.utils import get_badge_image, get_banner_image, get_weapon_image

logger = logging.getLogger(__name__)

RACE_CURRENT_THRESHOLD = 4000
RACE_HISTORICAL_THRESHOLD = 5000
RACE_RUN_INDEX = ["player_id", "season_number", "mode", "region"]


def _format_region_label(region_value: bool) -> str:
    return "Takoroka" if bool(region_value) else "Tentatek"


def _players_to_columnar(players: list[dict]) -> dict[str, list]:
    out: dict[str, list] = {}
    for player in players:
        for key, value in player.items():
            out.setdefault(key, []).append(value)
    return out


def _serialize_leaderboard_payload(players: list[dict]) -> bytes:
    return orjson.dumps({"players": _players_to_columnar(players)})


def _fetch_current_season() -> int | None:
    query = text(CURRENT_SEASON_QUERY)
    with Session() as session:
        season_number = session.execute(query).scalar_one_or_none()
    return int(season_number) if season_number is not None else None


def _serialize_race_run(group: pd.DataFrame) -> dict:
    sorted_group = group.sort_values("timestamp")
    latest_row = sorted_group.iloc[-1]
    peak_row = sorted_group.loc[sorted_group["x_power"].idxmax()]
    return {
        "run_id": ":".join(
            [
                str(latest_row["player_id"]),
                str(latest_row["season_number"]),
                str(latest_row["mode"]),
                "1" if bool(latest_row["region"]) else "0",
            ]
        ),
        "player_id": latest_row["player_id"],
        "splashtag": latest_row["splashtag"],
        "season_number": int(latest_row["season_number"]),
        "mode": latest_row["mode"],
        "region": _format_region_label(latest_row["region"]),
        "current_x_power": float(latest_row["x_power"]),
        "current_rank": int(latest_row["rank"]),
        "peak_x_power": float(peak_row["x_power"]),
        "peak_rank": int(peak_row["rank"]),
        "last_updated": latest_row["timestamp"].isoformat(),
        "points": [
            {
                "timestamp": row.timestamp.isoformat(),
                "x_power": float(row.x_power),
            }
            for row in sorted_group.itertuples()
        ],
    }


def build_race_to_5000_payload(
    current_runs_df: pd.DataFrame,
    historical_runs_df: pd.DataFrame,
    *,
    current_season: int | None = None,
) -> dict:
    def serialize_runs(frame: pd.DataFrame) -> list[dict]:
        if frame.empty:
            return []

        runs = [
            _serialize_race_run(group)
            for _, group in frame.groupby(RACE_RUN_INDEX, sort=False)
        ]
        return sorted(
            runs,
            key=lambda run: (run["peak_x_power"], run["last_updated"]),
            reverse=True,
        )

    current_runs = [
        run
        for run in serialize_runs(current_runs_df)
        if run["current_x_power"] >= RACE_CURRENT_THRESHOLD
    ]
    historical_runs = serialize_runs(historical_runs_df)
    detected_current_season = (
        int(current_runs_df["season_number"].max())
        if not current_runs_df.empty
        else None
    )

    return {
        "current_season": (
            detected_current_season
            if detected_current_season is not None
            else current_season
        ),
        "current_threshold": RACE_CURRENT_THRESHOLD,
        "historical_threshold": RACE_HISTORICAL_THRESHOLD,
        "current_runs": current_runs,
        "historical_runs": historical_runs,
        "updated_at": (
            max(run["last_updated"] for run in current_runs)
            if current_runs
            else None
        ),
    }


def fetch_race_to_5000_rows(
    query_text: str, threshold: int, season_number: int
) -> pd.DataFrame:
    query = text(query_text)
    with Session() as session:
        result = session.execute(
            query,
            {"threshold": threshold, "season_number": season_number},
        ).fetchall()

    rows = [{**row._asdict()} for row in result]
    if not rows:
        return pd.DataFrame(
            columns=[
                "player_id",
                "splashtag",
                "rank",
                "x_power",
                "timestamp",
                "mode",
                "region",
                "season_number",
            ]
        )

    return pd.DataFrame(rows)


def fetch_and_store_leaderboard_data(mode: str, region_bool: bool) -> list:
    """Fetches leaderboard data from the database and stores it in Redis.

    Args:
        mode (str): The game mode.
        region_bool (bool): Boolean indicating the region (True for 'Takoroka',
            False for 'Tentatek').

    Returns:
        list: A list of player data dictionaries.
    """
    logger.info(
        "Fetching leaderboard data for mode: %s, region: %s",
        mode,
        "Takoroka" if region_bool else "Tentatek",
    )
    query = text(LEADERBOARD_MAIN_QUERY)
    start = perf_counter()
    with Session() as session:
        result = session.execute(
            query, {"mode": mode, "region": region_bool}
        ).fetchall()
        players = [{**row._asdict()} for row in result]
    if metrics_enabled():
        label = f"front_page.fetch_leaderboard:{mode}:{int(region_bool)}"
        DATA_PULL_DURATION.labels(task=label).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(task=label).set(len(players))

    for player in players:
        player["weapon_image"] = get_weapon_image(int(player["weapon_id"]))
        player["badge_left_image"] = get_badge_image(player["badge_left_id"])
        player["badge_center_image"] = get_badge_image(
            player["badge_center_id"]
        )
        player["badge_right_image"] = get_badge_image(player["badge_right_id"])
        player["nameplate_image"] = get_banner_image(
            int(player["nameplate_id"])
        )
        player["timestamp"] = player["timestamp"].isoformat()
        player["rotation_start"] = player["rotation_start"].isoformat()

    # Save to Redis with a key that combines mode and region for uniqueness
    redis_key = (
        f"leaderboard_data:{mode}:{'Takoroka' if region_bool else 'Tentatek'}"
    )
    redis_conn.set(redis_key, _serialize_leaderboard_payload(players))
    logger.info(
        "Leaderboard data for mode: %s, region: %s saved to Redis",
        mode,
        "Takoroka" if region_bool else "Tentatek",
    )
    return players


def process_all_data(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Processes all data by filtering and aggregating it for each region.

    Args:
        df (pd.DataFrame): The input DataFrame containing player data.

    Returns:
        list[tuple[str, pd.DataFrame]]: A list of tuples, each containing a
        region and its processed DataFrame.
    """
    logger.info("Processing all data")
    start = perf_counter()
    keys_to_keep = ["player_id", "x_power", "weapon_id", "mode", "region"]
    df = df.loc[:, keys_to_keep]
    out = []
    for region in REGIONS:
        logger.info("Processing data for region: %s", region)
        region_df = df.loc[df["region"] == region]
        region_df = process_region_data(region_df)
        for mode in MODES_SNAKE_CASE.values():
            key = f"{mode}_weapon_image"
            weapon_key = f"{mode}_weapon_id"
            weapon_mask = region_df[weapon_key].notnull()
            region_df[key] = ""
            region_df.loc[weapon_mask, key] = (
                region_df.loc[weapon_mask, weapon_key]
                .astype(int)
                .apply(get_weapon_image)
            )
        out.append((region, region_df))
        if metrics_enabled():
            DATA_PULL_ROWS.labels(
                task=f"front_page.process_region:{region}"
            ).set(len(region_df))
    if metrics_enabled():
        DATA_PULL_DURATION.labels(task="front_page.process_all").observe(
            perf_counter() - start
        )
    return out


def process_region_data(df: pd.DataFrame) -> pd.DataFrame:
    """Processes data for a specific region by aggregating and sorting it.

    Args:
        df (pd.DataFrame): The input DataFrame containing player data for a
            specific region.

    Returns:
        pd.DataFrame: The processed DataFrame with aggregated and sorted data.
    """
    logger.info("Processing region data")
    df.loc[:, "mode"] = df["mode"].map(MODES_SNAKE_CASE)

    df = df.set_index(["player_id", "mode"]).unstack()
    df.columns = [f"{mode}_{column}" for column, mode in df.columns]
    xp_cols = [col for col in df.columns if "x_power" in col]
    df["total_x_power"] = df[xp_cols].sum(axis=1)
    df = df.sort_values("total_x_power", ascending=False).iloc[:500]
    df["rank"] = np.arange(1, 501)

    # pull from ALIASES_REDIS_KEY and get the latest alias
    # for each player in the top 500
    aliases = redis_conn.get(ALIASES_REDIS_KEY)
    aliases = orjson.loads(aliases)
    aliases_df = pd.DataFrame(aliases)
    aliases_df = (
        aliases_df.sort_values("last_seen", ascending=False)
        .drop_duplicates(subset="player_id")
        .set_index("player_id")
        .drop(columns=["last_seen"])
    )
    df = df.join(aliases_df)
    logger.info("Region data processed")
    return df


def pull_data() -> None:
    """Pulls data for all modes and regions, processes it, and stores it in
    Redis.
    """
    logger.info("Pulling data")
    pull_start = perf_counter()
    dfs = []
    for mode in MODES:
        for region in REGIONS:
            region_bool = region == "Takoroka"
            players = fetch_and_store_leaderboard_data(mode, region_bool)
            df = pd.DataFrame(players)
            df["mode"] = mode
            df["region"] = region
            dfs.append(df)

    if metrics_enabled():
        total_raw_rows = sum(len(df) for df in dfs)
        DATA_PULL_ROWS.labels(task="front_page.pull_data:raw_rows").set(
            total_raw_rows
        )

    for region, processed_df in process_all_data(pd.concat(dfs)):
        redis_key = f"leaderboard_data:All Modes:{region}"
        records_json = processed_df.reset_index().to_json(orient="records")
        all_modes_players = orjson.loads(records_json.encode())
        redis_conn.set(
            redis_key,
            _serialize_leaderboard_payload(all_modes_players),
        )
        logger.info("All data for region: %s saved to Redis", region)
        if metrics_enabled():
            DATA_PULL_ROWS.labels(
                task=f"front_page.leaderboard_payload:{region}"
            ).set(len(processed_df))
    if metrics_enabled():
        DATA_PULL_DURATION.labels(task="front_page.pull_data").observe(
            perf_counter() - pull_start
        )


def fetch_race_to_5000() -> None:
    logger.info("Fetching race-to-5000 data")
    start = perf_counter()
    current_season = _fetch_current_season()
    if current_season is None:
        payload = build_race_to_5000_payload(
            pd.DataFrame(),
            pd.DataFrame(),
        )
        redis_conn.set(RACE_TO_5000_REDIS_KEY, orjson.dumps(payload))
        if metrics_enabled():
            DATA_PULL_DURATION.labels(task="front_page.race_to_5000").observe(
                perf_counter() - start
            )
            DATA_PULL_ROWS.labels(task="front_page.race_to_5000.current").set(
                0
            )
            DATA_PULL_ROWS.labels(
                task="front_page.race_to_5000.historical"
            ).set(0)
        return
    current_runs_df = fetch_race_to_5000_rows(
        RACE_TO_5000_CURRENT_QUERY,
        RACE_CURRENT_THRESHOLD,
        current_season,
    )
    historical_runs_df = fetch_race_to_5000_rows(
        RACE_TO_5000_HISTORICAL_QUERY,
        RACE_HISTORICAL_THRESHOLD,
        current_season,
    )
    payload = build_race_to_5000_payload(
        current_runs_df,
        historical_runs_df,
        current_season=current_season,
    )
    redis_conn.set(RACE_TO_5000_REDIS_KEY, orjson.dumps(payload))
    if metrics_enabled():
        DATA_PULL_DURATION.labels(task="front_page.race_to_5000").observe(
            perf_counter() - start
        )
        DATA_PULL_ROWS.labels(task="front_page.race_to_5000.current").set(
            len(payload["current_runs"])
        )
        DATA_PULL_ROWS.labels(
            task="front_page.race_to_5000.historical"
        ).set(len(payload["historical_runs"]))
