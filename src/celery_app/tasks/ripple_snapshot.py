from __future__ import annotations

import asyncio
import logging
import math
import time
from bisect import bisect_right
from collections.abc import Mapping
from typing import Any, Dict, List, Tuple
from uuid import uuid4

import orjson
from sqlalchemy import BigInteger, bindparam, text

from celery_app.connections import rankings_async_session, redis_conn
from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_SNAPSHOT_LOCK_KEY,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_PERCENTILES_KEY,
    RIPPLE_STABLE_STATE_KEY,
)
from shared_lib.queries import ripple_queries

logger = logging.getLogger(__name__)


LOCK_TTL_SECONDS = 15 * 60

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


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _persist_state(state: Dict[str, Any]) -> None:
    # Keep player IDs as strings so reloads round-trip cleanly and remain
    # compatible with existing Redis payloads.
    serializable = {str(player_id): value for player_id, value in state.items()}
    redis_conn.set(RIPPLE_STABLE_STATE_KEY, orjson.dumps(serializable))


def _persist_payload(key: str, payload: Mapping[str, Any]) -> None:
    redis_conn.set(key, orjson.dumps(payload))


def _load_previous_stable_payload() -> Dict[str, Any] | None:
    raw = redis_conn.get(RIPPLE_STABLE_LATEST_KEY)
    if not raw:
        return None
    try:
        return orjson.loads(raw)
    except orjson.JSONDecodeError:
        logger.warning(
            "Failed to parse previous ripple stable payload; skipping deltas"
        )
        return None


async def _previous_calculated_at_ms(
    session,
    current_ts: int | None,
) -> int | None:
    schema = ripple_queries._schema()
    schema_sql = f'"{schema}"'

    if current_ts is not None:
        query = text(
            f"""
            SELECT MAX(calculated_at_ms)::bigint AS ts
            FROM {schema_sql}.player_rankings
            WHERE calculated_at_ms < :current_ts
            """
        )
        params = {"current_ts": int(current_ts)}
    else:
        query = text(
            f"""
            SELECT NULLIF((SELECT MAX(calculated_at_ms) FROM {schema_sql}.player_rankings), NULL)::bigint AS ts
            """
        )
        params: Dict[str, Any] = {}

    result = await session.execute(query, params)
    value = result.scalar()
    return None if value is None else int(value)


async def _latest_calculated_at_at_or_before(
    session,
    cutoff_ms: int | None,
) -> int | None:
    if cutoff_ms is None:
        return None

    schema = ripple_queries._schema()
    schema_sql = f'"{schema}"'

    query = text(
        f"""
        SELECT MAX(calculated_at_ms)::bigint AS ts
        FROM {schema_sql}.player_rankings
        WHERE calculated_at_ms <= :cutoff
        """
    )
    result = await session.execute(query, {"cutoff": int(cutoff_ms)})
    value = result.scalar()
    return None if value is None else int(value)


async def _load_baseline_snapshot_from_db(
    session,
    *,
    current_calc_ts: int | None,
    baseline_ts: int | None = None,
) -> Dict[str, Any] | None:
    if baseline_ts is None:
        baseline_ts = await _previous_calculated_at_ms(session, current_calc_ts)
    if baseline_ts is None:
        return None

    (
        rows,
        total,
        calc_ts,
        build_version,
    ) = await ripple_queries.fetch_ripple_page(
        session,
        **DEFAULT_PAGE_PARAMS,
        ts_ms=baseline_ts,
    )

    if not rows:
        return None

    player_ids = [
        str(row.get("player_id")) for row in rows if row.get("player_id")
    ]
    events = await _fetch_player_events(session, player_ids)
    players_with_events = {
        player_id: ms
        for player_id, info in events.items()
        if (ms := _to_int(info.get("latest_event_ms"))) is not None
        and (baseline_ts is None or ms <= baseline_ts)
    }
    event_scores = await _first_scores_after_events(
        session, players_with_events, cutoff_ms=baseline_ts
    )

    stable_rows: List[Dict[str, Any]] = []
    for row in rows:
        player_id = row.get("player_id")
        if player_id is None:
            continue
        player_key = str(player_id)
        event_info = events.get(player_key, {})
        latest_event_ms = _to_int(event_info.get("latest_event_ms"))
        score = event_scores.get(player_key)
        if score is None:
            score = float(row.get("score") or 0.0)
        else:
            score = float(score)
        stable_rows.append(
            {
                "player_id": player_key,
                "display_name": row.get("display_name"),
                "stable_score": score,
                "display_score": _display_score(score),
                "tournament_count": _to_int(row.get("tournament_count")),
                "window_tournament_count": _to_int(row.get("window_count")),
                "last_active_ms": latest_event_ms
                if latest_event_ms is not None
                else _to_int(row.get("last_active_ms")),
                "last_tournament_ms": latest_event_ms
                if latest_event_ms is not None
                else _to_int(row.get("last_active_ms")),
                "stable_rank": _to_int(row.get("rank")),
            }
        )

    stable_rows.sort(key=lambda r: (-float(r["stable_score"]), r["player_id"]))
    for idx, entry in enumerate(stable_rows, start=1):
        entry["stable_rank"] = idx

    return {
        "build_version": build_version,
        "calculated_at_ms": _to_int(calc_ts),
        "generated_at_ms": baseline_ts,
        "query_params": dict(DEFAULT_PAGE_PARAMS) | {"ts_ms": baseline_ts},
        "record_count": len(stable_rows),
        "total": _to_int(total),
        "data": stable_rows,
    }


def _compute_delta_payload(
    stable_rows: List[Dict[str, Any]],
    previous_payload: Dict[str, Any] | None,
    generated_at_ms: int,
) -> Dict[str, Any]:
    baseline_generated_at_ms = None
    if previous_payload:
        baseline_generated_at_ms = _to_int(
            previous_payload.get("generated_at_ms")
        )

    if not previous_payload or not isinstance(
        previous_payload.get("data"), list
    ):
        return {
            "generated_at_ms": generated_at_ms,
            "baseline_generated_at_ms": baseline_generated_at_ms,
            "record_count": 0,
            "comparison_count": 0,
            "players": {},
            "newcomers": [],
            "dropouts": [],
        }

    previous_index: Dict[str, Dict[str, Any]] = {}
    for entry in previous_payload.get("data", []):
        player_id = entry.get("player_id")
        if player_id is None:
            continue
        player_key = str(player_id)
        previous_index[player_key] = {
            "rank": _to_int(entry.get("stable_rank")),
            "stable_score": _to_float(entry.get("stable_score")),
            "display_score": _to_float(entry.get("display_score")),
        }

    player_deltas: Dict[str, Dict[str, Any]] = {}
    newcomers: List[str] = []
    remaining_previous = set(previous_index.keys())

    for row in stable_rows:
        player_id = row.get("player_id")
        if not player_id:
            continue
        player_key = str(player_id)

        previous = previous_index.get(player_key)
        current_score_value = _to_float(row.get("stable_score"))
        current_rank = _to_int(row.get("stable_rank"))

        rank_delta = None
        previous_rank = None
        previous_score_value: float | None = None
        previous_display_score_value: float | None = None
        is_new = False

        if previous:
            previous_rank = previous.get("rank")
            previous_score_value = previous.get("stable_score")
            previous_display_score_value = previous.get("display_score")
            if previous_rank is not None and current_rank is not None:
                rank_delta = previous_rank - current_rank
            remaining_previous.discard(player_key)
        else:
            is_new = True
            newcomers.append(player_key)

        score_delta = None
        display_score_delta = None
        if current_score_value is not None and previous_score_value is not None:
            score_delta = current_score_value - previous_score_value
            display_score_delta = _display_score(
                current_score_value
            ) - _display_score(previous_score_value)
        elif (
            current_score_value is not None
            and previous_display_score_value is not None
        ):
            display_score_delta = (
                _display_score(current_score_value)
                - previous_display_score_value
            )

        player_deltas[player_key] = {
            "rank_delta": rank_delta,
            "score_delta": score_delta,
            "display_score_delta": display_score_delta,
            "previous_rank": previous_rank,
            "previous_score": previous_score_value,
            "previous_display_score": previous_display_score_value,
            "is_new": is_new,
        }

    dropouts: List[Dict[str, Any]] = []
    for player_key in remaining_previous:
        previous = previous_index[player_key]
        dropouts.append(
            {
                "player_id": player_key,
                "previous_rank": previous.get("rank"),
                "previous_score": previous.get("stable_score"),
                "previous_display_score": previous.get("display_score"),
            }
        )

    return {
        "generated_at_ms": generated_at_ms,
        "baseline_generated_at_ms": baseline_generated_at_ms,
        "record_count": len(player_deltas),
        "comparison_count": len(previous_index),
        "players": player_deltas,
        "newcomers": newcomers,
        "dropouts": dropouts,
    }


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
        SELECT pat.player_id::text AS player_id,
               MAX(tet.event_ms)::bigint AS latest_event_ms,
               COUNT(DISTINCT pat.tournament_id)::int AS tournament_count
        FROM {schema_sql}.player_appearance_teams pat
        LEFT JOIN {schema_sql}.tournament_event_times tet
          ON tet.tournament_id = pat.tournament_id
        WHERE pat.player_id::text = ANY(:player_ids)
        GROUP BY pat.player_id
        """
    )

    result = await session.execute(query, {"player_ids": player_ids})
    out: Dict[str, Dict[str, Any]] = {}
    for row in result.mappings():
        player_id = str(row["player_id"])
        out[player_id] = {
            "latest_event_ms": _to_int(row["latest_event_ms"]),
            "tournament_count": _to_int(row["tournament_count"]),
        }
    return out


async def _first_scores_after_events(
    session,
    player_events: Dict[str, int],
    *,
    cutoff_ms: int | None = None,
) -> Dict[str, float]:
    if not player_events:
        return {}

    schema = ripple_queries._schema()
    schema_sql = f'"{schema}"'

    player_ids = list(player_events.keys())
    event_ms = [int(player_events[player_id]) for player_id in player_ids]

    query = text(
        f"""
        WITH params AS (
            SELECT player_id, event_ms
            FROM UNNEST(CAST(:player_ids AS text[]), CAST(:event_ms AS bigint[]))
                AS t(player_id, event_ms)
        )
        SELECT DISTINCT ON (pr.player_id)
               pr.player_id::text AS player_id,
               pr.score
        FROM params p
        JOIN {schema_sql}.player_rankings pr
          ON pr.player_id::text = p.player_id
         AND pr.calculated_at_ms >= p.event_ms
         AND (:cutoff_ms IS NULL OR pr.calculated_at_ms <= :cutoff_ms)
        ORDER BY pr.player_id, pr.calculated_at_ms
        """
    ).bindparams(bindparam("cutoff_ms", type_=BigInteger))

    result = await session.execute(
        query,
        {
            "player_ids": player_ids,
            "event_ms": event_ms,
            "cutoff_ms": None if cutoff_ms is None else int(cutoff_ms),
        },
    )

    out: Dict[str, float] = {}
    for row in result.mappings():
        score = row.get("score")
        if score is not None:
            out[str(row["player_id"])] = float(score)
    return out


async def _bootstrap_state(
    session,
    rows: List[Mapping[str, Any]],
    events: Dict[str, Dict[str, Any]],
    now_ms: int,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Rebuild the stable state and rows from scratch."""
    state: Dict[str, Any] = {}
    stable_rows: List[Dict[str, Any]] = []

    players_with_events = {
        player_id: info["latest_event_ms"]
        for player_id, info in events.items()
        if info.get("latest_event_ms") is not None
    }
    event_scores = await _first_scores_after_events(
        session, players_with_events
    )

    for row in rows:
        player_id = row.get("player_id")
        if not player_id:
            continue
        player_key = str(player_id)
        event_info = events.get(player_key, {})
        latest_event_ms = _to_int(event_info.get("latest_event_ms"))
        tournament_count = event_info.get("tournament_count")
        if tournament_count is None:
            tournament_count = _to_int(row.get("tournament_count"))
        stable_score = event_scores.get(player_key)
        if stable_score is None:
            score = row.get("score") or 0.0
            stable_score = float(score)
        else:
            stable_score = float(stable_score)

        last_ms = latest_event_ms
        if last_ms is None:
            last_ms = _to_int(row.get("last_active_ms"))

        state[player_key] = {
            "stable_score": stable_score,
            "last_tournament_ms": latest_event_ms,
            "last_active_ms": last_ms,
            "tournament_count": tournament_count,
            "updated_at_ms": now_ms,
            "recent_score_delta": None,
            "recent_score_delta_ms": None,
        }

        stable_rows.append(
            {
                "player_id": player_key,
                "display_name": row.get("display_name"),
                "stable_score": stable_score,
                "display_score": _display_score(stable_score),
                "tournament_count": tournament_count,
                "window_tournament_count": _to_int(row.get("window_count")),
                "last_active_ms": last_ms,
                "last_tournament_ms": latest_event_ms
                if latest_event_ms is not None
                else last_ms,
            }
        )

    stable_rows.sort(key=lambda r: (-float(r["stable_score"]), r["player_id"]))
    for idx, entry in enumerate(stable_rows, start=1):
        entry["stable_rank"] = idx

    return state, stable_rows


def _serialize_danger(
    danger_rows: List[Mapping[str, Any]],
    stable_display_scores: Dict[str, float],
) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    for row in danger_rows:
        raw_player_id = row.get("player_id")
        player_id = None if raw_player_id is None else str(raw_player_id)
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
    stable_rows: List[Dict[str, Any]] = []
    previous_stable_payload = _load_previous_stable_payload()
    yesterday_payload: Dict[str, Any] | None = None
    yesterday_cutoff_ms: int | None = None
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
                str(row.get("player_id"))
                for row in rows
                if row.get("player_id")
            ]
            events = await _fetch_player_events(session, player_ids)
            state, stable_rows = await _bootstrap_state(
                session, rows, events, generated_at_ms
            )

            day_start_ms = (generated_at_ms // MS_PER_DAY) * MS_PER_DAY
            if day_start_ms:
                yesterday_cutoff_ms = day_start_ms - 1
    finally:
        rankings_async_session.remove()

    calc_ts_int = _to_int(calc_ts)
    danger_calc_ts_int = _to_int(danger_calc_ts)
    stable_total = _to_int(total)
    danger_total_value = _to_int(danger_total)

    if yesterday_cutoff_ms is not None:
        try:
            async with rankings_async_session() as session:
                baseline_ts = await _latest_calculated_at_at_or_before(
                    session, yesterday_cutoff_ms
                )
                if baseline_ts is not None:
                    payload = await _load_baseline_snapshot_from_db(
                        session,
                        current_calc_ts=calc_ts_int,
                        baseline_ts=baseline_ts,
                    )
                    if payload and payload.get("data"):
                        yesterday_payload = payload
        finally:
            rankings_async_session.remove()

    if not previous_stable_payload or not previous_stable_payload.get("data"):
        if yesterday_payload:
            previous_stable_payload = yesterday_payload
        else:
            try:
                async with rankings_async_session() as session:
                    fallback_payload = await _load_baseline_snapshot_from_db(
                        session,
                        current_calc_ts=calc_ts_int,
                    )
                    if fallback_payload:
                        previous_stable_payload = fallback_payload
            finally:
                rankings_async_session.remove()

    new_state = state
    display_map = {
        row["player_id"]: row["display_score"] for row in stable_rows
    }
    danger_payload = _serialize_danger(danger_rows, display_map)

    grade_percentiles, score_population = _grade_threshold_percentiles(
        stable_rows
    )

    comparison_payload = yesterday_payload or previous_stable_payload

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

    delta_payload = _compute_delta_payload(
        stable_rows,
        comparison_payload,
        generated_at_ms,
    )

    _persist_state(new_state)
    _persist_payload(RIPPLE_STABLE_LATEST_KEY, stable_payload)
    _persist_payload(RIPPLE_DANGER_LATEST_KEY, danger_snapshot)
    _persist_payload(RIPPLE_STABLE_META_KEY, meta_payload)
    _persist_payload(RIPPLE_STABLE_PERCENTILES_KEY, percentiles_payload)
    _persist_payload(RIPPLE_STABLE_DELTAS_KEY, delta_payload)

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
    token = str(uuid4())
    acquired = redis_conn.set(
        RIPPLE_SNAPSHOT_LOCK_KEY,
        token,
        nx=True,
        ex=LOCK_TTL_SECONDS,
    )
    if not acquired:
        logger.info("Skipping ripple snapshot refresh; lock is already held")
        return {"skipped": True, "reason": "locked"}

    try:
        result = asyncio.run(_refresh_snapshots_async())
    finally:
        try:
            current = redis_conn.get(RIPPLE_SNAPSHOT_LOCK_KEY)
            if current == token:
                redis_conn.delete(RIPPLE_SNAPSHOT_LOCK_KEY)
        except Exception:
            logger.exception("Failed to release ripple snapshot lock")

    return result
