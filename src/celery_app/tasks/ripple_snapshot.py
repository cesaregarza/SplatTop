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
from sqlalchemy.exc import InterfaceError

from celery_app.connections import (
    rankings_async_engine,
    rankings_async_session,
    redis_conn,
)
from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_META_KEY,
    RIPPLE_SNAPSHOT_LOCK_KEY,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_PERCENTILES_KEY,
    RIPPLE_STABLE_PREVIOUS_KEY,
    RIPPLE_STABLE_PREVIOUS_META_KEY,
    RIPPLE_STABLE_STATE_KEY,
)
from shared_lib.queries import ripple_queries

logger = logging.getLogger(__name__)


LOCK_TTL_SECONDS = 15 * 60
MAX_REFRESH_RETRIES = 3
MIN_REQUIRED_TOURNAMENTS = 3
MAX_PLAYER_HISTORY_ENTRIES = 25
PLAYER_HISTORY_CHUNK_SIZE = 2_000

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
    "min_tournaments": MIN_REQUIRED_TOURNAMENTS,
    "tournament_window_days": DEFAULT_TOURNAMENT_WINDOW_DAYS,
    "ranked_only": True,
}

ALL_PLAYERS_PAGE_PARAMS = {
    "limit": DEFAULT_LIMIT,
    "offset": 0,
    "min_tournaments": None,
    "tournament_window_days": DEFAULT_TOURNAMENT_WINDOW_DAYS,
    "ranked_only": True,
}

DEFAULT_DANGER_PARAMS = {
    "limit": None,
    "offset": 0,
    "min_tournaments": MIN_REQUIRED_TOURNAMENTS,
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


def _batched(items: List[str], *, size: int) -> List[List[str]]:
    if size <= 0:
        return [items]
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def _persist_state(state: Dict[str, Any]) -> None:
    # Keep player IDs as strings so reloads round-trip cleanly and remain
    # compatible with existing Redis payloads.
    serializable = {str(player_id): value for player_id, value in state.items()}
    redis_conn.set(RIPPLE_STABLE_STATE_KEY, orjson.dumps(serializable))


def _persist_payload(key: str, payload: Mapping[str, Any]) -> None:
    redis_conn.set(key, orjson.dumps(payload))


def _load_previous_stable_payload() -> Tuple[Dict[str, Any] | None, str | None]:
    candidates = (
        (RIPPLE_STABLE_LATEST_KEY, "redis_latest"),
        (RIPPLE_STABLE_PREVIOUS_KEY, "redis_previous"),
    )
    for key, source in candidates:
        raw = redis_conn.get(key)
        if not raw:
            continue
        try:
            payload = orjson.loads(raw)
        except orjson.JSONDecodeError:
            if key == RIPPLE_STABLE_LATEST_KEY:
                logger.warning(
                    "Failed to parse previous ripple stable payload; skipping deltas"
                )
            else:
                logger.debug(
                    "Failed to parse preserved ripple stable payload from %s",
                    key,
                )
            continue
        if isinstance(payload, dict):
            return payload, source
    return None, None


def _persist_previous_payload(
    payload: Mapping[str, Any] | None,
    *,
    preserved_at_ms: int,
    source: str | None,
) -> None:
    if (
        not payload
        or not isinstance(payload, Mapping)
        or not payload.get("data")
    ):
        redis_conn.delete(RIPPLE_STABLE_PREVIOUS_KEY)
        redis_conn.delete(RIPPLE_STABLE_PREVIOUS_META_KEY)
        return

    envelope = {
        "preserved_at_ms": preserved_at_ms,
        "source": source or "unknown",
        "payload_generated_at_ms": _to_int(payload.get("generated_at_ms")),
    }

    serializable = dict(payload) if not isinstance(payload, dict) else payload
    try:
        redis_conn.set(RIPPLE_STABLE_PREVIOUS_KEY, orjson.dumps(serializable))
        redis_conn.set(RIPPLE_STABLE_PREVIOUS_META_KEY, orjson.dumps(envelope))
    except Exception as exc:  # pragma: no cover - best effort telemetry
        logger.debug("Failed to persist previous stable payload: %s", exc)


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


async def _fetch_player_ranked_history(
    session,
    player_ids: List[str],
    *,
    max_per_player: int = MAX_PLAYER_HISTORY_ENTRIES,
) -> Dict[str, List[Dict[str, Any]]]:
    if not player_ids:
        return {}

    max_rows = max(1, int(max_per_player))
    schema = ripple_queries._schema()
    schema_sql = f'"{schema}"'

    query = text(
        f"""
        WITH player_matches AS (
            SELECT DISTINCT pat.player_id::text AS player_id,
                            pat.tournament_id,
                            pat.team_id,
                            pat.match_id
            FROM {schema_sql}.player_appearance_teams pat
            WHERE pat.player_id::text = ANY(:player_ids)
        ),
        per_team AS (
            SELECT pm.player_id,
                   pm.tournament_id,
                   pm.team_id,
                   COALESCE(
                     MAX(
                       CASE
                         WHEN m.last_game_finished_at_ms IS NULL THEN NULL
                         WHEN m.last_game_finished_at_ms < 1000000000000
                           THEN m.last_game_finished_at_ms * 1000
                         ELSE m.last_game_finished_at_ms
                       END
                     ),
                     MAX(
                       CASE
                         WHEN t.start_time_ms IS NULL THEN NULL
                         WHEN t.start_time_ms < 1000000000000
                           THEN t.start_time_ms * 1000
                         ELSE t.start_time_ms
                       END
                     )
                   )::bigint AS event_ms,
                   MAX(t.name)::text AS tournament_name,
                   BOOL_OR(COALESCE(t.is_ranked, false)) AS is_ranked,
                   COALESCE(
                     SUM(CASE WHEN m.winner_team_id = pm.team_id THEN 1 ELSE 0 END),
                     0
                   )::int AS wins,
                   COALESCE(
                     SUM(CASE WHEN m.loser_team_id = pm.team_id THEN 1 ELSE 0 END),
                     0
                   )::int AS losses
            FROM player_matches pm
            LEFT JOIN {schema_sql}.matches m
              ON m.match_id = pm.match_id
             AND m.tournament_id = pm.tournament_id
            LEFT JOIN {schema_sql}.tournaments t
              ON t.tournament_id = pm.tournament_id
            GROUP BY pm.player_id, pm.tournament_id, pm.team_id
        ),
        per_tournament AS (
            SELECT pt.player_id,
                   pt.tournament_id,
                   pt.event_ms,
                   pt.tournament_name,
                   pt.is_ranked,
                   pt.team_id,
                   pt.wins,
                   pt.losses,
                   tt.name::text AS team_name,
                   ROW_NUMBER() OVER (
                     PARTITION BY pt.player_id, pt.tournament_id
                     ORDER BY (pt.wins + pt.losses) DESC,
                              pt.wins DESC,
                              COALESCE(pt.team_id, 0) DESC
                   ) AS team_row_num
            FROM per_team pt
            LEFT JOIN {schema_sql}.tournament_teams tt
              ON tt.tournament_id = pt.tournament_id
             AND tt.team_id = pt.team_id
        ),
        ranked_rows AS (
            SELECT pt.player_id,
                   pt.tournament_id,
                   pt.event_ms,
                   pt.tournament_name,
                   pt.is_ranked,
                   pt.team_id,
                   pt.team_name,
                   pt.wins,
                   pt.losses,
                   ROW_NUMBER() OVER (
                     PARTITION BY pt.player_id
                     ORDER BY pt.event_ms DESC NULLS LAST, pt.tournament_id DESC
                   ) AS row_num
            FROM per_tournament pt
            WHERE pt.team_row_num = 1
              AND pt.is_ranked IS TRUE
        )
        SELECT player_id,
               tournament_id,
               event_ms,
               tournament_name,
               is_ranked,
               team_id,
               team_name,
               wins,
               losses
        FROM ranked_rows
        WHERE row_num <= :max_per_player
        ORDER BY player_id, row_num
        """
    )

    history_by_player: Dict[str, List[Dict[str, Any]]] = {}

    for batch in _batched(player_ids, size=PLAYER_HISTORY_CHUNK_SIZE):
        try:
            result = await session.execute(
                query,
                {
                    "player_ids": batch,
                    "max_per_player": max_rows,
                },
            )
            rows = result.mappings().all()
        except Exception as exc:
            logger.warning(
                "Failed to fetch ranked tournament history for %s players: %s",
                len(batch),
                exc,
            )
            return {}

        for row in rows:
            if not bool(row.get("is_ranked")):
                continue

            player_id = str(row.get("player_id") or "")
            if not player_id:
                continue

            tournament_id_raw = row.get("tournament_id")
            tournament_id_int = _to_int(tournament_id_raw)
            tournament_id: int | str | None = tournament_id_int
            if tournament_id is None and tournament_id_raw is not None:
                tournament_id = str(tournament_id_raw)

            tournament_name = row.get("tournament_name")
            if not tournament_name and tournament_id is not None:
                tournament_name = f"Tournament {tournament_id}"

            team_id_raw = row.get("team_id")
            team_id_int = _to_int(team_id_raw)
            team_id: int | str | None = team_id_int
            if team_id is None and team_id_raw is not None:
                team_id = str(team_id_raw)

            wins = _to_int(row.get("wins")) or 0
            losses = _to_int(row.get("losses")) or 0
            result_summary = (
                f"{wins}W-{losses}L"
                if wins > 0 or losses > 0
                else None
            )

            team_name = row.get("team_name")
            if not team_name and team_id is not None:
                team_name = f"Team {team_id}"

            history_by_player.setdefault(player_id, []).append(
                {
                    "tournament_id": tournament_id,
                    "tournament_name": tournament_name,
                    "event_ms": _to_int(row.get("event_ms")),
                    "ranked": True,
                    "placement_label": None,
                    "result_summary": result_summary,
                    "team_name": team_name,
                    "team_id": team_id,
                }
            )

    for player_id, rows in history_by_player.items():
        rows.sort(
            key=lambda row: (
                _to_int(row.get("event_ms")) or -1,
                _to_int(row.get("tournament_id")) or -1,
            ),
            reverse=True,
        )
        history_by_player[player_id] = rows[:max_rows]

    return history_by_player


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


def _build_player_index_payload(
    *,
    all_rows: List[Mapping[str, Any]],
    stable_rows: List[Mapping[str, Any]],
    danger_rows: List[Mapping[str, Any]],
    tournament_history_by_player: Mapping[str, List[Mapping[str, Any]]],
    delta_payload: Mapping[str, Any],
    generated_at_ms: int,
    calculated_at_ms: int | None,
    build_version: str | None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    stable_by_id: Dict[str, Mapping[str, Any]] = {}
    for row in stable_rows:
        player_id = row.get("player_id")
        if player_id:
            stable_by_id[str(player_id)] = row

    danger_by_id: Dict[str, Mapping[str, Any]] = {}
    for row in danger_rows:
        player_id = row.get("player_id")
        if player_id:
            danger_by_id[str(player_id)] = row

    baseline_generated_at_ms = _to_int(
        delta_payload.get("baseline_generated_at_ms")
    )
    has_baseline = baseline_generated_at_ms is not None
    raw_delta_players = delta_payload.get("players")
    delta_players: Mapping[str, Any]
    if isinstance(raw_delta_players, Mapping):
        delta_players = raw_delta_players
    else:
        delta_players = {}

    players: Dict[str, Dict[str, Any]] = {}
    for row in all_rows:
        raw_player_id = row.get("player_id")
        if raw_player_id is None:
            continue
        player_id = str(raw_player_id)
        stable_row = stable_by_id.get(player_id, {})
        danger_row = danger_by_id.get(player_id, {})
        delta_entry = delta_players.get(player_id)
        if not isinstance(delta_entry, Mapping):
            delta_entry = {}

        lifetime_tournament_count = _to_int(row.get("tournament_count"))
        if lifetime_tournament_count is None:
            lifetime_tournament_count = _to_int(
                stable_row.get("tournament_count")
            )
        lifetime_tournament_count = max(0, lifetime_tournament_count or 0)

        window_tournament_count = _to_int(row.get("window_count"))
        if window_tournament_count is None:
            window_tournament_count = _to_int(
                stable_row.get("window_tournament_count")
            )

        eligible = player_id in stable_by_id
        ineligible_reason = None
        if not eligible:
            if lifetime_tournament_count < MIN_REQUIRED_TOURNAMENTS:
                ineligible_reason = "insufficient_lifetime_tournaments"
            else:
                ineligible_reason = "not_currently_eligible"

        stable_rank = _to_int(stable_row.get("stable_rank"))
        stable_score = _to_float(stable_row.get("stable_score"))
        display_score = _to_float(stable_row.get("display_score"))

        # Players with fewer than the minimum required lifetime tournaments
        # should not show rank/score on the public profile.
        if lifetime_tournament_count < MIN_REQUIRED_TOURNAMENTS:
            stable_rank = None
            stable_score = None
            display_score = None

        last_active_ms = _to_int(stable_row.get("last_active_ms"))
        if last_active_ms is None:
            last_active_ms = _to_int(row.get("last_active_ms"))
        last_tournament_ms = _to_int(stable_row.get("last_tournament_ms"))
        if last_tournament_ms is None:
            last_tournament_ms = last_active_ms

        progress_current = min(
            lifetime_tournament_count, MIN_REQUIRED_TOURNAMENTS
        )
        progress_remaining = max(
            0, MIN_REQUIRED_TOURNAMENTS - progress_current
        )
        player_history = tournament_history_by_player.get(player_id)
        if not isinstance(player_history, list):
            player_history = []
        history_rows = [
            dict(item) for item in player_history if isinstance(item, Mapping)
        ]

        players[player_id] = {
            "player_id": player_id,
            "display_name": stable_row.get("display_name")
            or row.get("display_name"),
            "eligible": eligible,
            "ineligible_reason": ineligible_reason,
            "minimum_required_tournaments": MIN_REQUIRED_TOURNAMENTS,
            "lifetime_ranked_tournaments": lifetime_tournament_count,
            "window_tournament_count": window_tournament_count,
            "progress_to_minimum": {
                "current": progress_current,
                "required": MIN_REQUIRED_TOURNAMENTS,
                "remaining": progress_remaining,
            },
            "stable_rank": stable_rank,
            "stable_score": stable_score,
            "display_score": display_score,
            "danger_days_left": _to_float(danger_row.get("days_left")),
            "last_active_ms": last_active_ms,
            "last_tournament_ms": last_tournament_ms,
            "rank_delta": _to_int(delta_entry.get("rank_delta"))
            if has_baseline
            else None,
            "display_score_delta": _to_float(
                delta_entry.get("display_score_delta")
            )
            if has_baseline
            else None,
            "delta_is_new": bool(delta_entry.get("is_new"))
            if has_baseline
            else False,
            "delta_has_baseline": has_baseline,
            "previous_rank": _to_int(delta_entry.get("previous_rank"))
            if has_baseline
            else None,
            "previous_display_score": _to_float(
                delta_entry.get("previous_display_score")
            )
            if has_baseline
            else None,
            "history_generated_at_ms": generated_at_ms,
            "history_record_count": len(history_rows),
            "history_max_records": MAX_PLAYER_HISTORY_ENTRIES,
            "tournament_history_ranked": history_rows,
        }

    payload = {
        "generated_at_ms": generated_at_ms,
        "calculated_at_ms": calculated_at_ms,
        "build_version": build_version,
        "minimum_required_tournaments": MIN_REQUIRED_TOURNAMENTS,
        "record_count": len(players),
        "players": players,
    }
    meta = {
        "generated_at_ms": generated_at_ms,
        "calculated_at_ms": calculated_at_ms,
        "build_version": build_version,
        "minimum_required_tournaments": MIN_REQUIRED_TOURNAMENTS,
        "record_count": len(players),
    }
    return payload, meta


async def _refresh_snapshots_async_once() -> Dict[str, Any]:
    generated_at_ms = _now_ms()
    rows: List[Mapping[str, Any]] = []
    all_rows: List[Mapping[str, Any]] = []
    total: Any = 0
    all_total: Any = 0
    calc_ts: Any = None
    build_version: Any = None
    danger_rows: List[Dict[str, Any]] = []
    danger_total: Any = 0
    danger_calc_ts: Any = None
    danger_build: Any = None
    events: Dict[str, Dict[str, Any]] = {}
    tournament_history_by_player: Dict[str, List[Dict[str, Any]]] = {}
    state: Dict[str, Any] = {}
    stable_rows: List[Dict[str, Any]] = []
    previous_stable_payload, preserved_source = _load_previous_stable_payload()
    preserved_payload: Dict[str, Any] | None = None
    if previous_stable_payload and previous_stable_payload.get("data"):
        preserved_payload = previous_stable_payload
        preserved_source = preserved_source or "redis_latest"
    yesterday_payload: Dict[str, Any] | None = None
    yesterday_cutoff_ms: int | None = None

    # Use a single session for all database queries
    async with rankings_async_session() as session:
        # Main query block in its own transaction
        async with session.begin():
            (
                rows,
                total,
                calc_ts,
                build_version,
            ) = await ripple_queries.fetch_ripple_page(
                session, **DEFAULT_PAGE_PARAMS
            )
            (
                all_rows,
                all_total,
                _all_calc_ts,
                _all_build_version,
            ) = await ripple_queries.fetch_ripple_page(
                session, **ALL_PLAYERS_PAGE_PARAMS
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
            all_player_ids = sorted(
                {
                    str(row.get("player_id"))
                    for row in all_rows
                    if row.get("player_id")
                }
            )
            events = await _fetch_player_events(session, player_ids)
            tournament_history_by_player = (
                await _fetch_player_ranked_history(
                    session,
                    all_player_ids,
                    max_per_player=MAX_PLAYER_HISTORY_ENTRIES,
                )
            )
            state, stable_rows = await _bootstrap_state(
                session, rows, events, generated_at_ms
            )

            day_start_ms = (generated_at_ms // MS_PER_DAY) * MS_PER_DAY
            if day_start_ms:
                yesterday_cutoff_ms = day_start_ms - 1

        calc_ts_int = _to_int(calc_ts)
        danger_calc_ts_int = _to_int(danger_calc_ts)
        stable_total = _to_int(total)
        danger_total_value = _to_int(danger_total)

        # Load yesterday's baseline snapshot in a new transaction
        if yesterday_cutoff_ms is not None:
            async with session.begin():
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

        # Load fallback snapshot if needed in a new transaction
        if not previous_stable_payload or not previous_stable_payload.get(
            "data"
        ):
            if yesterday_payload and yesterday_payload.get("data"):
                previous_stable_payload = yesterday_payload
                preserved_payload = previous_stable_payload
                preserved_source = "db_yesterday"
            else:
                async with session.begin():
                    fallback_payload = await _load_baseline_snapshot_from_db(
                        session,
                        current_calc_ts=calc_ts_int,
                    )
                    if fallback_payload and fallback_payload.get("data"):
                        previous_stable_payload = fallback_payload
                        preserved_payload = previous_stable_payload
                        preserved_source = "db_baseline"

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
    player_index_payload, player_index_meta_payload = (
        _build_player_index_payload(
            all_rows=all_rows,
            stable_rows=stable_rows,
            danger_rows=danger_payload,
            tournament_history_by_player=tournament_history_by_player,
            delta_payload=delta_payload,
            generated_at_ms=generated_at_ms,
            calculated_at_ms=calc_ts_int,
            build_version=build_version,
        )
    )

    _persist_previous_payload(
        preserved_payload,
        preserved_at_ms=generated_at_ms,
        source=preserved_source,
    )
    _persist_state(new_state)
    _persist_payload(RIPPLE_STABLE_LATEST_KEY, stable_payload)
    _persist_payload(RIPPLE_DANGER_LATEST_KEY, danger_snapshot)
    _persist_payload(RIPPLE_STABLE_META_KEY, meta_payload)
    _persist_payload(RIPPLE_STABLE_PERCENTILES_KEY, percentiles_payload)
    _persist_payload(RIPPLE_STABLE_DELTAS_KEY, delta_payload)
    _persist_payload(RIPPLE_PLAYER_INDEX_LATEST_KEY, player_index_payload)
    _persist_payload(RIPPLE_PLAYER_INDEX_META_KEY, player_index_meta_payload)

    logger.info(
        "Refreshed ripple snapshots: %s stable rows, %s danger rows, %s indexed players",
        len(stable_rows),
        len(danger_payload),
        len(player_index_payload["players"]),
    )

    return {
        "stable_rows": len(stable_rows),
        "danger_rows": len(danger_payload),
        "indexed_players": len(player_index_payload["players"]),
        "all_rows": _to_int(all_total),
    }


async def _refresh_snapshots_async() -> Dict[str, Any]:
    attempts = 0
    try:
        while True:
            try:
                return await _refresh_snapshots_async_once()
            except InterfaceError as exc:
                attempts += 1
                if attempts >= MAX_REFRESH_RETRIES:
                    logger.exception(
                        "Failed to refresh ripple snapshots after %s attempts",
                        attempts,
                    )
                    raise
                logger.warning(
                    "Retrying ripple snapshot refresh after InterfaceError: %s",
                    exc,
                )
                await rankings_async_engine.dispose()
                await asyncio.sleep(0.5)
    finally:
        await rankings_async_engine.dispose()


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
