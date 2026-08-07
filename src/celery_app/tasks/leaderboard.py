import logging
from time import perf_counter

import orjson
import pandas as pd
from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    SEASON_RESULTS_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
)
from shared_lib.monitoring import (
    DATA_PULL_DURATION,
    DATA_PULL_ROWS,
    metrics_enabled,
)
from shared_lib.queries.leaderboard_queries import (
    LIVE_WEAPON_LEADERBOARD_QUERY,
    SEASON_RESULTS_QUERY,
    WEAPON_LEADERBOARD_QUERY,
)
from shared_lib.queries.player_queries import fetch_current_season
from shared_lib.utils import get_all_alt_kits

logger = logging.getLogger(__name__)

FIRST_WEAPON_LEADERBOARD_SEASON = 1
idx_columns = ["player_id", "season_number", "mode", "region"]


def _empty_weapon_leaderboard() -> pd.DataFrame:
    return pd.DataFrame(
        columns=idx_columns
        + [
            "weapon_id",
            "max_x_power",
            "games_played",
            "percent_games_played",
        ]
    ).set_index(idx_columns)


def _aggregate_weapon_rows(
    rows: list[dict], alt_kits: dict[str, str]
) -> pd.DataFrame:
    if not rows:
        return _empty_weapon_leaderboard()

    weapon_leaderboard = pd.DataFrame(rows).set_index(idx_columns)
    weapon_ids = weapon_leaderboard["weapon_id"].astype(str)
    weapon_leaderboard["weapon_id"] = (
        weapon_ids.map(alt_kits).fillna(weapon_ids).astype(str)
    )

    total_games_df = (
        weapon_leaderboard.reset_index()
        .groupby(idx_columns)["games_played"]
        .sum()
        .rename("total_games_played")
    )
    weapon_leaderboard = weapon_leaderboard.merge(
        total_games_df, left_index=True, right_index=True, how="left"
    )
    weapon_leaderboard["percent_games_played"] = weapon_leaderboard[
        "games_played"
    ].div(weapon_leaderboard["total_games_played"])

    return (
        weapon_leaderboard.groupby(idx_columns + ["weapon_id"])
        .agg(
            {
                "max_x_power": "max",
                "games_played": "sum",
                "percent_games_played": "sum",
            }
        )
        .reset_index()
        .set_index(idx_columns)
    )


def _completed_seasons_to_derive(
    archived_seasons: set[int],
    current_season: int,
) -> list[int]:
    seasons = set(_archive_gap_seasons(archived_seasons, current_season))
    previous_season = current_season - 1
    if previous_season >= FIRST_WEAPON_LEADERBOARD_SEASON:
        # Rebuild the latest completed season during archive handoff so a
        # partially published archive cannot hide the remaining rows.
        seasons.add(previous_season)
    return sorted(seasons)


def _archive_gap_seasons(
    archived_seasons: set[int], current_season: int
) -> list[int]:
    return sorted(
        set(range(FIRST_WEAPON_LEADERBOARD_SEASON, current_season))
        - archived_seasons
    )


def _combine_weapon_leaderboards(
    weapon_leaderboards: list[pd.DataFrame],
) -> pd.DataFrame:
    populated = [frame for frame in weapon_leaderboards if not frame.empty]
    if not populated:
        return _empty_weapon_leaderboard()

    combined = pd.concat(populated).reset_index()
    combined["_weapon_id_key"] = combined["weapon_id"].astype(str)
    combined = combined.drop_duplicates(
        subset=idx_columns + ["_weapon_id_key"], keep="first"
    ).drop(columns="_weapon_id_key")
    return combined.set_index(idx_columns).sort_index()


def fetch_past_weapon_leaderboard_data() -> pd.DataFrame:
    """Fetches past weapon leaderboard data from the database.

    Returns:
        pd.DataFrame: A DataFrame of weapon leaderboard data.
    """
    logger.info("Fetching past weapon leaderboard data")
    query = text(WEAPON_LEADERBOARD_QUERY)
    start = perf_counter()
    with Session() as session:
        result = session.execute(query).fetchall()
        rows = [{**row._asdict()} for row in result]
        weapon_leaderboard = (
            pd.DataFrame(rows).set_index(idx_columns)
            if rows
            else _empty_weapon_leaderboard()
        )
    if metrics_enabled():
        DATA_PULL_DURATION.labels(
            task="celery.weapon_leaderboard.past"
        ).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(task="celery.weapon_leaderboard.past").set(
            len(weapon_leaderboard)
        )

    return weapon_leaderboard


def fetch_live_weapon_leaderboard_data(
    current_season: int | None = None,
    alt_kits: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Fetches live weapon leaderboard data from the database.

    Returns:
        pd.DataFrame: A DataFrame of weapon leaderboard data.
    """
    logger.info("Fetching live weapon leaderboard data")
    query = text(LIVE_WEAPON_LEADERBOARD_QUERY)
    start = perf_counter()
    if current_season is None:
        with Session() as session:
            current_season = fetch_current_season(session)
    if current_season is None:
        return _empty_weapon_leaderboard()
    with Session() as session:
        result = session.execute(
            query, {"season_number": current_season}
        ).fetchall()
        rows = [{**row._asdict()} for row in result]
    weapon_leaderboard = _aggregate_weapon_rows(
        rows, alt_kits if alt_kits is not None else get_all_alt_kits()
    )
    if metrics_enabled():
        DATA_PULL_DURATION.labels(
            task="celery.weapon_leaderboard.live"
        ).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(task="celery.weapon_leaderboard.live").set(
            len(weapon_leaderboard)
        )

    return weapon_leaderboard


def fetch_completed_weapon_leaderboard_fallback_data(
    archived_seasons: set[int],
    current_season: int | None,
    alt_kits: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Derive archive gaps and the latest completed rollover season."""
    if current_season is None:
        return _empty_weapon_leaderboard()

    logger.info("Checking completed weapon leaderboard fallback seasons")
    start = perf_counter()
    leaderboard_query = text(LIVE_WEAPON_LEADERBOARD_QUERY)
    fallback_seasons = _completed_seasons_to_derive(
        archived_seasons, current_season
    )
    with Session() as session:
        rows = []
        for season_number in fallback_seasons:
            season_rows = session.execute(
                leaderboard_query, {"season_number": season_number}
            ).fetchall()
            rows.extend({**row._asdict()} for row in season_rows)

    archive_gaps = _archive_gap_seasons(archived_seasons, current_season)
    if archive_gaps:
        logger.warning(
            "Deriving missing completed weapon leaderboard seasons: %s",
            ", ".join(str(season) for season in archive_gaps),
        )
    elif fallback_seasons:
        logger.info(
            "Rebuilding latest completed weapon leaderboard season: %s",
            fallback_seasons[-1],
        )
    weapon_leaderboard = _aggregate_weapon_rows(
        rows, alt_kits if alt_kits is not None else get_all_alt_kits()
    )
    if metrics_enabled():
        DATA_PULL_DURATION.labels(
            task="celery.weapon_leaderboard.completed_fallback"
        ).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(
            task="celery.weapon_leaderboard.completed_fallback"
        ).set(len(weapon_leaderboard))

    return weapon_leaderboard


def fetch_weapon_leaderboard() -> pd.DataFrame:
    logger.info("Fetching weapon data")
    start = perf_counter()
    past_weapon_leaderboard = fetch_past_weapon_leaderboard_data()
    archived_seasons = (
        set(
            past_weapon_leaderboard.reset_index()["season_number"]
            .dropna()
            .astype(int)
            .unique()
        )
        if not past_weapon_leaderboard.empty
        else set()
    )
    with Session() as session:
        current_season = fetch_current_season(session)
    alt_kits = get_all_alt_kits()
    completed_weapon_leaderboard_fallback = (
        fetch_completed_weapon_leaderboard_fallback_data(
            archived_seasons, current_season, alt_kits
        )
    )
    live_weapon_leaderboard = fetch_live_weapon_leaderboard_data(
        current_season, alt_kits
    )
    weapon_leaderboard = _combine_weapon_leaderboards(
        [
            past_weapon_leaderboard,
            completed_weapon_leaderboard_fallback,
            live_weapon_leaderboard,
        ]
    )
    del (
        past_weapon_leaderboard,
        completed_weapon_leaderboard_fallback,
        live_weapon_leaderboard,
    )

    redis_conn.set(
        WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
        orjson.dumps(
            weapon_leaderboard.reset_index().to_dict(orient="records")
        ),
    )
    if metrics_enabled():
        DATA_PULL_DURATION.labels(
            task="celery.weapon_leaderboard.fetch"
        ).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(task="celery.weapon_leaderboard.total").set(
            len(weapon_leaderboard)
        )


def fetch_season_results() -> pd.DataFrame:
    logger.info("Fetching season results")
    query = text(SEASON_RESULTS_QUERY)
    start = perf_counter()
    with Session() as session:
        result = session.execute(query).fetchall()
        season_results = pd.DataFrame([{**row._asdict()} for row in result])

    redis_conn.set(
        SEASON_RESULTS_REDIS_KEY,
        orjson.dumps(season_results.to_dict(orient="records")),
    )
    if metrics_enabled():
        DATA_PULL_DURATION.labels(task="celery.season_results.fetch").observe(
            perf_counter() - start
        )
        DATA_PULL_ROWS.labels(task="celery.season_results.fetch").set(
            len(season_results)
        )
