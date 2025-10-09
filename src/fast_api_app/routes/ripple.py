from __future__ import annotations

import hashlib
import math
from time import perf_counter
from typing import Any, Dict, List, Optional

import orjson
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
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
    dependencies=[Depends(require_scopes({"ripple.read"}))],
)

# Public docs router for ripple endpoints (no auth required)
docs_router = APIRouter(prefix="/api/ripple")


_CACHE_PREFIX = "api:ripple:cache:"
_CACHE_TTL_SECONDS = 300


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


@docs_router.get("/docs", response_class=HTMLResponse)
async def ripple_instructions():
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Ripple API Documentation</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 2rem; color: #333; }
    h1, h2, h3 { color: #2c3e50; margin-top: 2rem; }
    h1 { border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
    pre { background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }
    code { background: #f6f8fa; padding: 0.2rem 0.4rem; border-radius: 3px; font-family: 'Monaco', 'Consolas', monospace; }
    ul, ol { padding-left: 1.5rem; }
    li { margin: 0.4rem 0; }
    .endpoint { background: #e8f4f8; padding: 1rem; border-radius: 6px; margin: 1rem 0; }
    .note { background: #fff3cd; border-left: 4px solid #ffc107; padding: 1rem; margin: 1rem 0; }
    .section { border: 1px solid #e1e4e8; border-radius: 6px; margin: 2rem 0; padding: 1rem; }
  </style>
  </head>
  <body>
    <h1>Ripple API Documentation</h1>

    <div class=\"section\">
      <h2>Authentication</h2>
      <p>These endpoints require an API token with the <code>ripple.read</code> scope.</p>
      <p>Send your token using one of the headers:</p>
      <ul>
        <li><code>Authorization: Bearer rpl_&lt;uuid&gt;_&lt;secret&gt;</code></li>
        <li><code>X-API-Token: rpl_&lt;uuid&gt;_&lt;secret&gt;</code></li>
      </ul>
    </div>

    <div class=\"section\">
      <h2>Endpoints</h2>

      <h3>1) Leaderboard (preprocessed)</h3>
      <div class=\"endpoint\">
        <ul>
          <li><strong>Method:</strong> GET</li>
          <li><strong>Path:</strong> <code>/api/ripple</code></li>
        </ul>
      </div>
      <h4>Query Parameters</h4>
      <ul>
        <li><code>limit</code> (int, default 50, 1–500)</li>
        <li><code>offset</code> (int, default 0)</li>
        <li><code>build</code> (string, optional): filter by build_version</li>
        <li><code>ts_ms</code> (int, optional): specific <code>calculated_at_ms</code> snapshot</li>
        <li><code>min_tournaments</code> (int, default 3): minimum appearances within window</li>
        <li><code>tournament_window_days</code> (int, default 90)</li>
        <li><code>ranked_only</code> (bool, default true)</li>
        <li><code>score_multiplier</code> (float, default 25.0)</li>
        <li><code>score_offset</code> (float, default 0.0)</li>
      </ul>
      <h4>Response</h4>
      <pre>{
  "build_version": "2024.09.01",
  "calculated_at_ms": 1725148800000,
  "limit": 50,
  "offset": 0,
  "total": 12345,
  "data": [
    {
      "rank": 1,
      "player_id": "...",
      "display_name": "Player",
      "score": 1.2345,
      "display_score": 30.86,
      "win_loss_ratio": 1.23,
      "tournament_count": 12,
      "last_active_ms": 1725000000000
    }
  ]
}</pre>

      <h3>2) Raw rows</h3>
      <div class=\"endpoint\">
        <ul>
          <li><strong>Method:</strong> GET</li>
          <li><strong>Path:</strong> <code>/api/ripple/raw</code></li>
        </ul>
      </div>
      <p>Same query params as the leaderboard; returns DB-joined fields without presentation transforms.</p>

      <h3>3) Danger window</h3>
      <div class=\"endpoint\">
        <ul>
          <li><strong>Method:</strong> GET</li>
          <li><strong>Path:</strong> <code>/api/ripple/danger</code></li>
        </ul>
      </div>
      <h4>Query Parameters</h4>
      <ul>
        <li><code>limit</code> (int, default 20, 1–500)</li>
        <li><code>offset</code> (int, default 0)</li>
        <li><code>min_tournaments</code> (int, optional): exact count within window</li>
        <li><code>tournament_window_days</code> (int, default 90)</li>
        <li><code>ranked_only</code> (bool, default true)</li>
        <li><code>build</code> (string, optional)</li>
        <li><code>ts_ms</code> (int, optional)</li>
      </ul>
      <h4>Response</h4>
      <pre>{
  "build_version": "2024.09.01",
  "calculated_at_ms": 1725148800000,
  "limit": 20,
  "offset": 0,
  "total": 100,
  "data": [
    {
      "rank": 42,
      "player_id": "...",
      "display_name": "Player",
      "score": 0.9876,
      "display_score": 24.69,
      "window_tournament_count": 3,
      "oldest_in_window_ms": 1723000000000,
      "next_expiry_ms": 1723000000000,
      "days_left": 10.5
    }
  ]
}</pre>
      <div class=\"note\">Tip: sort by <code>days_left</code> and monitor <code>window_tournament_count</code> for eligibility risk.</div>
    </div>

    <div class=\"section\">
      <h2>Output Field Reference</h2>
      <p>The following describes the fields returned by the Ripple endpoints.</p>

      <h3>Envelope</h3>
      <ul>
        <li><code>build_version</code> (string): Identifier of the computed rankings snapshot.</li>
        <li><code>calculated_at_ms</code> (number): Snapshot timestamp in milliseconds since Unix epoch.</li>
        <li><code>limit</code>, <code>offset</code> (numbers): Pagination parameters echoed back.</li>
        <li><code>total</code> (number): Total number of rows available for the current query.</li>
      </ul>

      <h3>Leaderboard item (preprocessed)</h3>
      <ul>
        <li><code>rank</code> (number): Position ordered by <code>score</code> descending.</li>
        <li><code>player_id</code> (string): Stable player identifier.</li>
        <li><code>display_name</code> (string): Human‑readable player name.</li>
        <li><code>score</code> (number): Model score used for ranking (higher is better).</li>
        <li><code>display_score</code> (number): Presentation score computed as <code>(score + score_offset) * score_multiplier</code>.</li>
        <li><code>win_loss_ratio</code> (number): Computed internally from model inputs when available; otherwise equals <code>exp(score)</code>.</li>
        <li><code>tournament_count</code> (number|null): Total tournaments seen for the player in the snapshot.</li>
        <li><code>last_active_ms</code> (number|null): Last activity timestamp in milliseconds since epoch.</li>
      </ul>

      <h3>Danger item</h3>
      <ul>
        <li><code>rank</code> (number): Player rank in the snapshot (same ordering as leaderboard).</li>
        <li><code>window_tournament_count</code> (number): Distinct tournaments within the window considered.</li>
        <li><code>oldest_in_window_ms</code> (number): Oldest tournament event time (ms) within the active window.</li>
        <li><code>next_expiry_ms</code> (number): Time (ms) when the oldest tournament will fall out of the window.</li>
        <li><code>days_left</code> (number|null): Convenience value equal to <code>(next_expiry_ms - calculated_at_ms) / 86,400,000</code>.</li>
      </ul>

      <h3>Raw rows</h3>
      <p>Returns database‑joined fields for advanced use cases (schema is subject to change). Prefer the preprocessed endpoint unless raw fields are required.</p>
    </div>

  </body>
  </html>
        """
    )


def _display_score(
    score: float, *, offset: float = 0.0, multiplier: float = 25.0
) -> float:
    return (score + offset) * multiplier


@router.get("")
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
) -> Dict[str, Any]:
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


@router.get("/raw")
async def get_ripple_raw(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    build: Optional[str] = Query(None),
    ts_ms: Optional[int] = Query(None),
    min_tournaments: Optional[int] = Query(3, ge=0),
    tournament_window_days: int = Query(90, ge=1, le=3650),
    ranked_only: bool = Query(True),
) -> Dict[str, Any]:
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


@router.get("/danger")
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
