from __future__ import annotations

import hashlib
import math
from time import perf_counter
from typing import Any, Dict, List, Optional

import orjson
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from redis.exceptions import RedisError

from fast_api_app.auth import require_scopes
from fast_api_app.connections import rankings_async_session, redis_conn
from shared_lib.monitoring import (
    RIPPLE_CACHE_PAYLOAD_BYTES,
    RIPPLE_CACHE_REQUESTS,
    RIPPLE_QUERY_DURATION,
    metrics_enabled,
)
from shared_lib.queries.ripple_queries import (
    fetch_ripple_danger,
    fetch_ripple_page,
)

router = APIRouter(
    prefix="/api/ripple",
    tags=["ripple"],
    dependencies=[Depends(require_scopes({"ripple.read"}))],
)

# Public docs compatibility router for ripple endpoints (no auth required)
docs_router = APIRouter(prefix="/api/ripple")


_CACHE_PREFIX = "api:ripple:cache:"
_CACHE_TTL_SECONDS = 300
RIPPLE_OPENAPI_DOC_URL = "/docs#/paths/~1api~1ripple~1leaderboard/get"


class RippleLeaderboardItem(BaseModel):
    rank: Optional[int] = None
    player_id: Optional[str] = None
    display_name: Optional[str] = None
    score: float
    display_score: float
    win_loss_ratio: float
    tournament_count: Optional[int] = None
    last_active_ms: Optional[int] = None


class RippleLeaderboardResponse(BaseModel):
    build_version: str
    calculated_at_ms: int
    limit: int
    offset: int
    total: int
    data: List[RippleLeaderboardItem]


class RippleRawResponse(BaseModel):
    build_version: str
    calculated_at_ms: int
    limit: int
    offset: int
    total: int
    data: List[Dict[str, Any]]


class RippleDangerItem(BaseModel):
    rank: Optional[int] = None
    player_id: Optional[str] = None
    display_name: Optional[str] = None
    score: float
    display_score: float
    window_tournament_count: Optional[int] = None
    oldest_in_window_ms: Optional[int] = None
    next_expiry_ms: Optional[int] = None
    days_left: Optional[float] = None


class RippleDangerResponse(BaseModel):
    build_version: str
    calculated_at_ms: int
    limit: int
    offset: int
    total: int
    data: List[RippleDangerItem]


def _cache_key(kind: str, params: Dict[str, Any]) -> str:
    serialized = orjson.dumps(params, option=orjson.OPT_SORT_KEYS)
    digest = hashlib.sha256(serialized).hexdigest()
    return f"{_CACHE_PREFIX}{kind}:{digest}"


def _get_cached(kind: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    key = _cache_key(kind, params)
    try:
        cached = redis_conn.get(key)
    except RedisError:
        if metrics_enabled():
            RIPPLE_CACHE_REQUESTS.labels(kind, "redis_error").inc()
        return None
    if not cached:
        if metrics_enabled():
            RIPPLE_CACHE_REQUESTS.labels(kind, "miss").inc()
        return None
    try:
        payload = (
            cached
            if isinstance(cached, (bytes, bytearray, memoryview))
            else str(cached).encode("utf-8")
        )
        data = orjson.loads(payload)
    except orjson.JSONDecodeError:
        if metrics_enabled():
            RIPPLE_CACHE_REQUESTS.labels(kind, "decode_error").inc()
        try:
            redis_conn.delete(key)
        except RedisError:
            pass
        return None
    if metrics_enabled():
        RIPPLE_CACHE_REQUESTS.labels(kind, "hit").inc()
    return data


def _set_cached(
    kind: str, params: Dict[str, Any], payload: Dict[str, Any]
) -> None:
    key = _cache_key(kind, params)
    serialized = orjson.dumps(payload)
    try:
        redis_conn.setex(key, _CACHE_TTL_SECONDS, serialized)
    except RedisError:
        if metrics_enabled():
            RIPPLE_CACHE_REQUESTS.labels(kind, "store_error").inc()
        return None
    if metrics_enabled():
        RIPPLE_CACHE_PAYLOAD_BYTES.labels(kind=kind).set(len(serialized))


@docs_router.get(
    "/leaderboard/docs",
    response_class=HTMLResponse,
    summary="Legacy ripple docs",
)
@docs_router.get(
    "/docs",
    response_class=HTMLResponse,
    include_in_schema=False,
    deprecated=True,
    summary="Legacy ripple docs",
)
async def ripple_instructions():
    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Ripple API Docs</title>
</head>
<body>
  <h1>Ripple API docs moved to OpenAPI</h1>
  <p>
    This endpoint is deprecated. Use
    <a href=\"{RIPPLE_OPENAPI_DOC_URL}\">/docs#/paths/~1api~1ripple~1leaderboard/get</a>
    for interactive API documentation.
  </p>
</body>
</html>
        """.strip()
    )


def _display_score(
    score: float, *, offset: float = 0.0, multiplier: float = 25.0
) -> float:
    return (score + offset) * multiplier


@router.get(
    "/leaderboard",
    response_model=RippleLeaderboardResponse,
    summary="Get ripple leaderboard",
)
@router.get(
    "",
    response_model=RippleLeaderboardResponse,
    include_in_schema=False,
    deprecated=True,
)
async def get_ripple_leaderboard(
    # Pagination
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    # Run selection
    build: Optional[str] = Query(None, description="Filter to a build_version"),
    ts_ms: Optional[int] = Query(
        None, description="Use a specific calculated_at_ms (overrides build)"
    ),
    # Filters
    min_tournaments: Optional[int] = Query(
        3, ge=0, description="Minimum tournaments for eligibility"
    ),
    tournament_window_days: int = Query(
        90,
        ge=1,
        le=3650,
        description="Window in days to compute tournament count (default 90)",
    ),
    ranked_only: bool = Query(
        True,
        description="Count only ranked tournaments within the window (default true)",
    ),
    # Presentation controls
    score_multiplier: float = Query(25.0, ge=0.0, le=1000.0),
    score_offset: float = Query(0.0, ge=-1000000.0, le=1000000.0),
) -> RippleLeaderboardResponse:
    """Return a preprocessed page of ripple rankings (token-protected).

    The default run is the latest `calculated_at_ms`. Provide `build` or `ts_ms` to override.
    """

    cache_params = {
        "limit": limit,
        "offset": offset,
        "build": build,
        "ts_ms": ts_ms,
        "min_tournaments": min_tournaments,
        "tournament_window_days": tournament_window_days,
        "ranked_only": ranked_only,
        "score_multiplier": score_multiplier,
        "score_offset": score_offset,
    }

    cached = _get_cached("leaderboard", cache_params)
    if cached is not None:
        return cached

    start = perf_counter()
    async with rankings_async_session() as session:
        rows, total, calc_ts, build_version = await fetch_ripple_page(
            session,
            limit=limit,
            offset=offset,
            min_tournaments=min_tournaments,
            tournament_window_days=tournament_window_days,
            ranked_only=ranked_only,
            build=build,
            ts_ms=ts_ms,
        )
    if metrics_enabled():
        RIPPLE_QUERY_DURATION.labels(kind="leaderboard").observe(
            perf_counter() - start
        )

    def to_item(r: Dict[str, Any]) -> Dict[str, Any]:
        score = float(r.get("score") or 0.0)
        win_pr = r.get("win_pr")
        loss_pr = r.get("loss_pr")
        if win_pr is None or loss_pr is None or float(loss_pr) == 0.0:
            win_loss_ratio = math.exp(score)
        else:
            win_loss_ratio = float(win_pr) / max(float(loss_pr), 1e-10)

        return {
            "rank": r.get("rank"),
            "player_id": r.get("player_id"),
            "display_name": r.get("display_name"),
            "score": score,
            "display_score": _display_score(
                score, offset=score_offset, multiplier=score_multiplier
            ),
            "win_loss_ratio": win_loss_ratio,
            "tournament_count": r.get("tournament_count"),
            "last_active_ms": r.get("last_active_ms"),
        }

    items: List[Dict[str, Any]] = [to_item(dict(r)) for r in rows]

    response_payload = {
        "build_version": build_version,
        "calculated_at_ms": calc_ts,
        "limit": limit,
        "offset": offset,
        "total": total,
        "data": items,
    }

    _set_cached("leaderboard", cache_params, response_payload)

    return response_payload


@router.get(
    "/leaderboard/raw",
    response_model=RippleRawResponse,
    summary="Get raw ripple rows",
)
@router.get(
    "/raw",
    response_model=RippleRawResponse,
    include_in_schema=False,
    deprecated=True,
)
async def get_ripple_raw(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    build: Optional[str] = Query(None),
    ts_ms: Optional[int] = Query(None),
    min_tournaments: Optional[int] = Query(3, ge=0),
    tournament_window_days: int = Query(90, ge=1, le=3650),
    ranked_only: bool = Query(True),
) -> RippleRawResponse:
    """Return raw ripple rows as stored in the DB join (token-protected)."""

    cache_params = {
        "limit": limit,
        "offset": offset,
        "build": build,
        "ts_ms": ts_ms,
        "min_tournaments": min_tournaments,
        "tournament_window_days": tournament_window_days,
        "ranked_only": ranked_only,
    }

    cached = _get_cached("raw", cache_params)
    if cached is not None:
        return cached

    start = perf_counter()
    async with rankings_async_session() as session:
        rows, total, calc_ts, build_version = await fetch_ripple_page(
            session,
            limit=limit,
            offset=offset,
            min_tournaments=min_tournaments,
            tournament_window_days=tournament_window_days,
            ranked_only=ranked_only,
            build=build,
            ts_ms=ts_ms,
        )
    if metrics_enabled():
        RIPPLE_QUERY_DURATION.labels(kind="raw").observe(perf_counter() - start)

    items: List[Dict[str, Any]] = [dict(r) for r in rows]
    response_payload = {
        "build_version": build_version,
        "calculated_at_ms": calc_ts,
        "limit": limit,
        "offset": offset,
        "total": total,
        "data": items,
    }

    _set_cached("raw", cache_params, response_payload)

    return response_payload


@router.get(
    "/leaderboard/danger",
    response_model=RippleDangerResponse,
    summary="Get danger window",
)
@router.get(
    "/danger",
    response_model=RippleDangerResponse,
    include_in_schema=False,
    deprecated=True,
)
async def get_ripple_danger(
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    min_tournaments: Optional[int] = Query(None, ge=0),
    tournament_window_days: int = Query(90, ge=1, le=3650),
    ranked_only: bool = Query(True),
    build: Optional[str] = Query(None),
    ts_ms: Optional[int] = Query(None),
):
    cache_params = {
        "limit": limit,
        "offset": offset,
        "min_tournaments": min_tournaments,
        "tournament_window_days": tournament_window_days,
        "ranked_only": ranked_only,
        "build": build,
        "ts_ms": ts_ms,
    }

    cached = _get_cached("danger", cache_params)
    if cached is not None:
        return cached

    start = perf_counter()
    async with rankings_async_session() as session:
        rows, total, calc_ts, build_version = await fetch_ripple_danger(
            session,
            limit=limit,
            offset=offset,
            min_tournaments=min_tournaments,
            tournament_window_days=tournament_window_days,
            ranked_only=ranked_only,
            build=build,
            ts_ms=ts_ms,
        )
    if metrics_enabled():
        RIPPLE_QUERY_DURATION.labels(kind="danger").observe(
            perf_counter() - start
        )

    def to_item(r: Dict[str, Any]) -> Dict[str, Any]:
        score = float(r.get("score") or 0.0)
        next_expiry_ms = r.get("next_expiry_ms")
        days_left_ms = r.get("ms_left")
        days_left = None
        if days_left_ms is not None:
            days_left = float(days_left_ms) / 86400000.0
        return {
            "rank": r.get("player_rank"),
            "player_id": r.get("player_id"),
            "display_name": r.get("display_name"),
            "score": score,
            "display_score": _display_score(score),
            "window_tournament_count": r.get("window_count"),
            "oldest_in_window_ms": r.get("oldest_in_window_ms"),
            "next_expiry_ms": next_expiry_ms,
            "days_left": days_left,
        }

    items: List[Dict[str, Any]] = [to_item(dict(r)) for r in rows]
    response_payload = {
        "build_version": build_version,
        "calculated_at_ms": calc_ts,
        "limit": limit,
        "offset": offset,
        "total": total,
        "data": items,
    }

    _set_cached("danger", cache_params, response_payload)

    return response_payload
