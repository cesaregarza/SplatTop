import logging
import math
from datetime import datetime, timezone
from time import perf_counter

import orjson
from sqlalchemy import text

from celery_app.connections import Session, redis_conn
from shared_lib.constants import (
    PLAYER_LATEST_REDIS_KEY,
    PLAYER_PUBSUB_CHANNEL,
)
from shared_lib.monitoring import (
    DATA_PULL_DURATION,
    DATA_PULL_ROWS,
    metrics_enabled,
)
from shared_lib.queries.player_queries import (
    PLAYER_DATA_QUERY,
    PLAYER_LATEST_DATA_QUERY,
    SEASON_RESULTS_QUERY,
)

logger = logging.getLogger(__name__)

PLAYER_CHUNK_VERSION = 2
PLAYER_FETCH_LOCK_TTL_SECONDS = 300
PLAYER_CACHE_TTL_SECONDS = 900
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


def publish_cached_player_chunks(
    player_id: str, cached_payload_raw: bytes | str, cache_key: str
) -> None:
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
        cached_payload_raw = redis_conn.get(cache_key)
        if cached_payload_raw is not None:
            logger.info("Data already exists in cache. Skipping fetch.")
            publish_cached_player_chunks(
                player_id, cached_payload_raw, cache_key
            )
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
                redis_conn.set(
                    cache_key,
                    orjson.dumps(merged_payload),
                    ex=PLAYER_CACHE_TTL_SECONDS,
                )

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

    return reduce_player_history_rows(result)


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
    if not player_data:
        return {
            "weapon_counts": [],
            "weapon_winrate": [],
            "aggregate_season_data": [],
        }

    weapon_counts: dict[tuple[str, int, int], int] = {}
    weapon_winrate: dict[tuple[str, int, int], dict[str, int]] = {}
    season_peaks: dict[tuple[int, str], float] = {}
    previous_updated_x_power: float | None = None

    for row in player_data:
        mode = row.get("mode")
        season_number = row.get("season_number")
        x_power = row.get("x_power")
        weapon_id = row.get("weapon_id")
        updated = bool(row.get("updated"))

        if (
            mode
            and isinstance(season_number, int)
            and _is_finite_number(x_power)
        ):
            season_key = (season_number, mode)
            current_peak = season_peaks.get(season_key)
            if current_peak is None or x_power > current_peak:
                season_peaks[season_key] = x_power

        if not (
            updated
            and mode
            and isinstance(season_number, int)
            and isinstance(weapon_id, int)
        ):
            continue

        weapon_key = (mode, weapon_id, season_number)
        weapon_counts[weapon_key] = weapon_counts.get(weapon_key, 0) + 1

        if _is_finite_number(x_power):
            if previous_updated_x_power is not None:
                x_power_diff = x_power - previous_updated_x_power
                if x_power_diff != 0:
                    winrate_entry = weapon_winrate.setdefault(
                        weapon_key, {"sum": 0, "total_count": 0}
                    )
                    winrate_entry["total_count"] += 1
                    if x_power_diff > 0:
                        winrate_entry["sum"] += 1
            previous_updated_x_power = x_power

    return {
        "weapon_counts": [
            {
                "mode": mode,
                "weapon_id": weapon_id,
                "season_number": season_number,
                "count": count,
            }
            for (mode, weapon_id, season_number), count in sorted(
                weapon_counts.items(),
                key=lambda item: (item[0][2], item[0][0], item[0][1]),
            )
        ],
        "weapon_winrate": [
            {
                "mode": mode,
                "weapon_id": weapon_id,
                "season_number": season_number,
                **stats,
            }
            for (mode, weapon_id, season_number), stats in sorted(
                weapon_winrate.items(),
                key=lambda item: (item[0][2], item[0][0], item[0][1]),
            )
        ],
        "aggregate_season_data": [
            {
                "season_number": season_number,
                "mode": mode,
                "peak_x_power": peak_x_power,
            }
            for (season_number, mode), peak_x_power in sorted(
                season_peaks.items(), key=lambda item: (item[0][0], item[0][1])
            )
        ],
    }


def _is_finite_number(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _get_observed_day_key(timestamp: str | None) -> str | None:
    if not isinstance(timestamp, str):
        return None

    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed.date().isoformat()


def reduce_player_history_rows(player_data: list[dict]) -> list[dict]:
    """Keeps only chart-relevant history rows to shrink websocket payloads.

    The player page needs:
    - all updated rows for weapon-count and winrate aggregates,
    - every x-power change to preserve chart shape,
    - one anchor per observed UTC day to preserve continuity,
    - first and last rows per mode/season to preserve season bounds.
    """
    if not player_data:
        return []

    previous_x_power_by_partition: dict[tuple[str | None, int | None], float] = {}
    keep_keys: set[str] = set()
    last_row_key_by_partition: dict[tuple[str | None, int | None], str] = {}
    last_row_key_by_observed_day: dict[
        tuple[str | None, int | None, str], str
    ] = {}

    for row in player_data:
        row_key = row.get("timestamp")
        if not isinstance(row_key, str):
            continue

        partition_key = (row.get("mode"), row.get("season_number"))
        observed_day_key = _get_observed_day_key(row_key)
        x_power = row.get("x_power")
        previous_x_power = previous_x_power_by_partition.get(partition_key)
        should_keep = bool(row.get("updated"))

        if partition_key not in previous_x_power_by_partition:
            should_keep = True
        elif _is_finite_number(x_power) and x_power != previous_x_power:
            should_keep = True

        if should_keep:
            keep_keys.add(row_key)

        if _is_finite_number(x_power):
            previous_x_power_by_partition[partition_key] = x_power
        else:
            previous_x_power_by_partition.setdefault(partition_key, x_power)

        last_row_key_by_partition[partition_key] = row_key
        if observed_day_key is not None:
            last_row_key_by_observed_day[
                (*partition_key, observed_day_key)
            ] = row_key

    keep_keys.update(last_row_key_by_partition.values())
    keep_keys.update(last_row_key_by_observed_day.values())

    reduced_rows = [
        row
        for row in player_data
        if isinstance(row.get("timestamp"), str)
        and row["timestamp"] in keep_keys
    ]

    logger.info(
        "Reduced player history rows from %s to %s",
        len(player_data),
        len(reduced_rows),
    )
    return reduced_rows


def pull_all_latest_data(player_id: str) -> list[dict]:
    """Pulls the latest leaderboard rows for a player from the database.

    Args:
        player_id (str): The ID of the player.

    Returns:
        list[dict]: A list of dictionaries containing the latest data.
    """
    base_query = text(PLAYER_LATEST_DATA_QUERY)
    start = perf_counter()
    with Session() as session:
        result = session.execute(
            base_query, {"player_id": player_id}
        ).fetchall()

    latest_rows = [{**row._asdict()} for row in result]
    if metrics_enabled():
        DATA_PULL_DURATION.labels(
            task="player_detail.fetch_latest_data"
        ).observe(perf_counter() - start)
        DATA_PULL_ROWS.labels(task="player_detail.fetch_latest_data").set(
            len(latest_rows)
        )

    return latest_rows
