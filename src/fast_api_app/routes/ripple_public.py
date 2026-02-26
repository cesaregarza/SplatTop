from __future__ import annotations

import time
from typing import Any, Dict, Optional

import orjson
from fastapi import APIRouter, HTTPException

from fast_api_app.connections import redis_conn
from fast_api_app.feature_flags import is_comp_leaderboard_enabled
from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_PERCENTILES_KEY,
)

router = APIRouter(prefix="/api/ripple/public", tags=["ripple-public"])


_STALENESS_THRESHOLD_MS = 24 * 60 * 60 * 1000  # 24 hours


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
