import logging

import orjson
import pandas as pd
from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    SEASON_RESULTS_REDIS_KEY,
    WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
)
from shared_lib.queries.leaderboard_queries import (
    LIVE_WEAPON_LEADERBOARD_QUERY,
    SEASON_RESULTS_QUERY,
    WEAPON_LEADERBOARD_QUERY,
)
from shared_lib.utils import get_all_alt_kits

logger = logging.getLogger(__name__)

idx_columns = ["player_id", "season_number", "mode", "region"]


def fetch_past_weapon_leaderboard_data() -> pd.DataFrame:
    """Fetches past weapon leaderboard data from the database.

    Returns:
        pd.DataFrame: A DataFrame of weapon leaderboard data.
    """
    logger.info("Fetching past weapon leaderboard data")
    query = text(WEAPON_LEADERBOARD_QUERY)
    with Session() as session:
        result = session.execute(query).fetchall()
        weapon_leaderboard = pd.DataFrame(
            [{**row._asdict()} for row in result]
        ).set_index(idx_columns)

    return weapon_leaderboard


def fetch_live_weapon_leaderboard_data() -> pd.DataFrame:
    """Fetches live weapon leaderboard data from the database.

    Returns:
        pd.DataFrame: A DataFrame of weapon leaderboard data.
    """
    logger.info("Fetching live weapon leaderboard data")
    query = text(LIVE_WEAPON_LEADERBOARD_QUERY)
    with Session() as session:
        result = session.execute(query).fetchall()
        weapon_leaderboard = pd.DataFrame(
            [{**row._asdict()} for row in result]
        ).set_index(idx_columns)

    weapon_leaderboard["weapon_id"] = (
        weapon_leaderboard["weapon_id"]
        .astype(str)
        .map(get_all_alt_kits())
        .fillna(weapon_leaderboard["weapon_id"])
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

    return weapon_leaderboard.drop(columns="total_games_played")


def fetch_weapon_leaderboard() -> pd.DataFrame:
    logger.info("Fetching weapon data")
    past_weapon_leaderboard = fetch_past_weapon_leaderboard_data()
    live_weapon_leaderboard = fetch_live_weapon_leaderboard_data()
    weapon_leaderboard = pd.concat(
        [past_weapon_leaderboard, live_weapon_leaderboard]
    ).sort_index()
    del past_weapon_leaderboard, live_weapon_leaderboard

    redis_conn.set(
        WEAPON_LEADERBOARD_PEAK_REDIS_KEY,
        orjson.dumps(
            weapon_leaderboard.reset_index().to_dict(orient="records")
        ),
    )


def fetch_season_results() -> pd.DataFrame:
    logger.info("Fetching season results")
    query = text(SEASON_RESULTS_QUERY)
    with Session() as session:
        result = session.execute(query).fetchall()
        season_results = pd.DataFrame([{**row._asdict()} for row in result])

    redis_conn.set(
        SEASON_RESULTS_REDIS_KEY,
        orjson.dumps(season_results.to_dict(orient="records")),
    )
