from __future__ import annotations

import asyncio
from collections.abc import Sequence
import logging
import math
import re
from time import monotonic
from typing import Any, Literal, Mapping

import orjson
from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from fast_api_app.connections import limiter, rankings_async_session, redis_conn
from shared_lib.queries import ripple_queries

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

logger = logging.getLogger(__name__)

_TEAM_ID_RE = re.compile(r"\d+")
_TEAM_MATCHES_CACHE_PREFIX = "analytics:team_matches:v1"
_TEAM_MATCHES_CACHE_TTL_SECONDS = 120
_TEAM_MATCHES_LATEST_SNAPSHOT_CACHE_PREFIX = (
    "analytics:team_matches:latest_snapshot:v1"
)
_TEAM_MATCHES_LATEST_SNAPSHOT_CACHE_TTL_SECONDS = 30
_TEAM_MATCHES_ENRICH_TIMEOUT_SECONDS = 30.0
_MAX_SELECTED_TEAM_IDS = 10
_SCHEMA_COLUMNS_CACHE_TTL_SECONDS = 300.0
_SCORE_EPSILON = 1e-9
_MAX_ROUND_MAPS_COUNT = 20
_TOURNAMENT_SCORE_TIERS: tuple[tuple[float, str, str], ...] = (
    (5.0, "X", "x"),
    (10.0, "S+", "s_plus"),
    (20.0, "S", "s"),
    (40.0, "A+", "a_plus"),
    (80.0, "A", "a"),
    (160.0, "A-", "a_minus"),
)
_TIER_BUCKETS: tuple[tuple[str, str], ...] = (
    ("x", "X"),
    ("s_plus", "S+"),
    ("s", "S"),
    ("a_plus", "A+"),
    ("a", "A"),
    ("a_minus", "A-"),
    ("unscored", "Unscored"),
)
# Process-local cache only. In multi-worker deployments each worker keeps its
# own short-lived schema snapshot; correctness does not depend on cross-worker
# coherence because the cache is an optimization over information_schema reads.
_SCHEMA_COLUMNS_CACHE: dict[
    tuple[str, tuple[str, ...]], tuple[float, dict[str, set[str]]]
] = {}
_SCHEMA_COLUMNS_CACHE_LOCK = asyncio.Lock()


class TeamMatchRosterPlayer(BaseModel):
    player_id: int
    player_name: str


class TeamMatchRound(BaseModel):
    round_no: int | None = None
    maps_count: int | None = None
    map_index: int
    map_name: str | None = None
    map_mode: str | None = None
    team_a_score: float | None = Field(
        default=None,
        description=(
            "Only populated for the synthetic fallback round that uses "
            "aggregate match-level score data."
        ),
    )
    team_b_score: float | None = Field(
        default=None,
        description=(
            "Only populated for the synthetic fallback round that uses "
            "aggregate match-level score data."
        ),
    )
    winner_team_id: int | None = Field(
        default=None,
        description=(
            "Only populated for the synthetic fallback round that uses "
            "aggregate match-level winner data."
        ),
    )
    winner_side: Literal["team", "opponent"] | None = Field(
        default=None,
        description=(
            "Only populated for the synthetic fallback round that uses "
            "aggregate match-level winner data."
        ),
    )


class TeamMatchesSummary(BaseModel):
    primary_team_id: int | None = None
    primary_team_name: str | None = None
    team_ids: list[int]
    team_names: list[str]
    selected_team_count: int
    total_matches: int
    wins: int
    losses: int
    unresolved_matches: int
    decided_matches: int
    win_rate: float
    tournaments: int
    # Internal aggregation uses tier IDs; the public response uses labels.
    # Keep these aligned with _TIER_BUCKETS when adjusting tier definitions.
    tournament_tier_distribution: dict[str, int]
    tournament_tier_match_distribution: dict[str, int]


class TeamMatchItem(BaseModel):
    match_id: int
    team_id: int
    team_name: str
    opponent_team_id: int | None = None
    opponent_team_name: str
    tournament_id: int | None = None
    tournament_name: str | None = None
    tournament_mode: str | None = None
    map_picking_style: str | None = None
    tournament_tags: list[str] | None = None
    tournament_score: float | None = None
    tournament_score_tier_id: str
    tournament_score_tier: str
    winner_team_id: int | None = None
    winner_side: Literal["team", "opponent"] | None = None
    team_score: float | None = None
    opponent_score: float | None = None
    team_roster: list[TeamMatchRosterPlayer]
    opponent_roster: list[TeamMatchRosterPlayer]
    event_time_ms: int | None = None
    match_rounds: list[TeamMatchRound]
    team_is_winner: bool
    opponent_is_winner: bool


class TeamMatchesResponse(BaseModel):
    snapshot_id: int | None = None
    summary: TeamMatchesSummary
    matches: list[TeamMatchItem]


def _is_missing_relation_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "undefinedtable" in message
        or ("relation" in message and "does not exist" in message)
        or ("table" in message and "does not exist" in message)
        or "no such table" in message
    )


def _is_missing_column_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "undefinedcolumn" in message
        or "no such column" in message
        or ("column" in message and "does not exist" in message)
    )


def _is_access_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "permission denied" in message
        or "insufficientprivilege" in message
        or "access denied" in message
    )


def _normalize_id_sequence(values: Any) -> list[int]:
    if values is None:
        return []

    # Floats are accepted for backward compatibility with older helper callers
    # and will be truncated through int(); endpoint inputs should still be
    # integer IDs.
    if isinstance(values, (int, float, str)):
        values = [values]

    out: list[int] = []
    seen: set[int] = set()
    for value in values:
        if isinstance(value, list):
            for nested_id in _normalize_id_sequence(value):
                if nested_id not in seen:
                    seen.add(nested_id)
                    out.append(nested_id)
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed <= 0 or parsed in seen:
            continue
        seen.add(parsed)
        out.append(parsed)
    return out


def _parse_team_ids(raw: str | None, fallback_id: int | None) -> list[int]:
    tokens = _TEAM_ID_RE.findall(str(raw)) if raw else []
    parsed = _normalize_id_sequence(tokens)
    if parsed:
        return parsed
    if fallback_id is not None:
        return [int(fallback_id)]
    return []


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
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _empty_tier_counts() -> dict[str, int]:
    # Public summary payloads key tier counts by display label, not internal
    # tier ID. The internal aggregation maps back through _TIER_BUCKETS.
    return {label: 0 for _, label in _TIER_BUCKETS}


def _empty_summary() -> dict[str, Any]:
    return {
        "primary_team_id": None,
        "primary_team_name": None,
        "team_ids": [],
        "team_names": [],
        "selected_team_count": 0,
        "total_matches": 0,
        "wins": 0,
        "losses": 0,
        "unresolved_matches": 0,
        "decided_matches": 0,
        "win_rate": 0.0,
        "tournaments": 0,
        "tournament_tier_distribution": _empty_tier_counts(),
        "tournament_tier_match_distribution": _empty_tier_counts(),
    }


def _empty_payload(snapshot_id: int | None) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot_id,
        "summary": _empty_summary(),
        "matches": [],
    }


def _schema_sql(schema: str) -> str:
    # Safe quoting: schema comes from ripple_queries.schema_name(), which
    # validates against a strict identifier regex before returning it.
    return f'"{schema}"'


def _tournament_tier(value: Any) -> dict[str, str]:
    parsed = _to_float(value)
    if parsed is None:
        return {"tier_id": "unscored", "tier_label": "Unscored"}

    for threshold, label, tier_id in _TOURNAMENT_SCORE_TIERS:
        if parsed <= threshold:
            return {"tier_id": tier_id, "tier_label": label}
    logger.debug(
        "Tournament score exceeded known tier thresholds; treating as bottom-tier A- bucket: %s",
        parsed,
    )
    return {"tier_id": "a_minus", "tier_label": "A-"}


def _ms_expr(column_sql: str) -> str:
    # column_sql must be a hardcoded or pre-validated SQL identifier/expression
    # from this module; it is interpolated directly into SQL text.
    return (
        f"CASE WHEN {column_sql} IS NULL THEN NULL "
        f"WHEN {column_sql} < 1000000000000 THEN {column_sql} * 1000 "
        f"ELSE {column_sql} END"
    )


def _score_cmp(lhs: float | None, rhs: float | None) -> int | None:
    if lhs is None or rhs is None:
        return None
    diff = lhs - rhs
    if abs(diff) <= _SCORE_EPSILON:
        return 0
    return 1 if diff > 0 else -1


def _winner_side_from_scores(
    team_score: float | None, opponent_score: float | None
) -> str | None:
    cmp = _score_cmp(team_score, opponent_score)
    if cmp is None or cmp == 0:
        return None
    return "team" if cmp > 0 else "opponent"


def _normalize_tournament_tags(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = _to_text(value)
        return [normalized] if normalized else None
    if isinstance(value, (list, tuple, set)):
        iterable = sorted(value) if isinstance(value, set) else value
        out: list[str] = []
        seen: set[str] = set()
        for item in iterable:
            normalized = _to_text(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
        return out or None
    return None


def _canonical_team_ids_for_cache(team_ids: Sequence[int]) -> list[int]:
    normalized_team_ids = _normalize_id_sequence(team_ids)
    if len(normalized_team_ids) <= 1:
        return normalized_team_ids
    primary_team_id, *alias_team_ids = normalized_team_ids
    return [primary_team_id, *sorted(alias_team_ids)]


async def _get_table_columns(
    session: AsyncSession, schema: str, table: str
) -> set[str]:
    query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
        """
    )
    try:
        result = await session.execute(
            query, {"schema": schema, "table": table}
        )
    except Exception as exc:
        logger.warning(
            "Failed to introspect columns for %s.%s: %s",
            schema,
            table,
            exc,
        )
        return set()
    return {
        str(row.get("column_name"))
        for row in result.mappings().all()
        if row.get("column_name")
    }


async def _get_table_columns_map(
    session: AsyncSession, schema: str, tables: Sequence[str]
) -> dict[str, set[str]]:
    normalized_tables = [
        str(table).strip() for table in tables if str(table).strip()
    ]
    if not normalized_tables:
        return {}

    cache_key = (schema, tuple(normalized_tables))
    async with _SCHEMA_COLUMNS_CACHE_LOCK:
        cached = _SCHEMA_COLUMNS_CACHE.get(cache_key)
        if cached is not None:
            cached_at, cached_columns = cached
            if monotonic() - cached_at < _SCHEMA_COLUMNS_CACHE_TTL_SECONDS:
                return {
                    table: set(columns)
                    for table, columns in cached_columns.items()
                }
            _SCHEMA_COLUMNS_CACHE.pop(cache_key, None)

        out = {table: set() for table in normalized_tables}
        query = text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name IN :tables
            """
        ).bindparams(bindparam("tables", expanding=True))
        try:
            result = await session.execute(
                query,
                {"schema": schema, "tables": normalized_tables},
            )
        except Exception as exc:
            logger.warning(
                "Failed to batch-introspect columns for schema %s: %s",
                schema,
                exc,
            )
            return out

        for row in result.mappings().all():
            table_name = row.get("table_name")
            column_name = row.get("column_name")
            if not table_name or not column_name:
                continue
            normalized_table_name = str(table_name)
            if normalized_table_name not in out:
                continue
            out[normalized_table_name].add(str(column_name))

        _SCHEMA_COLUMNS_CACHE[cache_key] = (
            monotonic(),
            {table: set(columns) for table, columns in out.items()},
        )
        return out


def _team_matches_cache_key(
    *,
    schema: str,
    snapshot_id: int,
    team_ids: Sequence[int],
    limit: int,
) -> str:
    normalized_team_ids = _canonical_team_ids_for_cache(team_ids)
    team_ids_key = ",".join(str(team_id) for team_id in normalized_team_ids)
    return (
        f"{_TEAM_MATCHES_CACHE_PREFIX}:{schema}:snapshot:{int(snapshot_id)}:"
        f"limit:{int(limit)}:team_ids:{team_ids_key}"
    )


def _latest_snapshot_cache_key(schema: str) -> str:
    return f"{_TEAM_MATCHES_LATEST_SNAPSHOT_CACHE_PREFIX}:{schema}"


async def _load_cached_team_matches_payload(
    cache_key: str,
) -> dict[str, Any] | None:
    try:
        cached_payload_raw = await run_in_threadpool(redis_conn.get, cache_key)
    except Exception:
        logger.exception(
            "Failed to read team matches payload from cache: %s", cache_key
        )
        return None
    if cached_payload_raw is None:
        return None

    cached_payload_bytes = (
        cached_payload_raw.encode()
        if isinstance(cached_payload_raw, str)
        else cached_payload_raw
    )
    try:
        payload = orjson.loads(cached_payload_bytes)
    except orjson.JSONDecodeError:
        logger.warning(
            "Failed to decode cached team matches payload: %s", cache_key
        )
        return None
    return payload if isinstance(payload, dict) else None


async def _store_cached_team_matches_payload(
    cache_key: str, payload: Mapping[str, Any]
) -> None:
    try:
        await run_in_threadpool(
            redis_conn.setex,
            cache_key,
            _TEAM_MATCHES_CACHE_TTL_SECONDS,
            orjson.dumps(payload),
        )
    except Exception:
        logger.exception(
            "Failed to store team matches payload in cache: %s", cache_key
        )


async def _load_cached_latest_snapshot_id(schema: str) -> int | None:
    try:
        cached_snapshot_id = await run_in_threadpool(
            redis_conn.get, _latest_snapshot_cache_key(schema)
        )
    except Exception:
        logger.exception(
            "Failed to read latest team snapshot from cache for schema %s",
            schema,
        )
        return None
    if cached_snapshot_id is None:
        return None
    try:
        return int(cached_snapshot_id)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid cached latest team snapshot id for schema %s: %r",
            schema,
            cached_snapshot_id,
        )
        return None


async def _store_cached_latest_snapshot_id(
    schema: str, snapshot_id: int
) -> None:
    try:
        await run_in_threadpool(
            redis_conn.setex,
            _latest_snapshot_cache_key(schema),
            _TEAM_MATCHES_LATEST_SNAPSHOT_CACHE_TTL_SECONDS,
            str(int(snapshot_id)),
        )
    except Exception:
        logger.exception(
            "Failed to store latest team snapshot id in cache for schema %s",
            schema,
        )


async def _resolve_snapshot_id(
    session: AsyncSession, snapshot_id: int | None
) -> int:
    if snapshot_id is not None:
        return int(snapshot_id)

    schema = ripple_queries.schema_name()
    schema_sql = _schema_sql(schema)
    query = text(
        f"""
        SELECT run_id
        FROM {schema_sql}.team_search_refresh_runs
        WHERE status = 'completed'
        ORDER BY finished_at DESC NULLS LAST, run_id DESC
        LIMIT 1
        """
    )
    try:
        result = await session.execute(query)
        row = result.mappings().first()
    except SQLAlchemyError as exc:
        if (
            _is_missing_relation_error(exc)
            or _is_missing_column_error(exc)
            or _is_access_error(exc)
        ):
            row = None
        else:
            raise

    if not row or row.get("run_id") is None:
        raise HTTPException(
            status_code=503,
            detail="No completed team-search snapshot available yet.",
        )
    return int(row["run_id"])


async def _fetch_team_name_map(
    session: AsyncSession,
    *,
    schema: str,
    snapshot_id: int | None,
    team_ids: Sequence[int],
) -> dict[int, str]:
    normalized_ids = _normalize_id_sequence(team_ids)
    if snapshot_id is None or not normalized_ids:
        return {}

    schema_sql = _schema_sql(schema)
    query = text(
        f"""
        SELECT team_id, team_name
        FROM {schema_sql}.team_search_embeddings
        WHERE snapshot_id = :snapshot_id
          AND team_id IN :team_ids
        """
    ).bindparams(bindparam("team_ids", expanding=True))

    try:
        result = await session.execute(
            query,
            {"snapshot_id": int(snapshot_id), "team_ids": normalized_ids},
        )
    except SQLAlchemyError as exc:
        if (
            _is_missing_relation_error(exc)
            or _is_missing_column_error(exc)
            or _is_access_error(exc)
        ):
            return {}
        raise

    return {
        int(row["team_id"]): str(row["team_name"])
        for row in result.mappings().all()
        if row.get("team_id") is not None and row.get("team_name")
    }


async def _fetch_match_rows(
    session: AsyncSession,
    *,
    schema: str,
    team_ids: Sequence[int],
    limit: int,
    match_columns: set[str] | None = None,
    tournament_columns: set[str] | None = None,
) -> list[dict[str, Any]]:
    team_ids_sorted = _normalize_id_sequence(team_ids)
    if not team_ids_sorted:
        return []

    # Normal route flow passes batched column metadata from
    # _fetch_team_matches_payload(). Keep the singular fallback so these helpers
    # remain usable in isolation and in focused tests.
    if match_columns is None:
        match_columns = await _get_table_columns(session, schema, "matches")
    if not {"match_id", "team1_id", "team2_id"}.issubset(match_columns):
        return []

    if tournament_columns is None:
        tournament_columns = await _get_table_columns(
            session, schema, "tournaments"
        )
    schema_sql = _schema_sql(schema)

    select_parts = [
        "m.match_id::bigint AS match_id",
        (
            "m.tournament_id::bigint AS tournament_id"
            if "tournament_id" in match_columns
            else "NULL::bigint AS tournament_id"
        ),
        "m.team1_id::bigint AS team1_id",
        "m.team2_id::bigint AS team2_id",
        (
            "m.winner_team_id::bigint AS winner_team_id"
            if "winner_team_id" in match_columns
            else "NULL::bigint AS winner_team_id"
        ),
        (
            "m.team1_score::double precision AS team1_score"
            if "team1_score" in match_columns
            else "NULL::double precision AS team1_score"
        ),
        (
            "m.team2_score::double precision AS team2_score"
            if "team2_score" in match_columns
            else "NULL::double precision AS team2_score"
        ),
    ]

    join_sql = ""
    order_candidates: list[str] = []
    if (
        "tournament_id" in match_columns
        and "tournament_id" in tournament_columns
    ):
        join_sql = (
            f"LEFT JOIN {schema_sql}.tournaments t "
            "ON t.tournament_id = m.tournament_id"
        )
        if "name" in tournament_columns:
            select_parts.append("t.name::text AS tournament_name")
        elif "tournament_name" in tournament_columns:
            select_parts.append("t.tournament_name::text AS tournament_name")
        else:
            select_parts.append("NULL::text AS tournament_name")

        if "format_hint" in tournament_columns:
            select_parts.append(
                "NULLIF(BTRIM(t.format_hint::text), '') AS tournament_mode"
            )
        else:
            select_parts.append("NULL::text AS tournament_mode")

        if "map_picking_style" in tournament_columns:
            select_parts.append(
                "NULLIF(BTRIM(t.map_picking_style::text), '') AS map_picking_style"
            )
        else:
            select_parts.append("NULL::text AS map_picking_style")

        if "tags" in tournament_columns:
            select_parts.append("t.tags AS tournament_tags")
        else:
            select_parts.append("NULL::jsonb AS tournament_tags")

        if "start_time_ms" in tournament_columns:
            order_candidates.append(_ms_expr("t.start_time_ms"))
    else:
        select_parts.extend(
            [
                "NULL::text AS tournament_name",
                "NULL::text AS tournament_mode",
                "NULL::text AS map_picking_style",
                "NULL::jsonb AS tournament_tags",
            ]
        )

    if "last_game_finished_at_ms" in match_columns:
        order_candidates.append(_ms_expr("m.last_game_finished_at_ms"))
    if "created_at_ms" in match_columns:
        order_candidates.append(_ms_expr("m.created_at_ms"))

    event_time_expr = (
        f"COALESCE({', '.join(order_candidates)})"
        if order_candidates
        else "NULL::bigint"
    )
    select_parts.append(f"{event_time_expr}::bigint AS event_time_ms")

    where_clauses = [
        "(m.team1_id IN :team_ids OR m.team2_id IN :team_ids)",
    ]
    if len(team_ids_sorted) > 1:
        where_clauses.append(
            "NOT (m.team1_id IN :team_ids AND m.team2_id IN :team_ids)"
        )

    query = text(
        f"""
        WITH match_rows AS (
            SELECT
                {", ".join(select_parts)}
            FROM {schema_sql}.matches m
            {join_sql}
            WHERE {" AND ".join(where_clauses)}
        )
        SELECT *
        FROM match_rows
        ORDER BY event_time_ms DESC NULLS LAST, match_id DESC
        LIMIT :limit
        """
    ).bindparams(bindparam("team_ids", expanding=True))

    try:
        result = await session.execute(
            query,
            {"team_ids": team_ids_sorted, "limit": max(1, int(limit))},
        )
    except SQLAlchemyError as exc:
        if (
            _is_missing_relation_error(exc)
            or _is_missing_column_error(exc)
            or _is_access_error(exc)
        ):
            logger.warning("Team matches query unavailable: %s", exc)
            return []
        raise

    return [dict(row) for row in result.mappings().all()]


async def _fetch_match_rosters(
    session: AsyncSession,
    *,
    schema: str,
    rows: Sequence[Mapping[str, Any]],
    pat_columns: set[str] | None = None,
    players_columns: set[str] | None = None,
) -> dict[tuple[int, int, int], list[dict[str, Any]]]:
    if not rows:
        return {}

    # See note in _fetch_match_rows() about helper-level fallback introspection.
    if pat_columns is None:
        pat_columns = await _get_table_columns(
            session, schema, "player_appearance_teams"
        )
    if not {"match_id", "team_id", "player_id"}.issubset(pat_columns):
        return {}

    match_ids = sorted(
        {
            int(match_id)
            for row in rows
            if (match_id := _to_int(row.get("match_id"))) is not None
        }
    )
    team_ids = sorted(
        {
            int(team_id)
            for row in rows
            for raw in (row.get("team1_id"), row.get("team2_id"))
            if (team_id := _to_int(raw)) is not None
        }
    )
    if not match_ids or not team_ids:
        return {}

    if players_columns is None:
        players_columns = await _get_table_columns(session, schema, "players")
    schema_sql = _schema_sql(schema)
    player_name_expr = "pat.player_id::text"
    join_players = ""
    if "player_id" in players_columns and "display_name" in players_columns:
        join_players = (
            f"LEFT JOIN {schema_sql}.players players "
            "ON players.player_id = pat.player_id"
        )
        player_name_expr = (
            "COALESCE(NULLIF(BTRIM(players.display_name::text), ''), "
            "pat.player_id::text)"
        )

    tournament_id_expr = (
        "pat.tournament_id::bigint"
        if "tournament_id" in pat_columns
        else "NULL::bigint"
    )

    query = text(
        f"""
        SELECT
            pat.match_id::bigint AS match_id,
            {tournament_id_expr} AS tournament_id,
            pat.team_id::bigint AS team_id,
            pat.player_id::bigint AS player_id,
            {player_name_expr} AS player_name
        FROM {schema_sql}.player_appearance_teams pat
        {join_players}
        WHERE pat.match_id IN :match_ids
          AND pat.team_id IN :team_ids
        ORDER BY pat.match_id, pat.team_id, pat.player_id
        """
    ).bindparams(
        bindparam("match_ids", expanding=True),
        bindparam("team_ids", expanding=True),
    )

    try:
        result = await session.execute(
            query,
            {"match_ids": match_ids, "team_ids": team_ids},
        )
    except SQLAlchemyError as exc:
        if (
            _is_missing_relation_error(exc)
            or _is_missing_column_error(exc)
            or _is_access_error(exc)
        ):
            return {}
        raise

    rosters: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    seen: dict[tuple[int, int, int], set[int]] = {}
    for row in result.mappings().all():
        match_id = _to_int(row.get("match_id"))
        team_id = _to_int(row.get("team_id"))
        player_id = _to_int(row.get("player_id"))
        if match_id is None or team_id is None or player_id is None:
            continue
        tournament_id = _to_int(row.get("tournament_id")) or 0
        key = (match_id, tournament_id, team_id)
        roster_seen = seen.setdefault(key, set())
        if player_id in roster_seen:
            continue
        roster_seen.add(player_id)
        rosters.setdefault(key, []).append(
            {
                "player_id": player_id,
                "player_name": _to_text(row.get("player_name"))
                or str(player_id),
            }
        )
    return rosters


async def _fetch_match_rounds(
    session: AsyncSession,
    *,
    schema: str,
    rows: Sequence[Mapping[str, Any]],
    selected_team_ids: Sequence[int],
    match_columns: set[str] | None = None,
    round_columns: set[str] | None = None,
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    if not rows:
        return {}

    # See note in _fetch_match_rows() about helper-level fallback introspection.
    if match_columns is None:
        match_columns = await _get_table_columns(session, schema, "matches")
    if round_columns is None:
        round_columns = await _get_table_columns(session, schema, "rounds")
    if "round_id" not in match_columns:
        return {}
    if not {"round_id", "number"}.issubset(round_columns):
        return {}
    schema_sql = _schema_sql(schema)

    team_id_set = set(_normalize_id_sequence(selected_team_ids))
    match_context: dict[int, dict[str, Any]] = {}
    for row in rows:
        match_id = _to_int(row.get("match_id"))
        if match_id is None:
            continue
        match_context[match_id] = {
            "tournament_id": _to_int(row.get("tournament_id")) or 0,
            "team1_id": _to_int(row.get("team1_id")),
            "team2_id": _to_int(row.get("team2_id")),
        }

    if not match_context:
        return {}

    maps_count_expr = (
        "r.maps_count::int" if "maps_count" in round_columns else "NULL::int"
    )
    map_mode_expr = (
        "r.maps_type::text" if "maps_type" in round_columns else "NULL::text"
    )

    query = text(
        f"""
        SELECT
            m.match_id::bigint AS match_id,
            r.round_id::bigint AS round_id,
            r.number::int AS round_no,
            {maps_count_expr} AS maps_count,
            {map_mode_expr} AS map_mode
        FROM {schema_sql}.matches m
        LEFT JOIN {schema_sql}.rounds r
          ON m.round_id = r.round_id
        WHERE m.match_id IN :match_ids
        ORDER BY r.number NULLS LAST
        """
    ).bindparams(bindparam("match_ids", expanding=True))

    try:
        result = await session.execute(
            query,
            {"match_ids": sorted(match_context.keys())},
        )
    except SQLAlchemyError as exc:
        if (
            _is_missing_relation_error(exc)
            or _is_missing_column_error(exc)
            or _is_access_error(exc)
        ):
            return {}
        raise

    out: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in result.mappings().all():
        match_id = _to_int(row.get("match_id"))
        if match_id is None:
            continue
        context = match_context.get(match_id)
        if context is None:
            continue

        team1_id = _to_int(context.get("team1_id"))
        team2_id = _to_int(context.get("team2_id"))
        if team1_id not in team_id_set and team2_id not in team_id_set:
            continue

        maps_count = _to_int(row.get("maps_count")) or 1
        maps_count = max(1, min(maps_count, _MAX_ROUND_MAPS_COUNT))
        round_no = _to_int(row.get("round_no"))
        tournament_id = context["tournament_id"]
        key = (match_id, int(tournament_id))

        for map_index in range(1, maps_count + 1):
            out.setdefault(key, []).append(
                {
                    "round_no": round_no,
                    "maps_count": maps_count,
                    "map_index": map_index,
                    "map_name": None,
                    "map_mode": _to_text(row.get("map_mode")),
                    "team_a_score": None,
                    "team_b_score": None,
                    "winner_team_id": None,
                    "winner_side": None,
                }
            )

    for rounds in out.values():
        rounds.sort(
            key=lambda round_row: (
                round_row.get("round_no") is None,
                _to_int(round_row.get("round_no"))
                if round_row.get("round_no") is not None
                else 1_000_000,
                _to_int(round_row.get("map_index"))
                if round_row.get("map_index") is not None
                else 1_000_000,
            )
        )

    return out


async def _fetch_tournament_scores(
    session: AsyncSession,
    *,
    schema: str,
    tournament_ids: Sequence[int],
    rankings_columns: set[str] | None = None,
    pat_columns: set[str] | None = None,
) -> dict[int, float]:
    normalized_ids = _normalize_id_sequence(tournament_ids)
    if not normalized_ids:
        return {}

    if rankings_columns is None:
        rankings_columns = await _get_table_columns(
            session, schema, "player_rankings"
        )
    if pat_columns is None:
        pat_columns = await _get_table_columns(
            session, schema, "player_appearance_teams"
        )
    if "player_id" not in rankings_columns or "score" not in rankings_columns:
        return {}
    if not {"tournament_id", "player_id"}.issubset(pat_columns):
        return {}

    rank_field = None
    if "player_rank" in rankings_columns:
        rank_field = "player_rank"
    elif "rank" in rankings_columns:
        rank_field = "rank"

    player_rank_expr = (
        f"NULLIF(pr.{rank_field}, 0)::double precision"
        if rank_field
        else "NULL::double precision"
    )
    rank_filter = (
        f"(pr.score IS NOT NULL OR NULLIF(pr.{rank_field}, 0) IS NOT NULL)"
        if rank_field
        else "pr.score IS NOT NULL"
    )

    schema_sql = _schema_sql(schema)
    # Lower player_rank values are stronger. We use the 10th-best rostered
    # player's rank as a tournament-strength cutoff, so lower numeric scores map
    # to stronger tiers in _tournament_tier().
    # latest_rankings uses MAX(calculated_at_ms) across player_rankings; an
    # index on (calculated_at_ms) is the main production mitigation if this
    # cold-path aggregate becomes expensive.
    query = text(
        f"""
        WITH latest_rankings AS (
            SELECT MAX(calculated_at_ms) AS calculated_at_ms
            FROM {schema_sql}.player_rankings
        ),
        roster AS (
            SELECT DISTINCT
                pat.tournament_id::bigint AS tournament_id,
                pat.player_id::bigint AS player_id
            FROM {schema_sql}.player_appearance_teams pat
            WHERE pat.tournament_id IN :tournament_ids
        ),
        scored_players AS (
            SELECT
                r.tournament_id,
                {player_rank_expr} AS player_rank,
                pr.score::double precision AS score,
                ROW_NUMBER() OVER (
                    PARTITION BY r.tournament_id
                    ORDER BY
                        CASE
                            WHEN {player_rank_expr} IS NOT NULL THEN 0
                            ELSE 1
                        END,
                        CASE
                            WHEN {player_rank_expr} IS NOT NULL THEN {player_rank_expr}
                            ELSE -pr.score
                        END ASC,
                        r.player_id ASC
                ) AS score_rank
            FROM roster r
            JOIN {schema_sql}.player_rankings pr
              ON pr.player_id = r.player_id
             AND pr.calculated_at_ms = (
                    SELECT calculated_at_ms FROM latest_rankings
                )
            WHERE {rank_filter}
        ),
        ranked_players AS (
            SELECT
                tournament_id,
                COALESCE(player_rank, score_rank::double precision)
                    AS tournament_rank,
                score_rank,
                COUNT(*) OVER (PARTITION BY tournament_id) AS roster_player_count
            FROM scored_players
        )
        SELECT
            tournament_id,
            MAX(tournament_rank) FILTER (
                WHERE score_rank = LEAST(10, roster_player_count)
            ) AS tournament_score
        FROM ranked_players
        GROUP BY tournament_id
        """
    ).bindparams(bindparam("tournament_ids", expanding=True))

    try:
        result = await session.execute(
            query, {"tournament_ids": normalized_ids}
        )
    except SQLAlchemyError as exc:
        if (
            _is_missing_relation_error(exc)
            or _is_missing_column_error(exc)
            or _is_access_error(exc)
        ):
            return {}
        raise

    scores: dict[int, float] = {}
    for row in result.mappings().all():
        tournament_id = _to_int(row.get("tournament_id"))
        score = _to_float(row.get("tournament_score"))
        if tournament_id is not None and score is not None:
            scores[tournament_id] = score
    return scores


def _build_team_matches_payload(
    *,
    snapshot_id: int | None,
    team_ids: Sequence[int],
    rows: Sequence[Mapping[str, Any]],
    team_names: Mapping[int, str] | None = None,
    rosters: Mapping[tuple[int, int, int], Sequence[Mapping[str, Any]]]
    | None = None,
    match_rounds: Mapping[tuple[int, int], Sequence[Mapping[str, Any]]]
    | None = None,
    tournament_scores: Mapping[int, float] | None = None,
) -> dict[str, Any]:
    team_ids_sorted = _normalize_id_sequence(team_ids)
    if not team_ids_sorted:
        return _empty_payload(snapshot_id)

    team_names = team_names or {}
    rosters = rosters or {}
    match_rounds = match_rounds or {}
    tournament_scores = tournament_scores or {}
    team_id_set = set(team_ids_sorted)

    selected_team_names = [
        team_names.get(team_id, f"Team {team_id}")
        for team_id in team_ids_sorted
    ]
    summary = _empty_summary()
    summary.update(
        {
            "primary_team_id": int(team_ids_sorted[0]),
            "primary_team_name": selected_team_names[0],
            "team_ids": team_ids_sorted,
            "team_names": selected_team_names,
            "selected_team_count": len(team_ids_sorted),
        }
    )

    matches_out: list[dict[str, Any]] = []
    tournaments_seen: set[int] = set()
    tournaments_by_tier: dict[str, int] = {}
    matches_by_tier: dict[str, int] = {}

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _to_int(row.get("event_time_ms")) is None,
            -(_to_int(row.get("event_time_ms")) or -1),
            -(_to_int(row.get("match_id")) or -1),
        ),
    )

    for row in sorted_rows:
        match_id = _to_int(row.get("match_id"))
        if match_id is None:
            continue

        tournament_id = _to_int(row.get("tournament_id"))
        team1_id = _to_int(row.get("team1_id"))
        team2_id = _to_int(row.get("team2_id"))

        if team1_id in team_id_set and team2_id not in team_id_set:
            subject_team_id = team1_id
            opponent_team_id = team2_id
            subject_is_team1 = True
        elif team2_id in team_id_set and team1_id not in team_id_set:
            subject_team_id = team2_id
            opponent_team_id = team1_id
            subject_is_team1 = False
        elif team1_id in team_id_set:
            subject_team_id = team1_id
            opponent_team_id = team2_id
            subject_is_team1 = True
        elif team2_id in team_id_set:
            subject_team_id = team2_id
            opponent_team_id = team1_id
            subject_is_team1 = False
        else:
            continue

        team_score = (
            _to_float(row.get("team1_score"))
            if subject_is_team1
            else _to_float(row.get("team2_score"))
        )
        opponent_score = (
            _to_float(row.get("team2_score"))
            if subject_is_team1
            else _to_float(row.get("team1_score"))
        )

        winner_team_id = _to_int(row.get("winner_team_id"))
        winner_side = None
        if winner_team_id in team_id_set:
            winner_side = "team"
        elif (
            opponent_team_id is not None and winner_team_id == opponent_team_id
        ):
            winner_side = "opponent"
        else:
            winner_side = _winner_side_from_scores(team_score, opponent_score)

        roster_tournament_id = tournament_id or 0
        team_roster = [
            {
                "player_id": _to_int(player.get("player_id")),
                "player_name": _to_text(player.get("player_name"))
                or str(player.get("player_id")),
            }
            for player in rosters.get(
                (match_id, roster_tournament_id, subject_team_id), []
            )
            if _to_int(player.get("player_id")) is not None
        ]
        opponent_roster = [
            {
                "player_id": _to_int(player.get("player_id")),
                "player_name": _to_text(player.get("player_name"))
                or str(player.get("player_id")),
            }
            for player in rosters.get(
                (match_id, roster_tournament_id, opponent_team_id or -1), []
            )
            if _to_int(player.get("player_id")) is not None
        ]

        rounds_key = (match_id, roster_tournament_id)
        normalized_rounds = [
            {
                "round_no": _to_int(round_row.get("round_no")),
                "maps_count": _to_int(round_row.get("maps_count")),
                "map_index": _to_int(round_row.get("map_index")) or 1,
                "map_name": _to_text(round_row.get("map_name")),
                "map_mode": _to_text(round_row.get("map_mode")),
                "team_a_score": _to_float(round_row.get("team_a_score")),
                "team_b_score": _to_float(round_row.get("team_b_score")),
                "winner_team_id": _to_int(round_row.get("winner_team_id")),
                "winner_side": (
                    round_row.get("winner_side")
                    if round_row.get("winner_side")
                    in {"team", "opponent", None}
                    else None
                ),
            }
            for round_row in match_rounds.get(rounds_key, [])
        ]
        if not normalized_rounds and (
            team_score is not None or opponent_score is not None
        ):
            normalized_rounds = [
                {
                    "round_no": None,
                    "maps_count": None,
                    "map_index": 1,
                    "map_name": None,
                    "map_mode": None,
                    "team_a_score": team_score,
                    "team_b_score": opponent_score,
                    "winner_team_id": winner_team_id,
                    "winner_side": winner_side,
                }
            ]

        if winner_side == "team":
            summary["wins"] += 1
        elif winner_side == "opponent":
            summary["losses"] += 1
        else:
            summary["unresolved_matches"] += 1

        tournament_score = (
            tournament_scores.get(tournament_id)
            if tournament_id is not None
            else None
        )
        tier = _tournament_tier(tournament_score)
        matches_by_tier[tier["tier_id"]] = (
            matches_by_tier.get(tier["tier_id"], 0) + 1
        )
        if tournament_id is not None and tournament_id not in tournaments_seen:
            tournaments_by_tier[tier["tier_id"]] = (
                tournaments_by_tier.get(tier["tier_id"], 0) + 1
            )
            tournaments_seen.add(tournament_id)

        matches_out.append(
            {
                "match_id": match_id,
                "team_id": subject_team_id,
                "team_name": team_names.get(
                    subject_team_id, f"Team {subject_team_id}"
                ),
                "opponent_team_id": opponent_team_id,
                "opponent_team_name": (
                    team_names.get(opponent_team_id, f"Team {opponent_team_id}")
                    if opponent_team_id is not None
                    else "Unknown opponent"
                ),
                "tournament_id": tournament_id,
                "tournament_name": _to_text(row.get("tournament_name")),
                "tournament_mode": _to_text(row.get("tournament_mode")),
                "map_picking_style": _to_text(row.get("map_picking_style")),
                "tournament_tags": _normalize_tournament_tags(
                    row.get("tournament_tags")
                ),
                "tournament_score": (
                    round(float(tournament_score), 4)
                    if tournament_score is not None
                    else None
                ),
                "tournament_score_tier_id": tier["tier_id"],
                "tournament_score_tier": tier["tier_label"],
                "winner_team_id": winner_team_id,
                "winner_side": winner_side,
                "team_score": team_score,
                "opponent_score": opponent_score,
                "team_roster": team_roster,
                "opponent_roster": opponent_roster,
                "event_time_ms": _to_int(row.get("event_time_ms")),
                "match_rounds": normalized_rounds,
                "team_is_winner": bool(winner_side == "team"),
                "opponent_is_winner": bool(winner_side == "opponent"),
            }
        )

    summary["total_matches"] = len(matches_out)
    summary["tournaments"] = len(tournaments_seen)
    summary["decided_matches"] = summary["wins"] + summary["losses"]
    summary["win_rate"] = (
        round(summary["wins"] / summary["decided_matches"], 4)
        if summary["decided_matches"] > 0
        else 0.0
    )
    summary["tournament_tier_distribution"] = {
        label: tournaments_by_tier.get(tier_id, 0)
        for tier_id, label in _TIER_BUCKETS
    }
    summary["tournament_tier_match_distribution"] = {
        label: matches_by_tier.get(tier_id, 0)
        for tier_id, label in _TIER_BUCKETS
    }

    return {
        "snapshot_id": snapshot_id,
        "summary": summary,
        "matches": matches_out,
    }


async def _fetch_match_rosters_in_new_session(
    *,
    schema: str,
    rows: Sequence[Mapping[str, Any]],
    pat_columns: set[str],
    players_columns: set[str],
) -> dict[tuple[int, int, int], list[dict[str, Any]]]:
    async with rankings_async_session() as session:
        return await _fetch_match_rosters(
            session,
            schema=schema,
            rows=rows,
            pat_columns=pat_columns,
            players_columns=players_columns,
        )


async def _fetch_match_rounds_in_new_session(
    *,
    schema: str,
    rows: Sequence[Mapping[str, Any]],
    selected_team_ids: Sequence[int],
    match_columns: set[str],
    round_columns: set[str],
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    async with rankings_async_session() as session:
        return await _fetch_match_rounds(
            session,
            schema=schema,
            rows=rows,
            selected_team_ids=selected_team_ids,
            match_columns=match_columns,
            round_columns=round_columns,
        )


async def _fetch_tournament_scores_in_new_session(
    *,
    schema: str,
    tournament_ids: Sequence[int],
    rankings_columns: set[str],
    pat_columns: set[str],
) -> dict[int, float]:
    async with rankings_async_session() as session:
        return await _fetch_tournament_scores(
            session,
            schema=schema,
            tournament_ids=tournament_ids,
            rankings_columns=rankings_columns,
            pat_columns=pat_columns,
        )


async def _fetch_team_matches_payload(
    session: AsyncSession,
    *,
    snapshot_id: int | None,
    team_ids: Sequence[int],
    limit: int,
) -> dict[str, Any]:
    schema = ripple_queries.schema_name()
    team_ids_sorted = _normalize_id_sequence(team_ids)
    if not team_ids_sorted:
        return _empty_payload(snapshot_id)

    columns_by_table = await _get_table_columns_map(
        session,
        schema,
        [
            "matches",
            "tournaments",
            "player_appearance_teams",
            "players",
            "rounds",
            "player_rankings",
        ],
    )
    match_columns = columns_by_table.get("matches", set())
    tournament_columns = columns_by_table.get("tournaments", set())
    pat_columns = columns_by_table.get("player_appearance_teams", set())
    players_columns = columns_by_table.get("players", set())
    round_columns = columns_by_table.get("rounds", set())
    rankings_columns = columns_by_table.get("player_rankings", set())

    rows = await _fetch_match_rows(
        session,
        schema=schema,
        team_ids=team_ids_sorted,
        limit=limit,
        match_columns=match_columns,
        tournament_columns=tournament_columns,
    )
    opponent_ids = sorted(
        {
            int(team_id)
            for row in rows
            for raw in (row.get("team1_id"), row.get("team2_id"))
            if (team_id := _to_int(raw)) is not None
            and team_id not in team_ids_sorted
        }
    )
    team_name_map = await _fetch_team_name_map(
        session,
        schema=schema,
        snapshot_id=snapshot_id,
        team_ids=[*team_ids_sorted, *opponent_ids],
    )
    if not rows:
        return _build_team_matches_payload(
            snapshot_id=snapshot_id,
            team_ids=team_ids_sorted,
            rows=[],
            team_names=team_name_map,
        )

    tournament_ids = list(
        dict.fromkeys(
            tournament_id
            for row in rows
            if (tournament_id := _to_int(row.get("tournament_id")))
            is not None
        )
    )
    try:
        rosters, rounds, tournament_scores = await asyncio.wait_for(
            asyncio.gather(
                _fetch_match_rosters_in_new_session(
                    schema=schema,
                    rows=rows,
                    pat_columns=pat_columns,
                    players_columns=players_columns,
                ),
                _fetch_match_rounds_in_new_session(
                    schema=schema,
                    rows=rows,
                    selected_team_ids=team_ids_sorted,
                    match_columns=match_columns,
                    round_columns=round_columns,
                ),
                _fetch_tournament_scores_in_new_session(
                    schema=schema,
                    tournament_ids=tournament_ids,
                    rankings_columns=rankings_columns,
                    pat_columns=pat_columns,
                ),
            ),
            timeout=_TEAM_MATCHES_ENRICH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Timed out enriching team matches payload for snapshot=%s team_ids=%s limit=%s",
            snapshot_id,
            team_ids_sorted,
            limit,
        )
        rosters, rounds, tournament_scores = {}, {}, {}
    return _build_team_matches_payload(
        snapshot_id=snapshot_id,
        team_ids=team_ids_sorted,
        rows=rows,
        team_names=team_name_map,
        rosters=rosters,
        match_rounds=rounds,
        tournament_scores=tournament_scores,
    )


@router.get(
    "/team/{team_id}/matches",
    response_model=TeamMatchesResponse,
)
@limiter.limit("30/minute")
async def analytics_team_matches(
    request: Request,
    team_id: int = Path(..., ge=1),
    team_ids: str | None = Query(default=None),
    snapshot_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=25, ge=1, le=200),
):
    # Public read endpoint: rely on the rate limit plus Redis-backed response
    # caching rather than requiring auth for this analytics surface.
    path_team_id = int(team_id)
    parsed_team_ids = _parse_team_ids(team_ids, path_team_id)
    parsed_team_ids = [
        path_team_id,
        *[
            parsed_id
            for parsed_id in parsed_team_ids
            if parsed_id != path_team_id
        ],
    ]
    if len(parsed_team_ids) > _MAX_SELECTED_TEAM_IDS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"At most {_MAX_SELECTED_TEAM_IDS} team IDs are allowed "
                "per request."
            ),
        )

    schema = ripple_queries.schema_name()
    checked_cache_key: str | None = None
    if snapshot_id is not None:
        checked_cache_key = _team_matches_cache_key(
            schema=schema,
            snapshot_id=int(snapshot_id),
            team_ids=parsed_team_ids,
            limit=limit,
        )
        cached_payload = await _load_cached_team_matches_payload(
            checked_cache_key
        )
        if cached_payload is not None:
            return cached_payload
    else:
        cached_latest_snapshot_id = await _load_cached_latest_snapshot_id(
            schema
        )
        if cached_latest_snapshot_id is not None:
            # Snapshot advances can race this optimistic lookup; the resolved
            # snapshot re-check below is the authoritative cache key.
            checked_cache_key = _team_matches_cache_key(
                schema=schema,
                snapshot_id=cached_latest_snapshot_id,
                team_ids=parsed_team_ids,
                limit=limit,
            )
            cached_payload = await _load_cached_team_matches_payload(
                checked_cache_key
            )
            if cached_payload is not None:
                return cached_payload

    async with rankings_async_session() as session:
        resolved_snapshot_id = await _resolve_snapshot_id(session, snapshot_id)
        if snapshot_id is None:
            await _store_cached_latest_snapshot_id(schema, resolved_snapshot_id)
        cache_key = _team_matches_cache_key(
            schema=schema,
            snapshot_id=resolved_snapshot_id,
            team_ids=parsed_team_ids,
            limit=limit,
        )
        if cache_key != checked_cache_key:
            cached_payload = await _load_cached_team_matches_payload(
                cache_key
            )
            if cached_payload is not None:
                return cached_payload

        payload = await _fetch_team_matches_payload(
            session,
            snapshot_id=resolved_snapshot_id,
            team_ids=parsed_team_ids,
            limit=limit,
        )
        await _store_cached_team_matches_payload(cache_key, payload)
        return payload
