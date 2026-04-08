import logging
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

PLAYER_CHUNK_VERSION = 2
PLAYER_FETCH_LOCK_TTL_SECONDS = 300
PLAYER_AGGREGATED_KEYS = (
    "weapon_counts",
    "weapon_winrate",
    "season_results",
    "aggregate_season_data",
    "latest_data",
)


def build_empty_player_payload() -> dict:
    return {
        "player_data": [],
        "aggregated_data": {key: [] for key in PLAYER_AGGREGATED_KEYS},
    }


def merge_player_payload(base_payload: dict, payload: dict | None) -> dict:
    if not payload:
        return base_payload

    if "player_data" in payload and payload["player_data"] is not None:
        base_payload["player_data"] = payload["player_data"]

    aggregated_payload = payload.get("aggregated_data") or {}
    for key in PLAYER_AGGREGATED_KEYS:
        if key in aggregated_payload and aggregated_payload[key] is not None:
            base_payload["aggregated_data"][key] = aggregated_payload[key]

    return base_payload


def build_snapshot_payload(
    season_data: list[dict], latest_data: list[dict]
) -> dict:
    return {
        "aggregated_data": {
            "season_results": season_data,
            "latest_data": latest_data,
        }
    }


def build_analysis_payload(player_data: list[dict]) -> dict:
    return {
        "player_data": player_data,
        "aggregated_data": aggregate_player_analysis(player_data),
    }


def publish_player_chunk(
    player_id: str,
    phase: str,
    payload: dict | None = None,
    *,
    cache_key: str | None = None,
) -> None:
    message = {
        "player_id": player_id,
        "type": "player_chunk",
        "version": PLAYER_CHUNK_VERSION,
        "phase": phase,
        "payload": payload or {},
    }
    if cache_key:
        message["key"] = cache_key
    redis_conn.publish(PLAYER_PUBSUB_CHANNEL, orjson.dumps(message))


def publish_cached_player_chunks(player_id: str, cache_key: str) -> None:
    cached_payload_raw = redis_conn.get(cache_key)
    if cached_payload_raw is None:
        return

    cached_payload = merge_player_payload(
        build_empty_player_payload(), orjson.loads(cached_payload_raw)
    )
    publish_player_chunk(
        player_id,
        "snapshot",
        build_snapshot_payload(
            cached_payload["aggregated_data"]["season_results"],
            cached_payload["aggregated_data"]["latest_data"],
        ),
    )
    publish_player_chunk(
        player_id,
        "analysis",
        {
            "player_data": cached_payload["player_data"],
            "aggregated_data": {
                "aggregate_season_data": cached_payload["aggregated_data"][
                    "aggregate_season_data"
                ],
                "weapon_counts": cached_payload["aggregated_data"][
                    "weapon_counts"
                ],
                "weapon_winrate": cached_payload["aggregated_data"][
                    "weapon_winrate"
                ],
            },
        },
    )
    publish_player_chunk(player_id, "complete", cache_key=cache_key)


def fetch_player_data(player_id: str) -> None:
    """Fetches player data and stores it in Redis.

    Args:
        player_id (str): The ID of the player.
    """
    logger.info("Running task: fetch_player_data for player_id: %s", player_id)
    task_signature = f"fetch_player_data:{player_id}"
    lock_acquired = redis_conn.set(
        task_signature,
        "true",
        nx=True,
        ex=PLAYER_FETCH_LOCK_TTL_SECONDS,
    )

    if not lock_acquired:
        logger.info("Task already running. Skipping.")
        return

    try:
        cache_key = f"{PLAYER_LATEST_REDIS_KEY}:{player_id}"

        if redis_conn.exists(cache_key):
            logger.info("Data already exists in cache. Skipping fetch.")
            publish_cached_player_chunks(player_id, cache_key)
        else:
            season_result = _fetch_season_data(player_id)
            latest_data = pull_all_latest_data(player_id)
            merged_payload = merge_player_payload(
                build_empty_player_payload(),
                build_snapshot_payload(season_result, latest_data),
            )
            publish_player_chunk(
                player_id,
                "snapshot",
                build_snapshot_payload(season_result, latest_data),
            )

            try:
                player_result = _fetch_player_data(player_id)
                analysis_payload = build_analysis_payload(player_result)
                merge_player_payload(merged_payload, analysis_payload)
                publish_player_chunk(
                    player_id, "analysis", analysis_payload
                )
            except Exception as e:
                logger.exception(
                    "Error building player analysis payload for player_id=%s",
                    player_id,
                )
                publish_player_chunk(
                    player_id,
                    "error",
                    {"message": str(e), "stage": "analysis"},
                )
            finally:
                redis_conn.set(cache_key, orjson.dumps(merged_payload), ex=60)

            publish_player_chunk(player_id, "complete", cache_key=cache_key)
    finally:
        try:
            redis_conn.delete(task_signature)
        except Exception as e:
            logger.error("Error deleting task signature: %s", e)
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


def aggregate_player_analysis(player_data: list[dict]) -> dict:
    """Aggregates history-driven player detail data from player snapshots."""
    logger.info("Aggregating player data")
    player_df = pd.DataFrame(player_data)
    return {
        "weapon_counts": aggregate_weapon_counts(player_df),
        "weapon_winrate": aggregate_weapon_winrate(player_df),
        "aggregate_season_data": aggregate_season_data(player_df),
    }


def aggregate_weapon_counts(player_df: pd.DataFrame) -> list[dict]:
    """Aggregates weapon counts from player data.

    Args:
        player_df (pd.DataFrame): DataFrame containing player data.

    Returns:
        list[dict]: A list of dictionaries with aggregated weapon counts.
    """
    if player_df.empty or "updated" not in player_df:
        return []
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
    if player_df.empty or "updated" not in player_df:
        return []
    out_df = player_df.query("updated")
    if out_df.empty:
        return []
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
    if player_df.empty or "season_number" not in player_df:
        return []
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
            leaderboard_data = redis_conn.get(redis_key)
            if not leaderboard_data:
                continue
            data.extend(orjson.loads(leaderboard_data))

    if not data:
        return []

    leaderboard_df = pd.DataFrame(data)
    if "player_id" not in leaderboard_df:
        return []

    return leaderboard_df.query(f"player_id == @player_id").to_dict(
        orient="records"
    )
