from __future__ import annotations

import asyncio
import logging
import math
import time
from bisect import bisect_right
from collections.abc import Mapping
from typing import Any, Dict, List, Tuple

import orjson
from sqlalchemy import text

from celery_app.connections import rankings_async_session, redis_conn
from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_PERCENTILES_KEY,
    RIPPLE_STABLE_STATE_KEY,
)
from shared_lib.queries import ripple_queries

logger = logging.getLogger(__name__)

# Fetch the complete snapshot so the public cache can serve every stable row;
# pagination happens on the consumer side.
DEFAULT_LIMIT = None
DEFAULT_TOURNAMENT_WINDOW_DAYS = 120
SCORE_OFFSET = 0.0
SCORE_MULTIPLIER = 25.0
DISPLAY_OFFSET = 150.0
MS_PER_DAY = 86_400_000

GRADE_THRESHOLDS = [
    ("XB-", -5.0),
    ("XB", -4.0),
    ("XB+", -3.0),
    ("XA-", -2.0),
    ("XA", -1.0),
    ("XA+", 0.0),
    ("XS-", 0.8),
    ("XS", 1.5),
    ("XS+", 2.4),
    ("XX", 4.0),
    ("XX+", 5.0),
]

DEFAULT_PAGE_PARAMS = {
    "limit": DEFAULT_LIMIT,
    "offset": 0,
    "min_tournaments": 3,
    "tournament_window_days": DEFAULT_TOURNAMENT_WINDOW_DAYS,
    "ranked_only": True,
}

DEFAULT_DANGER_PARAMS = {
    "limit": None,
    "offset": 0,
    "min_tournaments": 3,
    "tournament_window_days": DEFAULT_TOURNAMENT_WINDOW_DAYS,
    "ranked_only": True,
}


def _display_score(score: float) -> float:
    return (score + SCORE_OFFSET) * SCORE_MULTIPLIER


def _grade_threshold_percentiles(
    stable_rows: List[Mapping[str, Any]]
) -> Tuple[List[Dict[str, Any]], int]:
    scores = sorted(
        float(row["stable_score"])
        for row in stable_rows
        if row.get("stable_score") is not None
    )
    total = len(scores)
    results: List[Dict[str, Any]] = []

    previous_threshold = float("-inf")
    for label, raw_ceiling in GRADE_THRESHOLDS:
        raw_floor = previous_threshold
        if total == 0:
            count_at_or_above = 0
        elif math.isfinite(raw_floor):
            idx = bisect_right(scores, raw_floor)
            count_at_or_above = total - idx
        else:
            count_at_or_above = total

        percentile = 0.0 if total == 0 else count_at_or_above / total

        results.append(
            {
                "label": label,
                "raw_floor": None
                if not math.isfinite(raw_floor)
                else round(raw_floor, 4),
                "raw_ceiling": round(raw_ceiling, 4),
                "display_floor": None
                if not math.isfinite(raw_floor)
                else round(raw_floor * SCORE_MULTIPLIER + DISPLAY_OFFSET, 2),
                "display_ceiling": round(
                    raw_ceiling * SCORE_MULTIPLIER + DISPLAY_OFFSET, 2
                ),
                "count": count_at_or_above,
                "percentile": round(percentile, 4),
            }
        )

        previous_threshold = raw_ceiling

    if total == 0:
        return results, total

    # Ensure percentiles are monotonically non-increasing even with rounding
    running_min = 1.0
    for entry in results:
        running_min = min(running_min, entry["percentile"])
        entry["percentile"] = running_min

    return results, total


def _now_ms() -> int:
    return int(time.time() * 1000)


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_state() -> Dict[str, Any]:
    payload = redis_conn.get(RIPPLE_STABLE_STATE_KEY)
    if not payload:
        return {}
    try:
        return orjson.loads(payload)
    except orjson.JSONDecodeError:
        logger.warning("Failed to parse ripple stable state; rebuilding")
        return {}


def _persist_state(state: Dict[str, Any]) -> None:
    # Keep player IDs as strings so reloads round-trip cleanly and remain
    # compatible with existing Redis payloads.
    serializable = {str(player_id): value for player_id, value in state.items()}
    redis_conn.set(RIPPLE_STABLE_STATE_KEY, orjson.dumps(serializable))


def _persist_payload(key: str, payload: Mapping[str, Any]) -> None:
    redis_conn.set(key, orjson.dumps(payload))


async def _fetch_player_events(
    session, player_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    if not player_ids:
        return {}

    schema = ripple_queries._schema()
    schema_sql = f'"{schema}"'

    # Use LEFT JOIN to ensure lifetime tournament_count is not undercounted
    # when a tournament is missing from the event-time MV. We still compute
    # latest_event_ms from available event times, but total tournaments are
    # counted across all appearances.
    query = text(
        f"""
        SELECT pat.player_id,
               MAX(tet.event_ms)::bigint AS latest_event_ms,
               COUNT(DISTINCT pat.tournament_id)::int AS tournament_count
        FROM {schema_sql}.player_appearance_teams pat
        LEFT JOIN {schema_sql}.tournament_event_times tet
          ON tet.tournament_id = pat.tournament_id
        WHERE pat.player_id = ANY(:player_ids)
        GROUP BY pat.player_id
        """
    )

    result = await session.execute(query, {"player_ids": player_ids})
    out: Dict[str, Dict[str, Any]] = {}
    for row in result.mappings():
        out[row["player_id"]] = {
            "latest_event_ms": _to_int(row["latest_event_ms"]),
            "tournament_count": _to_int(row["tournament_count"]),
        }
    return out


async def _first_score_after_event(
    session, player_id: str, event_ms: int
) -> float | None:
    schema = ripple_queries._schema()
    schema_sql = f'"{schema}"'

    query = text(
        f"""
        SELECT score
        FROM {schema_sql}.player_rankings
        WHERE player_id = :player_id
          AND calculated_at_ms >= :event_ms
        ORDER BY calculated_at_ms ASC
        LIMIT 1
        """
    )

    result = await session.execute(
        query, {"player_id": player_id, "event_ms": event_ms}
    )
    row = result.first()
    if not row:
        return None
    score = row[0]
    return None if score is None else float(score)


async def _bootstrap_state(
    session,
    rows: List[Mapping[str, Any]],
    events: Dict[str, Dict[str, Any]],
    now_ms: int,
) -> Dict[str, Any]:
    """Build the stable cache from scratch when Redis lacks history."""
    state: Dict[str, Any] = {}
    for row in rows:
        player_id = row.get("player_id")
        if not player_id:
            continue
        event_info = events.get(player_id, {})
        latest_event_ms = _to_int(event_info.get("latest_event_ms"))
        tournament_count = event_info.get("tournament_count")
        stable_score = None
        if latest_event_ms is not None:
            stable_score = await _first_score_after_event(
                session, player_id, latest_event_ms
            )
        if stable_score is None:
            score = row.get("score") or 0.0
            stable_score = float(score)
        state[player_id] = {
            "stable_score": stable_score,
            "last_tournament_ms": latest_event_ms,
            # Align last_active_ms to last_tournament_ms to prevent desyncs
            "last_active_ms": latest_event_ms,
            "tournament_count": tournament_count
            or _to_int(row.get("tournament_count")),
            "updated_at_ms": now_ms,
        }
    return state


def _merge_state(
    rows: List[Mapping[str, Any]],
    events: Dict[str, Dict[str, Any]],
    previous_state: Dict[str, Any],
    now_ms: int,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    new_state = dict(previous_state)
    stable_rows: List[Dict[str, Any]] = []

    for row in rows:
        player_id = row.get("player_id")
        if not player_id:
            continue
        score = float(row.get("score") or 0.0)
        display_name = row.get("display_name")
        event_info = events.get(player_id, {})
        latest_event_ms = _to_int(event_info.get("latest_event_ms"))
        tournament_count = event_info.get("tournament_count")
        if tournament_count is None:
            tournament_count = _to_int(row.get("tournament_count"))
        # We intentionally align last_active_ms with last_tournament_ms so that
        # the public snapshot displays a single coherent timestamp for both.
        last_active_ms = None  # will be set after last_tournament_ms determined

        existing = new_state.get(player_id, {})
        stable_score = existing.get("stable_score")
        last_tournament_ms = existing.get("last_tournament_ms")

        if latest_event_ms is not None and (
            last_tournament_ms is None or latest_event_ms > last_tournament_ms
        ):
            stable_score = score
            last_tournament_ms = latest_event_ms
        elif stable_score is None:
            stable_score = score
        if last_tournament_ms is None:
            last_tournament_ms = latest_event_ms

        # Finalize last_active_ms to match last_tournament_ms
        last_active_ms = last_tournament_ms

        new_state[player_id] = {
            "stable_score": stable_score,
            "last_tournament_ms": last_tournament_ms,
            "last_active_ms": last_active_ms,
            "tournament_count": tournament_count,
            "updated_at_ms": now_ms,
        }

        # Include 90d window count from the page row when available so the
        # public stable payload can show window counts even if a player does
        # not appear in the danger set.
        stable_rows.append(
            {
                "player_id": player_id,
                "display_name": display_name,
                "stable_score": stable_score,
                "display_score": _display_score(stable_score),
                "tournament_count": tournament_count,
                "window_tournament_count": _to_int(row.get("window_count")),
                "last_active_ms": last_active_ms,
                "last_tournament_ms": last_tournament_ms,
            }
        )

    stable_rows.sort(key=lambda r: (-r["stable_score"], r["player_id"]))
    for idx, row in enumerate(stable_rows, start=1):
        row["stable_rank"] = idx

    return stable_rows, new_state


def _serialize_danger(
    danger_rows: List[Mapping[str, Any]],
    stable_display_scores: Dict[str, float],
) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    for row in danger_rows:
        player_id = row.get("player_id")
        ms_left = row.get("ms_left")
        ms_left_value = float(ms_left) if ms_left is not None else None
        days_left = None
        if ms_left_value is not None:
            days_left = ms_left_value / MS_PER_DAY
        fallback_score = float(row.get("score") or 0.0)
        serialized.append(
            {
                "rank": _to_int(row.get("player_rank")),
                "player_id": player_id,
                "display_name": row.get("display_name"),
                "display_score": stable_display_scores.get(
                    player_id, _display_score(fallback_score)
                ),
                "window_tournament_count": _to_int(row.get("window_count")),
                "oldest_in_window_ms": _to_int(row.get("oldest_in_window_ms")),
                "next_expiry_ms": _to_int(row.get("next_expiry_ms")),
                "days_left": days_left,
            }
        )
    return serialized


async def _refresh_snapshots_async() -> Dict[str, Any]:
    generated_at_ms = _now_ms()
    rows: List[Mapping[str, Any]] = []
    total: Any = 0
    calc_ts: Any = None
    build_version: Any = None
    danger_rows: List[Dict[str, Any]] = []
    danger_total: Any = 0
    danger_calc_ts: Any = None
    danger_build: Any = None
    events: Dict[str, Dict[str, Any]] = {}
    state: Dict[str, Any] = {}
    try:
        async with rankings_async_session() as session:
            (
                rows,
                total,
                calc_ts,
                build_version,
            ) = await ripple_queries.fetch_ripple_page(
                session, **DEFAULT_PAGE_PARAMS
            )
            (
                danger_rows_raw,
                danger_total,
                danger_calc_ts,
                danger_build,
            ) = await ripple_queries.fetch_ripple_danger(
                session, **DEFAULT_DANGER_PARAMS
            )
            danger_rows = [dict(r) for r in danger_rows_raw]
            player_ids = [
                row.get("player_id") for row in rows if row.get("player_id")
            ]
            events = await _fetch_player_events(session, player_ids)

            state = _load_state()
            if not state:
                logger.info("Bootstrapping ripple stable state")
                state = await _bootstrap_state(
                    session, rows, events, generated_at_ms
                )
    finally:
        rankings_async_session.remove()

    calc_ts_int = _to_int(calc_ts)
    danger_calc_ts_int = _to_int(danger_calc_ts)
    stable_total = _to_int(total)
    danger_total_value = _to_int(danger_total)

    stable_rows, new_state = _merge_state(rows, events, state, generated_at_ms)
    display_map = {
        row["player_id"]: row["display_score"] for row in stable_rows
    }
    danger_payload = _serialize_danger(danger_rows, display_map)

    grade_percentiles, score_population = _grade_threshold_percentiles(
        stable_rows
    )

    stable_payload = {
        "build_version": build_version,
        "calculated_at_ms": calc_ts_int,
        "generated_at_ms": generated_at_ms,
        "query_params": dict(DEFAULT_PAGE_PARAMS),
        "record_count": len(stable_rows),
        "total": stable_total,
        "data": stable_rows,
    }
    danger_snapshot = {
        "build_version": danger_build or build_version,
        "calculated_at_ms": danger_calc_ts_int,
        "generated_at_ms": generated_at_ms,
        "query_params": dict(DEFAULT_DANGER_PARAMS),
        "record_count": len(danger_payload),
        "total": danger_total_value,
        "data": danger_payload,
    }
    meta_payload = {
        "generated_at_ms": generated_at_ms,
        "stable_calculated_at_ms": calc_ts_int,
        "stable_record_count": len(stable_rows),
        "danger_calculated_at_ms": danger_calc_ts_int,
        "danger_record_count": len(danger_payload),
        "build_version": build_version,
    }

    percentiles_payload = {
        "generated_at_ms": generated_at_ms,
        "record_count": len(stable_rows),
        "score_population": score_population,
        "grade_thresholds": grade_percentiles,
        "transform": {
            "score_offset": SCORE_OFFSET,
            "display_offset": DISPLAY_OFFSET,
            "multiplier": SCORE_MULTIPLIER,
        },
    }

    _persist_state(new_state)
    _persist_payload(RIPPLE_STABLE_LATEST_KEY, stable_payload)
    _persist_payload(RIPPLE_DANGER_LATEST_KEY, danger_snapshot)
    _persist_payload(RIPPLE_STABLE_META_KEY, meta_payload)
    _persist_payload(RIPPLE_STABLE_PERCENTILES_KEY, percentiles_payload)

    logger.info(
        "Refreshed ripple snapshots: %s stable rows, %s danger rows",
        len(stable_rows),
        len(danger_payload),
    )

    return {
        "stable_rows": len(stable_rows),
        "danger_rows": len(danger_payload),
    }


def refresh_ripple_snapshots() -> Dict[str, Any]:
    """Celery entrypoint to refresh cached ripple leaderboard snapshots."""
    return asyncio.run(_refresh_snapshots_async())
