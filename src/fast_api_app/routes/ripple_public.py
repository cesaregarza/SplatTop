from __future__ import annotations

import logging
from html import escape
from io import BytesIO
import time
from time import perf_counter
from typing import Any, Dict, Optional
from urllib.parse import quote

import orjson
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import text

from celery_app.tasks.ripple_snapshot import (
    MAX_PLAYER_HISTORY_ENTRIES,
    MAX_PLAYER_MATCH_LOO_ENTRIES,
    MIN_REQUIRED_TOURNAMENTS,
    _fetch_player_match_loo_impacts,
    _fetch_player_ranked_history,
    refresh_ripple_snapshots,
)
from fast_api_app.comp_auth import (
    is_comp_admin_discord_id,
    is_comp_player_owner,
    read_authenticated_comp_discord_id,
    require_comp_admin,
)
from fast_api_app.connections import celery, rankings_async_session, redis_conn
from fast_api_app.feature_flags import is_comp_leaderboard_enabled
from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_META_KEY,
    RIPPLE_PLAYER_INDEX_PLAYER_PREFIX,
    RIPPLE_PLAYER_INDEX_PLAYER_HISTORY_PREFIX,
    RIPPLE_PLAYER_INDEX_PLAYER_RESULTS_PREFIX,
    RIPPLE_PLAYER_INDEX_PLAYER_SUMMARY_PREFIX,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_PERCENTILES_KEY,
)
from shared_lib.queries import ripple_queries
from shared_lib.monitoring import (
    RIPPLE_PLAYER_SECTION_CACHE_REQUESTS,
    RIPPLE_PLAYER_SECTION_PAYLOAD_BYTES,
    RIPPLE_PLAYER_SECTION_RESOLVE_DURATION,
    metrics_enabled,
)

router = APIRouter(prefix="/api/ripple/public", tags=["ripple-public"])
admin_router = APIRouter(prefix="/api/ripple/admin", tags=["ripple-admin"])
share_router = APIRouter(tags=["ripple-public-share"])

logger = logging.getLogger(__name__)


_STALENESS_THRESHOLD_MS = 24 * 60 * 60 * 1000  # 24 hours
_SHARE_CARD_WIDTH = 1200
_SHARE_CARD_HEIGHT = 630
_SHARE_SCORE_OFFSET = 150.0
_SHARE_SCORE_TARGET = 250.0
_SHARE_FONT_REGULAR_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_SHARE_FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_DEFAULT_PLAYER_WINDOW_DAYS = 120


def _ensure_enabled() -> None:
    if not is_comp_leaderboard_enabled():
        raise HTTPException(
            status_code=404, detail="Competition leaderboard is disabled"
        )


def _load_payload(key: str) -> Optional[Dict[str, Any]]:
    raw = redis_conn.get(key)
    if not raw:
        return None
    try:
        return orjson.loads(raw)
    except orjson.JSONDecodeError:
        return None


def _observe_ripple_player_section_payload(
    section: str, payload: Dict[str, Any] | None
) -> None:
    if not metrics_enabled() or not isinstance(payload, dict):
        return

    RIPPLE_PLAYER_SECTION_PAYLOAD_BYTES.labels(section=section).observe(
        len(orjson.dumps(payload))
    )


def _empty_payload() -> Dict[str, Any]:
    return {
        "build_version": None,
        "calculated_at_ms": None,
        "generated_at_ms": None,
        "query_params": {},
        "record_count": 0,
        "total": 0,
        "data": [],
    }


def _empty_percentiles_payload() -> Dict[str, Any]:
    return {
        "generated_at_ms": None,
        "record_count": 0,
        "score_population": 0,
        "grade_thresholds": [],
        "transform": {
            "score_offset": 0.0,
            "display_offset": 0.0,
            "multiplier": 1.0,
        },
    }


def _empty_deltas_payload() -> Dict[str, Any]:
    return {
        "generated_at_ms": None,
        "baseline_generated_at_ms": None,
        "record_count": 0,
        "comparison_count": 0,
        "players": {},
        "newcomers": [],
        "dropouts": [],
    }


def _empty_player_index_payload() -> Dict[str, Any]:
    return {
        "generated_at_ms": None,
        "calculated_at_ms": None,
        "build_version": None,
        "minimum_required_tournaments": 3,
        "record_count": 0,
        "player_ids": [],
        "players": {},
    }


def _player_index_key(player_id: str) -> str:
    return f"{RIPPLE_PLAYER_INDEX_PLAYER_PREFIX}{player_id}"


def _player_index_summary_key(player_id: str) -> str:
    return f"{RIPPLE_PLAYER_INDEX_PLAYER_SUMMARY_PREFIX}{player_id}"


def _player_index_history_key(player_id: str) -> str:
    return f"{RIPPLE_PLAYER_INDEX_PLAYER_HISTORY_PREFIX}{player_id}"


def _player_index_results_key(player_id: str) -> str:
    return f"{RIPPLE_PLAYER_INDEX_PLAYER_RESULTS_PREFIX}{player_id}"


def _extract_player_from_legacy_index(
    payload: Dict[str, Any], player_id: str
) -> Optional[Dict[str, Any]]:
    players = payload.get("players")
    if not isinstance(players, dict):
        return None

    player = players.get(player_id)
    return player if isinstance(player, dict) else None


def _load_player_index_meta_payload() -> Dict[str, Any]:
    meta_payload = _load_payload(RIPPLE_PLAYER_INDEX_META_KEY)
    if not isinstance(meta_payload, dict):
        latest_payload = _load_payload(RIPPLE_PLAYER_INDEX_LATEST_KEY)
        if isinstance(latest_payload, dict):
            meta_payload = latest_payload
        else:
            meta_payload = _empty_player_index_payload()
    return meta_payload


def _merge_player_payload_with_meta(
    player: Dict[str, Any], meta_payload: Dict[str, Any]
) -> Dict[str, Any]:
    enriched = _decorate(
        {
            "generated_at_ms": meta_payload.get("generated_at_ms"),
        }
    )
    response = dict(player)
    response.update(
        {
            "generated_at_ms": meta_payload.get("generated_at_ms"),
            "calculated_at_ms": meta_payload.get("calculated_at_ms"),
            "build_version": meta_payload.get("build_version"),
            "stale": enriched["stale"],
            "retrieved_at_ms": enriched["retrieved_at_ms"],
        }
    )
    return response


def _load_public_player_payload(player_id: str) -> Optional[Dict[str, Any]]:
    meta_payload = _load_player_index_meta_payload()
    player = _load_payload(_player_index_key(player_id))
    if not isinstance(player, dict):
        latest_payload = _load_payload(RIPPLE_PLAYER_INDEX_LATEST_KEY)
        if isinstance(latest_payload, dict):
            player = _extract_player_from_legacy_index(
                latest_payload, player_id
            )

    if not isinstance(player, dict):
        return None

    return _merge_player_payload_with_meta(player, meta_payload)


def _load_public_player_section_payload(
    player_id: str,
    section: str,
    section_key: str,
) -> Optional[Dict[str, Any]]:
    started = perf_counter()
    meta_payload = _load_player_index_meta_payload()
    player = _load_payload(section_key)
    if isinstance(player, dict):
        resolved = _merge_player_payload_with_meta(player, meta_payload)
        status = "section_hit"
    else:
        resolved = _load_public_player_payload(player_id)
        status = "legacy_hit" if isinstance(resolved, dict) else "miss"

    if metrics_enabled():
        RIPPLE_PLAYER_SECTION_CACHE_REQUESTS.labels(
            section=section,
            status=status,
        ).inc()
        RIPPLE_PLAYER_SECTION_RESOLVE_DURATION.labels(
            section=section,
            status=status,
        ).observe(perf_counter() - started)

    return resolved


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


def _danger_days_left_for_player(player_id: str) -> float | None:
    payload = _load_payload(RIPPLE_DANGER_LATEST_KEY)
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("player_id") or "") != player_id:
            continue
        return _to_float(row.get("days_left"))
    return None


async def _load_admin_player_base_from_db(
    session,
    player_id: str,
) -> Dict[str, Any] | None:
    schema = ripple_queries._schema()
    schema_sql = f'"{schema}"'
    window_ms = _DEFAULT_PLAYER_WINDOW_DAYS * 86_400_000

    query = text(
        f"""
        WITH latest_ts AS (
            SELECT MAX(calculated_at_ms) AS ts
            FROM {schema_sql}.player_rankings
        ),
        latest_build AS (
            SELECT MAX(r.build_version)::text AS build_version
            FROM {schema_sql}.player_rankings r
            JOIN latest_ts l ON r.calculated_at_ms = l.ts
        ),
        ranked_events AS (
            SELECT DISTINCT
                pat.tournament_id,
                CASE
                    WHEN tet.event_ms IS NULL THEN NULL
                    WHEN tet.event_ms < 1000000000000
                        THEN tet.event_ms * 1000
                    ELSE tet.event_ms
                END::bigint AS event_ms
            FROM {schema_sql}.player_appearance_teams pat
            JOIN {schema_sql}.tournament_event_times tet
              ON tet.tournament_id = pat.tournament_id
            WHERE pat.player_id::text = :player_id
              AND tet.is_ranked IS TRUE
        ),
        counts AS (
            SELECT
                COUNT(*)::int AS lifetime_ranked_tournaments,
                COALESCE(
                    SUM(
                        CASE
                            WHEN re.event_ms IS NOT NULL
                             AND latest_ts.ts IS NOT NULL
                             AND re.event_ms BETWEEN
                               (latest_ts.ts - :window_ms) AND latest_ts.ts
                                THEN 1
                            ELSE 0
                        END
                    ),
                    0
                )::int AS window_tournament_count,
                MAX(re.event_ms)::bigint AS last_active_ms
            FROM ranked_events re
            CROSS JOIN latest_ts
        ),
        current_rank AS (
            SELECT ranked.player_id::text AS player_id,
                   ranked.stable_rank::int AS stable_rank,
                   ranked.score::double precision AS stable_score,
                   (ranked.score * 25.0)::double precision AS display_score
            FROM (
                SELECT
                    r.player_id,
                    r.score,
                    ROW_NUMBER() OVER (
                        ORDER BY r.score DESC, r.player_id
                    ) AS stable_rank
                FROM {schema_sql}.player_rankings r
                JOIN latest_ts l ON r.calculated_at_ms = l.ts
            ) ranked
            WHERE ranked.player_id::text = :player_id
        ),
        current_stats AS (
            SELECT
                s.tournament_count::int AS ranking_tournament_count,
                CASE
                    WHEN s.last_active_ms IS NULL THEN NULL
                    WHEN s.last_active_ms < 1000000000000
                        THEN s.last_active_ms * 1000
                    ELSE s.last_active_ms
                END::bigint AS ranking_last_active_ms
            FROM {schema_sql}.player_ranking_stats s
            JOIN latest_ts l ON s.calculated_at_ms = l.ts
            WHERE s.player_id::text = :player_id
        )
        SELECT
            COALESCE(p.player_id::text, current_rank.player_id, :player_id)
              AS player_id,
            p.display_name::text AS display_name,
            COALESCE(
                counts.lifetime_ranked_tournaments,
                current_stats.ranking_tournament_count,
                0
            )::int AS lifetime_ranked_tournaments,
            COALESCE(counts.window_tournament_count, 0)::int
              AS window_tournament_count,
            COALESCE(
                counts.last_active_ms,
                current_stats.ranking_last_active_ms
            )::bigint AS last_active_ms,
            current_rank.stable_rank,
            current_rank.stable_score,
            current_rank.display_score,
            latest_ts.ts::bigint AS calculated_at_ms,
            latest_build.build_version
        FROM latest_ts
        LEFT JOIN latest_build ON TRUE
        LEFT JOIN {schema_sql}.players p
          ON p.player_id::text = :player_id
        LEFT JOIN counts ON TRUE
        LEFT JOIN current_rank ON TRUE
        LEFT JOIN current_stats ON TRUE
        """
    )

    result = await session.execute(
        query,
        {
            "player_id": player_id,
            "window_ms": window_ms,
        },
    )
    row = result.mappings().first()
    if not row:
        return None

    base = dict(row)
    has_any_data = any(
        [
            str(base.get("display_name") or "").strip(),
            _to_int(base.get("lifetime_ranked_tournaments")),
            _to_int(base.get("window_tournament_count")),
            _to_int(base.get("last_active_ms")),
            _to_int(base.get("stable_rank")),
            _to_float(base.get("stable_score")),
        ]
    )
    if not has_any_data:
        return None
    return base


async def _enrich_admin_player_payload_with_db_history(
    player_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    response = dict(payload)
    history_generated_at_ms = _to_int(
        response.get("history_generated_at_ms")
    ) or _to_int(response.get("generated_at_ms"))
    if history_generated_at_ms is None:
        history_generated_at_ms = int(time.time() * 1000)

    calculated_at_ms = _to_int(response.get("calculated_at_ms"))
    build_version = response.get("build_version")

    try:
        async with rankings_async_session() as session:
            history_by_player = await _fetch_player_ranked_history(
                session,
                [player_id],
                max_per_player=None,
            )
            match_loo_by_player = (
                await _fetch_player_match_loo_impacts(
                    session,
                    [player_id],
                    calculated_at_ms=calculated_at_ms,
                    build_version=build_version,
                    max_per_player=MAX_PLAYER_MATCH_LOO_ENTRIES,
                )
                if calculated_at_ms is not None
                else {}
            )
    except Exception:
        logger.exception(
            "Failed to enrich cached admin competition player payload from DB",
            extra={"player_id": player_id},
        )
        return response

    history_rows = history_by_player.get(player_id)
    if isinstance(history_rows, list):
        response["history_generated_at_ms"] = history_generated_at_ms
        response["history_record_count"] = len(history_rows)
        response["history_max_records"] = None
        response["tournament_history_ranked"] = history_rows

    match_loo_rows = match_loo_by_player.get(player_id)
    if isinstance(match_loo_rows, list):
        response["match_loo_generated_at_ms"] = history_generated_at_ms
        response["match_loo_record_count"] = len(match_loo_rows)
        response["match_loo_max_records"] = MAX_PLAYER_MATCH_LOO_ENTRIES
        response["match_loo_impacts"] = match_loo_rows

    return response


async def _load_admin_player_payload_from_db_only(
    player_id: str,
) -> Dict[str, Any] | None:
    player_id = str(player_id or "").strip()
    if not player_id:
        return None

    meta_payload = _load_payload(RIPPLE_PLAYER_INDEX_META_KEY)
    if not isinstance(meta_payload, dict):
        meta_payload = _load_payload(RIPPLE_STABLE_META_KEY) or {}

    async with rankings_async_session() as session:
        base = await _load_admin_player_base_from_db(session, player_id)
        if not isinstance(base, dict):
            return None

        history_by_player = await _fetch_player_ranked_history(
            session,
            [player_id],
            max_per_player=None,
        )
        match_loo_by_player = await _fetch_player_match_loo_impacts(
            session,
            [player_id],
            calculated_at_ms=_to_int(base.get("calculated_at_ms")),
            build_version=base.get("build_version"),
            max_per_player=MAX_PLAYER_MATCH_LOO_ENTRIES,
        )

    history_rows = history_by_player.get(player_id) or []
    match_loo_rows = match_loo_by_player.get(player_id) or []
    lifetime_ranked_tournaments = max(
        0, _to_int(base.get("lifetime_ranked_tournaments")) or 0
    )
    window_tournament_count = max(
        0, _to_int(base.get("window_tournament_count")) or 0
    )
    stable_rank = _to_int(base.get("stable_rank"))
    stable_score = _to_float(base.get("stable_score"))
    display_score = _to_float(base.get("display_score"))
    eligible = stable_rank is not None and stable_score is not None

    generated_at_ms = _to_int(meta_payload.get("generated_at_ms"))
    if generated_at_ms is None:
        generated_at_ms = int(time.time() * 1000)

    last_active_ms = _to_int(base.get("last_active_ms"))
    last_tournament_ms = last_active_ms
    if last_tournament_ms is None and history_rows:
        last_tournament_ms = _to_int(history_rows[0].get("event_ms"))

    progress_current = min(
        lifetime_ranked_tournaments, MIN_REQUIRED_TOURNAMENTS
    )
    progress_remaining = max(
        0, MIN_REQUIRED_TOURNAMENTS - progress_current
    )

    delta_payload = _load_payload(RIPPLE_STABLE_DELTAS_KEY) or {}
    delta_players = (
        delta_payload.get("players")
        if isinstance(delta_payload.get("players"), dict)
        else {}
    )
    delta_entry = delta_players.get(player_id, {})
    has_baseline = _to_int(delta_payload.get("baseline_generated_at_ms")) is not None

    return {
        "player_id": player_id,
        "display_name": str(base.get("display_name") or player_id),
        "eligible": eligible,
        "ineligible_reason": None
        if eligible
        else "insufficient_lifetime_tournaments"
        if lifetime_ranked_tournaments < MIN_REQUIRED_TOURNAMENTS
        else "not_currently_eligible",
        "minimum_required_tournaments": MIN_REQUIRED_TOURNAMENTS,
        "lifetime_ranked_tournaments": lifetime_ranked_tournaments,
        "window_tournament_count": window_tournament_count,
        "progress_to_minimum": {
            "current": progress_current,
            "required": MIN_REQUIRED_TOURNAMENTS,
            "remaining": progress_remaining,
        },
        "stable_rank": stable_rank,
        "stable_score": stable_score,
        "display_score": display_score,
        "danger_days_left": _danger_days_left_for_player(player_id),
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
        "history_max_records": None,
        "tournament_history_ranked": history_rows,
        "match_loo_generated_at_ms": generated_at_ms,
        "match_loo_record_count": len(match_loo_rows),
        "match_loo_max_records": MAX_PLAYER_MATCH_LOO_ENTRIES,
        "match_loo_impacts": match_loo_rows,
        "generated_at_ms": generated_at_ms,
        "calculated_at_ms": _to_int(base.get("calculated_at_ms"))
        or _to_int(meta_payload.get("calculated_at_ms")),
        "build_version": base.get("build_version")
        or meta_payload.get("build_version"),
        "stale": _decorate({"generated_at_ms": generated_at_ms})["stale"],
        "retrieved_at_ms": int(time.time() * 1000),
    }


async def _load_admin_player_payload_from_db(
    player_id: str,
) -> Dict[str, Any] | None:
    player_id = str(player_id or "").strip()
    if not player_id:
        return None

    cached_player = _apply_admin_player_overrides(
        _load_public_player_payload(player_id)
    )
    if isinstance(cached_player, dict):
        return await _enrich_admin_player_payload_with_db_history(
            player_id,
            cached_player,
        )

    return await _load_admin_player_payload_from_db_only(player_id)


def _strip_private_player_fields(
    payload: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    return {
        key: value
        for key, value in payload.items()
        if not str(key).startswith("private_")
    }


def _strip_player_results_fields(
    payload: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    hidden_fields = {
        "match_loo_generated_at_ms",
        "match_loo_record_count",
        "match_loo_max_records",
        "match_loo_impacts",
    }
    return {
        key: value for key, value in payload.items() if key not in hidden_fields
    }


def _apply_admin_player_overrides(
    payload: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    response = dict(payload)
    response["stable_rank"] = response.get(
        "private_stable_rank", response.get("stable_rank")
    )
    response["stable_score"] = response.get(
        "private_stable_score", response.get("stable_score")
    )
    response["display_score"] = response.get(
        "private_display_score", response.get("display_score")
    )
    return _strip_private_player_fields(response)


def _apply_public_player_visibility(
    payload: Dict[str, Any] | None,
    request: Request,
    player_id: str,
) -> Dict[str, Any] | None:
    public_payload = _strip_private_player_fields(payload)
    if not isinstance(public_payload, dict):
        return None

    discord_id = read_authenticated_comp_discord_id(request)
    can_view_results = is_comp_admin_discord_id(
        discord_id
    ) or is_comp_player_owner(player_id, discord_id)

    response = (
        dict(public_payload)
        if can_view_results
        else _strip_player_results_fields(public_payload)
    )
    response["viewer_can_view_results"] = can_view_results
    return response


def _player_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail="Player not found in competition index",
    )


def _build_player_summary_payload(
    payload: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    excluded_fields = {
        "tournament_history_ranked",
        "match_loo_impacts",
    }
    return {
        key: value
        for key, value in payload.items()
        if key not in excluded_fields
    }


def _build_player_history_payload(
    payload: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    return {
        "player_id": payload.get("player_id"),
        "generated_at_ms": payload.get("generated_at_ms"),
        "history_generated_at_ms": payload.get("history_generated_at_ms"),
        "history_record_count": payload.get("history_record_count", 0),
        "history_max_records": payload.get("history_max_records"),
        "tournament_history_ranked": payload.get("tournament_history_ranked")
        if isinstance(payload.get("tournament_history_ranked"), list)
        else [],
    }


def _build_player_results_payload(
    payload: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    viewer_can_view_results = bool(payload.get("viewer_can_view_results"))
    return {
        "player_id": payload.get("player_id"),
        "generated_at_ms": payload.get("generated_at_ms"),
        "viewer_can_view_results": viewer_can_view_results,
        "match_loo_generated_at_ms": payload.get("match_loo_generated_at_ms")
        if viewer_can_view_results
        else None,
        "match_loo_record_count": payload.get("match_loo_record_count", 0)
        if viewer_can_view_results
        else 0,
        "match_loo_max_records": payload.get("match_loo_max_records")
        if viewer_can_view_results
        else None,
        "match_loo_impacts": payload.get("match_loo_impacts")
        if viewer_can_view_results and isinstance(payload.get("match_loo_impacts"), list)
        else [],
    }


def _decorate(payload: Dict[str, Any]) -> Dict[str, Any]:
    generated_at_ms = payload.get("generated_at_ms")
    now_ms = int(time.time() * 1000)
    stale = True
    if generated_at_ms is not None:
        try:
            delta = now_ms - int(generated_at_ms)
            stale = delta > _STALENESS_THRESHOLD_MS
        except (TypeError, ValueError):
            stale = True
    enriched = dict(payload)
    enriched["stale"] = stale
    enriched["retrieved_at_ms"] = now_ms
    return enriched


def _decorate_percentiles(payload: Dict[str, Any]) -> Dict[str, Any]:
    base = _decorate(payload)
    # Percentiles payloads don't carry build metadata, so drop unused keys.
    return base


@router.get(
    "/leaderboard",
    name="public-ripple-leaderboard",
    summary="Get public ripple leaderboard",
)
@router.get(
    "",
    name="public-ripple-stable-legacy",
    include_in_schema=False,
    deprecated=True,
)
async def get_public_ripple_leaderboard() -> Dict[str, Any]:
    _ensure_enabled()
    payload = _load_payload(RIPPLE_STABLE_LATEST_KEY) or _empty_payload()
    deltas = _load_payload(RIPPLE_STABLE_DELTAS_KEY) or _empty_deltas_payload()
    enriched = _decorate(payload)
    enriched["deltas"] = _decorate(deltas)
    return enriched


@router.get(
    "/leaderboard/danger",
    name="public-ripple-leaderboard-danger",
    summary="Get public ripple danger window",
)
@router.get(
    "/danger",
    name="public-ripple-danger-legacy",
    include_in_schema=False,
    deprecated=True,
)
async def get_public_ripple_danger() -> Dict[str, Any]:
    _ensure_enabled()
    payload = _load_payload(RIPPLE_DANGER_LATEST_KEY) or _empty_payload()
    return _decorate(payload)


@router.get(
    "/player/{player_id}/summary",
    name="public-ripple-player-summary",
    summary="Get public competition player summary",
)
async def get_public_ripple_player_summary(
    player_id: str, request: Request
) -> Dict[str, Any]:
    _ensure_enabled()
    player = _build_player_summary_payload(
        _apply_public_player_visibility(
            _load_public_player_section_payload(
                player_id,
                "summary",
                _player_index_summary_key(player_id),
            ),
            request,
            player_id,
        )
    )
    if not isinstance(player, dict):
        raise _player_not_found()
    _observe_ripple_player_section_payload("summary", player)
    return player


@router.get(
    "/player/{player_id}/history",
    name="public-ripple-player-history",
    summary="Get public competition player history payload",
)
async def get_public_ripple_player_history(
    player_id: str, request: Request
) -> Dict[str, Any]:
    _ensure_enabled()
    player = _build_player_history_payload(
        _apply_public_player_visibility(
            _load_public_player_section_payload(
                player_id,
                "history",
                _player_index_history_key(player_id),
            ),
            request,
            player_id,
        )
    )
    if not isinstance(player, dict):
        raise _player_not_found()
    _observe_ripple_player_section_payload("history", player)
    return player


@router.get(
    "/player/{player_id}/results",
    name="public-ripple-player-results",
    summary="Get public competition player results payload",
)
async def get_public_ripple_player_results(
    player_id: str, request: Request
) -> Dict[str, Any]:
    _ensure_enabled()
    player = _build_player_results_payload(
        _apply_public_player_visibility(
            _load_public_player_section_payload(
                player_id,
                "results",
                _player_index_results_key(player_id),
            ),
            request,
            player_id,
        )
    )
    if not isinstance(player, dict):
        raise _player_not_found()
    _observe_ripple_player_section_payload("results", player)
    return player


@router.get(
    "/player/{player_id}",
    name="public-ripple-player",
    summary="Get public competition player profile",
)
async def get_public_ripple_player(
    player_id: str, request: Request
) -> Dict[str, Any]:
    _ensure_enabled()
    player = _apply_public_player_visibility(
        _load_public_player_payload(player_id),
        request,
        player_id,
    )
    if not isinstance(player, dict):
        raise _player_not_found()
    return player


@admin_router.get(
    "/player/{player_id}/summary",
    name="admin-ripple-player-summary",
    summary="Get admin competition player summary",
)
async def get_admin_ripple_player_summary(
    player_id: str, _discord_id: str = Depends(require_comp_admin)
) -> Dict[str, Any]:
    _ensure_enabled()
    player = _build_player_summary_payload(
        _apply_admin_player_overrides(
            _load_public_player_section_payload(
                player_id,
                "summary",
                _player_index_summary_key(player_id),
            )
        )
    )
    if not isinstance(player, dict):
        raise _player_not_found()
    player["viewer_can_view_results"] = True
    _observe_ripple_player_section_payload("summary", player)
    return player


@admin_router.get(
    "/player/{player_id}/history",
    name="admin-ripple-player-history",
    summary="Get admin competition player history payload",
)
async def get_admin_ripple_player_history(
    player_id: str, _discord_id: str = Depends(require_comp_admin)
) -> Dict[str, Any]:
    _ensure_enabled()
    player = None
    try:
        player = await _load_admin_player_payload_from_db(player_id)
    except Exception:
        logger.exception(
            "Failed to load admin competition player history payload from DB",
            extra={"player_id": player_id},
        )
    if not isinstance(player, dict):
        player = _apply_admin_player_overrides(
            _load_public_player_section_payload(
                player_id,
                "history",
                _player_index_history_key(player_id),
            )
        )
    player = _build_player_history_payload(player)
    if not isinstance(player, dict):
        raise _player_not_found()
    _observe_ripple_player_section_payload("history", player)
    return player


@admin_router.get(
    "/player/{player_id}/results",
    name="admin-ripple-player-results",
    summary="Get admin competition player results payload",
)
async def get_admin_ripple_player_results(
    player_id: str, _discord_id: str = Depends(require_comp_admin)
) -> Dict[str, Any]:
    _ensure_enabled()
    player = None
    try:
        player = await _load_admin_player_payload_from_db(player_id)
    except Exception:
        logger.exception(
            "Failed to load admin competition player results payload from DB",
            extra={"player_id": player_id},
        )
    if not isinstance(player, dict):
        player = _apply_admin_player_overrides(
            _load_public_player_section_payload(
                player_id,
                "results",
                _player_index_results_key(player_id),
            )
        )
    if isinstance(player, dict):
        player["viewer_can_view_results"] = True
    player = _build_player_results_payload(player)
    if not isinstance(player, dict):
        raise _player_not_found()
    _observe_ripple_player_section_payload("results", player)
    return player


@admin_router.get(
    "/player/{player_id}",
    name="admin-ripple-player",
    summary="Get admin competition player profile",
)
async def get_admin_ripple_player(
    player_id: str, _discord_id: str = Depends(require_comp_admin)
) -> Dict[str, Any]:
    _ensure_enabled()
    player = None
    try:
        player = await _load_admin_player_payload_from_db(player_id)
    except Exception:
        logger.exception(
            "Failed to load admin competition player payload from DB",
            extra={"player_id": player_id},
        )
    if not isinstance(player, dict):
        player = _apply_admin_player_overrides(
            _load_public_player_payload(player_id)
        )
    if not isinstance(player, dict):
        raise _player_not_found()
    player["viewer_can_view_results"] = True
    return player


@admin_router.post(
    "/refresh",
    name="admin-ripple-refresh",
    summary="Queue competition snapshot refresh",
)
async def queue_admin_ripple_refresh(
    wait: bool = False,
    _discord_id: str = Depends(require_comp_admin),
) -> Dict[str, Any]:
    requested_at_ms = int(time.time() * 1000)
    if wait:
        result = await run_in_threadpool(refresh_ripple_snapshots)
        return {
            "queued": False,
            "completed": True,
            "task_name": "tasks.refresh_ripple_snapshots",
            "task_id": None,
            "requested_at_ms": requested_at_ms,
            "result": result,
        }

    task = celery.send_task("tasks.refresh_ripple_snapshots")
    task_id = getattr(task, "id", None)
    return {
        "queued": True,
        "completed": False,
        "task_name": "tasks.refresh_ripple_snapshots",
        "task_id": task_id,
        "requested_at_ms": requested_at_ms,
    }


@router.get(
    "/metadata",
    name="public-ripple-metadata",
    summary="Get public ripple metadata",
)
@router.get(
    "/meta",
    name="public-ripple-meta-legacy",
    include_in_schema=False,
    deprecated=True,
)
async def get_public_ripple_meta() -> Dict[str, Any]:
    _ensure_enabled()
    meta = _load_payload(RIPPLE_STABLE_META_KEY) or {}
    stable = _load_payload(RIPPLE_STABLE_LATEST_KEY)
    danger = _load_payload(RIPPLE_DANGER_LATEST_KEY)
    now_ms = int(time.time() * 1000)
    return {
        "meta": meta,
        "stable": {
            "present": stable is not None,
            "stale": _decorate(stable or _empty_payload())["stale"],
        },
        "danger": {
            "present": danger is not None,
            "stale": _decorate(danger or _empty_payload())["stale"],
        },
        "feature_flag": {
            # Expose only the effective state; omit Redis key names to avoid
            # leaking internal implementation details.
            "enabled": True,
        },
        "retrieved_at_ms": now_ms,
    }


@router.get(
    "/leaderboard/percentiles",
    name="public-ripple-leaderboard-percentiles",
    summary="Get public ripple leaderboard percentiles",
)
@router.get(
    "/percentiles",
    name="public-ripple-percentiles-legacy",
    include_in_schema=False,
    deprecated=True,
)
async def get_public_ripple_percentiles() -> Dict[str, Any]:
    _ensure_enabled()
    payload = (
        _load_payload(RIPPLE_STABLE_PERCENTILES_KEY)
        or _empty_percentiles_payload()
    )
    return _decorate_percentiles(payload)


def _share_origin(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.netloc)
    return f"{scheme}://{host}".rstrip("/")


def _share_profile_url(request: Request, player_id: str) -> str:
    return f"{_share_origin(request)}/u/{quote(player_id, safe='')}"


def _share_image_url(request: Request, player_id: str) -> str:
    return (
        f"{_share_origin(request)}/api/ripple/public/player/"
        f"{quote(player_id, safe='')}/share-image.png"
    )


def _share_rank_score(player: Dict[str, Any]) -> Optional[float]:
    display_score = player.get("display_score")
    if display_score is None:
        return None
    try:
        return float(display_score) + _SHARE_SCORE_OFFSET
    except (TypeError, ValueError):
        return None


def _share_rank_label(player: Dict[str, Any]) -> str:
    rank = player.get("stable_rank")
    if rank is None:
        return "Off board"
    try:
        return f"#{int(rank)}"
    except (TypeError, ValueError):
        return "Off board"


def _share_status_label(player: Dict[str, Any]) -> str:
    if player.get("eligible"):
        return "Live snapshot"

    lifetime = player.get("lifetime_ranked_tournaments")
    minimum_required = player.get("minimum_required_tournaments") or 3
    try:
        if int(lifetime or 0) >= int(minimum_required):
            return "Not currently eligible"
    except (TypeError, ValueError):
        pass
    return "Unlocking profile"


def _share_last_active_label(player: Dict[str, Any]) -> str:
    timestamp = player.get("last_active_ms") or player.get("generated_at_ms")
    if timestamp is None:
        return "Unavailable"
    try:
        formatted = time.strftime(
            "%Y-%m-%d %H:%M UTC",
            time.gmtime(int(timestamp) / 1000),
        )
    except (TypeError, ValueError, OSError):
        return "Unavailable"
    return formatted


def _share_description(player: Dict[str, Any]) -> str:
    score = _share_rank_score(player)
    score_label = (
        f"Rank score {score:.2f} / {_SHARE_SCORE_TARGET:.0f}"
        if score is not None
        else "Rank score hidden"
    )
    active_window = int(player.get("window_tournament_count") or 0)
    minimum_required = int(player.get("minimum_required_tournaments") or 3)
    lifetime = int(player.get("lifetime_ranked_tournaments") or 0)
    return (
        f"{_share_rank_label(player)} · {score_label} · "
        f"Active window {active_window}/{minimum_required} · "
        f"Lifetime ranked {lifetime}"
    )


def _share_title(player: Dict[str, Any]) -> str:
    display_name = (
        player.get("display_name") or player.get("player_id") or "Player"
    )
    return (
        f"{display_name} · {_share_rank_label(player)} · splat.top Competitive"
    )


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: max(0, limit - 1)].rstrip()}…"


def _load_share_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    font_path = _SHARE_FONT_BOLD_PATH if bold else _SHARE_FONT_REGULAR_PATH
    try:
        return ImageFont.truetype(font_path, size=size)
    except OSError:
        return ImageFont.load_default()


def _measure_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def _truncate_text_for_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> str:
    candidate = text
    if _measure_text(draw, candidate, font)[0] <= max_width:
        return candidate

    while len(candidate) > 1:
        candidate = candidate[:-1].rstrip()
        trial = f"{candidate}…"
        if _measure_text(draw, trial, font)[0] <= max_width:
            return trial
    return "…"


def _draw_chip(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    text_fill: tuple[int, int, int, int],
    min_width: int = 0,
) -> int:
    text_width, text_height = _measure_text(draw, text, font)
    box_width = max(min_width, text_width + 44)
    box_height = max(54, text_height + 24)
    draw.rounded_rectangle(
        (x, y, x + box_width, y + box_height),
        radius=14,
        fill=fill,
        outline=outline,
        width=2,
    )
    draw.text(
        (x + 22, y + ((box_height - text_height) / 2) - 2),
        text,
        font=font,
        fill=text_fill,
    )
    return x + box_width


def _draw_stat_panel(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    width: int,
    label: str,
    value: str,
    label_font: ImageFont.ImageFont,
    value_font: ImageFont.ImageFont,
) -> None:
    draw.rounded_rectangle(
        (x, y, x + width, y + 112),
        radius=18,
        fill=(11, 22, 35, 198),
        outline=(148, 163, 184, 42),
        width=2,
    )
    draw.text((x + 24, y + 20), label, font=label_font, fill=(142, 162, 184))
    draw.text((x + 24, y + 56), value, font=value_font, fill=(248, 250, 252))


def _share_progress_label(player: Dict[str, Any]) -> str:
    score = _share_rank_score(player)
    if score is None:
        return "Rank score hidden"
    remaining = max(0.0, _SHARE_SCORE_TARGET - score)
    if remaining < 0.01:
        return "Ready for XX+"
    return f"{remaining:.2f} to XX+"


def _share_card_png(player: Dict[str, Any]) -> bytes:
    display_name = str(
        player.get("display_name")
        or player.get("player_id")
        or "Unknown player"
    )
    player_id = str(player.get("player_id") or "unknown")
    rank_label = _share_rank_label(player)
    status_label = _share_status_label(player)
    description = _share_description(player)
    last_active = _share_last_active_label(player)

    score = _share_rank_score(player)
    score_label = (
        f"{score:.2f} / {_SHARE_SCORE_TARGET:.0f}"
        if score is not None
        else "Hidden"
    )
    progress_pct = 0.0
    if score is not None:
        progress_pct = max(
            0.0, min((score / _SHARE_SCORE_TARGET) * 100.0, 100.0)
        )
    progress_width = round(520 * progress_pct / 100.0, 2)

    active_window = (
        f"{int(player.get('window_tournament_count') or 0)}/"
        f"{int(player.get('minimum_required_tournaments') or 3)}"
    )
    lifetime = str(int(player.get("lifetime_ranked_tournaments") or 0))

    image = Image.new(
        "RGBA", (_SHARE_CARD_WIDTH, _SHARE_CARD_HEIGHT), "#08111d"
    )
    draw = ImageDraw.Draw(image)

    for y in range(_SHARE_CARD_HEIGHT):
        blend = y / max(1, _SHARE_CARD_HEIGHT - 1)
        red = int(8 + (7 * blend))
        green = int(17 + (14 * blend))
        blue = int(29 + (19 * blend))
        draw.line(
            ((0, y), (_SHARE_CARD_WIDTH, y)),
            fill=(red, green, blue, 255),
        )

    draw.ellipse(
        (760, -180, 1360, 360),
        fill=(34, 211, 238, 34),
    )
    draw.rounded_rectangle(
        (36, 36, 1164, 594),
        radius=26,
        fill=(9, 18, 31, 234),
        outline=(148, 163, 184, 54),
        width=2,
    )

    eyebrow_font = _load_share_font(24)
    title_font = _load_share_font(58, bold=True)
    subtitle_font = _load_share_font(24)
    chip_font = _load_share_font(24, bold=True)
    score_label_font = _load_share_font(20, bold=True)
    score_font = _load_share_font(42, bold=True)
    panel_label_font = _load_share_font(18, bold=True)
    panel_value_font = _load_share_font(38, bold=True)
    body_font = _load_share_font(26)
    footer_font = _load_share_font(22)

    title_name = _truncate_text_for_width(
        draw,
        display_name,
        title_font,
        820,
    )
    subtitle = _truncate_text(player_id, 40)
    description = _truncate_text_for_width(draw, description, body_font, 1040)
    progress_label = _share_progress_label(player)

    draw.text(
        (72, 84),
        "SPLAT.TOP / COMPETITIVE",
        font=eyebrow_font,
        fill=(142, 162, 184),
    )
    draw.text((72, 152), title_name, font=title_font, fill=(248, 250, 252))
    draw.text((72, 214), subtitle, font=subtitle_font, fill=(159, 177, 196))

    next_x = _draw_chip(
        draw,
        x=72,
        y=258,
        text=rank_label,
        font=chip_font,
        fill=(167, 139, 250, 36),
        outline=(167, 139, 250, 88),
        text_fill=(243, 232, 255, 255),
        min_width=136,
    )
    _draw_chip(
        draw,
        x=next_x + 16,
        y=258,
        text=status_label,
        font=chip_font,
        fill=(34, 211, 238, 28),
        outline=(34, 211, 238, 74),
        text_fill=(224, 251, 255, 255),
        min_width=250,
    )

    draw.text(
        (72, 352),
        "RANK SCORE",
        font=score_label_font,
        fill=(142, 162, 184),
    )
    draw.text((72, 392), score_label, font=score_font, fill=(248, 250, 252))
    draw.rounded_rectangle(
        (72, 450, 592, 466),
        radius=8,
        fill=(20, 33, 48, 240),
    )
    draw.rounded_rectangle(
        (72, 450, 72 + progress_width, 466),
        radius=8,
        fill=(34, 211, 238, 255),
    )
    draw.text((72, 486), progress_label, font=footer_font, fill=(142, 162, 184))

    _draw_stat_panel(
        draw,
        x=700,
        y=338,
        width=184,
        label="ACTIVE WINDOW",
        value=active_window,
        label_font=panel_label_font,
        value_font=panel_value_font,
    )
    _draw_stat_panel(
        draw,
        x=900,
        y=338,
        width=228,
        label="LIFETIME RANKED",
        value=lifetime,
        label_font=panel_label_font,
        value_font=panel_value_font,
    )

    draw.text((72, 540), description, font=body_font, fill=(216, 226, 238))
    draw.text(
        (72, 578),
        f"Last active: {last_active}",
        font=footer_font,
        fill=(142, 162, 184),
    )

    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _share_preview_html(
    *,
    title: str,
    description: str,
    profile_url: str,
    image_url: str,
    redirect_url: str | None = None,
) -> str:
    refresh_meta = ""
    redirect_script = ""
    redirect_body = ""
    if redirect_url:
        escaped_redirect = escape(redirect_url)
        refresh_meta = (
            f'<meta http-equiv="refresh" content="0;url={escaped_redirect}" />'
        )
        redirect_script = (
            f"<script>window.location.replace("
            f"{orjson.dumps(redirect_url).decode()});</script>"
        )
        redirect_body = (
            f'<p>Redirecting to <a href="{escaped_redirect}">'
            f"{escape(title)}</a>…</p>"
        )
    else:
        redirect_body = (
            f"<main><h1>{escape(title)}</h1>"
            f"<p>{escape(description)}</p>"
            f'<p>Open <a href="{escape(profile_url)}">{escape(profile_url)}</a> '
            "to view the full competitive profile.</p></main>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}" />
    <meta property="og:title" content="{escape(title)}" />
    <meta property="og:description" content="{escape(description)}" />
    <meta property="og:image" content="{escape(image_url)}" />
    <meta property="og:image:type" content="image/png" />
    <meta property="og:image:width" content="{_SHARE_CARD_WIDTH}" />
    <meta property="og:image:height" content="{_SHARE_CARD_HEIGHT}" />
    <meta property="og:image:alt" content="{escape(description)}" />
    <meta property="og:url" content="{escape(profile_url)}" />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{escape(title)}" />
    <meta name="twitter:description" content="{escape(description)}" />
    <meta name="twitter:image" content="{escape(image_url)}" />
    <link rel="canonical" href="{escape(profile_url)}" />
    {refresh_meta}
    {redirect_script}
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #020617;
        color: #e2e8f0;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        padding: 32px;
      }}
      main, p {{
        max-width: 680px;
        text-align: center;
      }}
      h1 {{
        margin: 0 0 12px;
        font-size: 28px;
      }}
      p {{
        margin: 0;
        line-height: 1.5;
      }}
      a {{
        color: #67e8f9;
      }}
    </style>
  </head>
  <body>
    {redirect_body}
  </body>
</html>"""


@share_router.get(
    "/u/{player_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="Competition player preview",
)
async def get_public_ripple_player_preview(
    request: Request, player_id: str
) -> HTMLResponse:
    _ensure_enabled()
    player = _load_public_player_payload(player_id)
    if not isinstance(player, dict):
        raise HTTPException(
            status_code=404,
            detail="Player not found in competition index",
        )

    profile_url = _share_profile_url(request, player_id)
    image_url = _share_image_url(request, player_id)
    title = _share_title(player)
    description = _share_description(player)

    return HTMLResponse(
        content=_share_preview_html(
            title=title,
            description=description,
            profile_url=profile_url,
            image_url=image_url,
        )
    )


@share_router.get(
    "/share/u/{player_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
    deprecated=True,
)
async def get_public_ripple_player_share_alias(
    request: Request, player_id: str
) -> HTMLResponse:
    _ensure_enabled()
    player = _load_public_player_payload(player_id)
    if not isinstance(player, dict):
        raise HTTPException(
            status_code=404,
            detail="Player not found in competition index",
        )

    profile_url = _share_profile_url(request, player_id)
    image_url = _share_image_url(request, player_id)
    title = _share_title(player)
    description = _share_description(player)

    return HTMLResponse(
        content=_share_preview_html(
            title=title,
            description=description,
            profile_url=profile_url,
            image_url=image_url,
            redirect_url=profile_url,
        )
    )


@router.get(
    "/player/{player_id}/share-image.png",
    include_in_schema=False,
    summary="Competition player preview image",
)
async def get_public_ripple_player_share_image(player_id: str) -> Response:
    _ensure_enabled()
    player = _load_public_player_payload(player_id)
    if not isinstance(player, dict):
        raise HTTPException(
            status_code=404,
            detail="Player not found in competition index",
        )

    return Response(
        content=_share_card_png(player),
        media_type="image/png",
    )
