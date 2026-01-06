import logging
import threading
from time import perf_counter

import orjson
import pandas as pd
from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    MODES,
    PLAYER_LATEST_REDIS_KEY,
    PLAYER_PUBSUB_CHANNEL,
    REGIONS,
)
from shared_lib.monitoring import (
    DATA_PULL_DURATION,
    DATA_PULL_ROWS,
    metrics_enabled,
)
from shared_lib.queries.player_queries import (
    PLAYER_DATA_QUERY,
    SEASON_RESULTS_QUERY,
)

logger = logging.getLogger(__name__)

# Thread-safe tracking of in-progress tasks to prevent stale execution
# when Redis lock TTL expires before task completes
_in_progress: set[str] = set()
_in_progress_lock = threading.Lock()


def fetch_player_data(player_id: str) -> None:
    """Fetches player data and stores it in Redis.

    Args:
        player_id (str): The ID of the player.
    """
    logger.info("Running task: fetch_player_data for player_id: %s", player_id)
    task_signature = f"fetch_player_data:{player_id}"

    # Check local in-progress tracking first (handles stale Redis locks)
    with _in_progress_lock:
        if task_signature in _in_progress:
            logger.info("Task already running locally. Skipping.")
            return
        # Atomic lock acquisition with SETNX
        if not redis_conn.set(task_signature, "true", nx=True, ex=60):
            logger.info("Task already running. Skipping.")
            return
        _in_progress.add(task_signature)

    try:
        cache_key = f"{PLAYER_LATEST_REDIS_KEY}:{player_id}"

        if redis_conn.exists(cache_key):
            logger.info("Data already exists in cache. Skipping fetch.")
        else:
            player_result = _fetch_player_data(player_id)
            season_result = _fetch_season_data(player_id)
            result = {
                "player_data": player_result,
                "aggregated_data": aggregate_player_data(
                    player_result, season_result, player_id
                ),
            }
            redis_conn.set(cache_key, orjson.dumps(result), ex=60)

        # Publish the data to the player_data_channel
        redis_conn.publish(
            PLAYER_PUBSUB_CHANNEL,
            orjson.dumps(
                {"player_id": player_id, "key": cache_key, "type": "data"}
            ),
        )
    finally:
        # Always release locks, even on exception
        with _in_progress_lock:
            _in_progress.discard(task_signature)
        try:
            redis_conn.delete(task_signature)
        except Exception as e:
            logger.error(f"Error deleting task signature: {e}")
            logger.error("Probably expired before deletion. Proceeding.")


def _fetch_player_data(player_id: str) -> list[dict]:
    """Fetches player data from the database.

    Args:
        player_id (str): The ID of the player.

    Returns:
        list[dict]: A list of dictionaries containing player data.
    """
    base_query = text(PLAYER_DATA_QUERY)
    start = perf_counter()
    with Session() as session:
        result = session.execute(
            base_query, {"player_id": player_id}
        ).fetchall()

    result = [{**row._asdict()} for row in result]
    if metrics_enabled():
        DATA_PULL_DURATION.labels(
            task="player_detail.fetch_player_data"
        ).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(task="player_detail.fetch_player_data").set(
            len(result)
        )
    for player in result:
        player["timestamp"] = player["timestamp"].isoformat()
        player["rotation_start"] = player["rotation_start"].isoformat()

    return result


def _fetch_season_data(player_id: str) -> list[dict]:
    """Fetches season data for a player from the database.

    Args:
        player_id (str): The ID of the player.

    Returns:
        list[dict]: A list of dictionaries containing season data.
    """
    base_query = text(SEASON_RESULTS_QUERY)
    start = perf_counter()
    with Session() as session:
        result = session.execute(
            base_query, {"player_id": player_id}
        ).fetchall()

    result = [{**row._asdict()} for row in result]
    if metrics_enabled():
        DATA_PULL_DURATION.labels(
            task="player_detail.fetch_season_data"
        ).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(task="player_detail.fetch_season_data").set(
            len(result)
        )

    return result


def aggregate_player_data(
    player_data: list[dict], season_data: list[dict], player_id: str
) -> dict:
    """Aggregates player and season data.

    Args:
        player_data (list[dict]): List of player data dictionaries.
        season_data (list[dict]): List of season data dictionaries.
        player_id (str): The ID of the player.

    Returns:
        dict: A dictionary containing aggregated data.
    """
    logger.info("Aggregating player data")
    player_df = pd.DataFrame(player_data)
    weapon_counts = aggregate_weapon_counts(player_df)
    weapon_winrate = aggregate_weapon_winrate(player_df)
    agg_season_data = aggregate_season_data(player_df)
    latest_data = pull_all_latest_data(player_id)
    return {
        "weapon_counts": weapon_counts,
        "weapon_winrate": weapon_winrate,
        "season_results": season_data,
        "aggregate_season_data": agg_season_data,
        "latest_data": latest_data,
    }


def aggregate_weapon_counts(player_df: pd.DataFrame) -> list[dict]:
    """Aggregates weapon counts from player data.

    Args:
        player_df (pd.DataFrame): DataFrame containing player data.

    Returns:
        list[dict]: A list of dictionaries with aggregated weapon counts.
    """
    return (
        player_df.query("updated")
        .sort_values("timestamp", ascending=False)
        .groupby(["mode", "weapon_id", "season_number"])["rank"]
        .count()
        .reset_index()
        .rename(columns={"rank": "count"})
        .to_dict(orient="records")
    )


def aggregate_weapon_winrate(player_df: pd.DataFrame) -> list[dict]:
    """Aggregates weapon win rates from player data.

    Args:
        player_df (pd.DataFrame): DataFrame containing player data.

    Returns:
        list[dict]: A list of dictionaries with aggregated weapon win rates.
    """
    out_df = player_df.query("updated")
    out_df["x_power_diff"] = out_df["x_power"].diff()
    # It shouldn't ever happen but filter out any x_power_diff that are 0
    out_df = out_df.loc[out_df["x_power_diff"] != 0]
    out_df["win"] = out_df["x_power_diff"] > 0
    return (
        out_df.groupby(["mode", "weapon_id", "season_number"])["win"]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"win": "win_count", "count": "total_count"})
        .to_dict(orient="records")
    )


def aggregate_season_data(player_df: pd.DataFrame) -> list[dict]:
    """Aggregates season data from player data.

    Args:
        player_df (pd.DataFrame): DataFrame containing player data.

    Returns:
        list[dict]: A list of dictionaries with aggregated season data.
    """
    return (
        player_df.groupby(["season_number", "mode"])["x_power"]
        .max()
        .rename("peak_x_power")
        .reset_index()
        .to_dict(orient="records")
    )


def pull_all_latest_data(player_id: str) -> list[dict]:
    """Pulls the latest data for a player from Redis.

    Args:
        player_id (str): The ID of the player.

    Returns:
        list[dict]: A list of dictionaries containing the latest data.
    """
    data = []
    for region in REGIONS:
        for mode in MODES:
            redis_key = f"leaderboard_data:{mode}:{region}"
            data.extend(orjson.loads(redis_conn.get(redis_key)))

    return (
        pd.DataFrame(data)
        .query(f"player_id == @player_id")
        .to_dict(orient="records")
    )
