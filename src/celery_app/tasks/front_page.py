import logging

import numpy as np
import orjson
import pandas as pd
from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    ALIASES_REDIS_KEY,
    MODES,
    MODES_SNAKE_CASE,
    REGIONS,
)
from shared_lib.queries.front_page_queries import LEADERBOARD_MAIN_QUERY
from shared_lib.utils import get_badge_image, get_banner_image, get_weapon_image

logger = logging.getLogger(__name__)


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
    with Session() as session:
        result = session.execute(
            query, {"mode": mode, "region": region_bool}
        ).fetchall()
        players = [{**row._asdict()} for row in result]

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
    redis_conn.set(redis_key, orjson.dumps(players))
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
    keys_to_keep = ["player_id", "x_power", "weapon_id", "mode", "region"]
    df = df.loc[:, keys_to_keep]
    out = []
    for region in REGIONS:
        logger.info(f"Processing data for region: {region}")
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
    dfs = []
    for mode in MODES:
        for region in REGIONS:
            region_bool = region == "Takoroka"
            players = fetch_and_store_leaderboard_data(mode, region_bool)
            df = pd.DataFrame(players)
            df["mode"] = mode
            df["region"] = region
            dfs.append(df)

    for region, processed_df in process_all_data(pd.concat(dfs)):
        redis_key = f"leaderboard_data:All Modes:{region}"
        redis_conn.set(
            redis_key, processed_df.reset_index().to_json(orient="records")
        )
        logger.info(f"All data for region: {region} saved to Redis")
