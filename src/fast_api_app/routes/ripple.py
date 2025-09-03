from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from fast_api_app.auth import require_api_token
from fast_api_app.connections import async_session
from shared_lib.queries.ripple_queries import fetch_ripple_page

router = APIRouter(
    prefix="/api/ripple", dependencies=[Depends(require_api_token)]
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
    # Presentation controls
    score_multiplier: float = Query(25.0),
    score_offset: float = Query(0.0),
) -> Dict[str, Any]:
    """Return a preprocessed page of ripple rankings (token-protected).

    The default run is the latest `calculated_at_ms`. Provide `build` or `ts_ms` to override.
    """

    async with async_session() as session:
        rows, total, calc_ts, build_version = await fetch_ripple_page(
            session,
            limit=limit,
            offset=offset,
            min_tournaments=min_tournaments,
            build=build,
            ts_ms=ts_ms,
        )

    def to_item(r: Dict[str, Any]) -> Dict[str, Any]:
        score = float(r.get("score") or 0.0)
        win_pr = r.get("win_pr")
        loss_pr = r.get("loss_pr")
        if win_pr is None or loss_pr is None or float(loss_pr) == 0.0:
            win_loss_ratio = math.exp(score)
            win_loss_diff = score
        else:
            win_loss_ratio = float(win_pr) / max(float(loss_pr), 1e-10)
            win_loss_diff = float(win_pr) - float(loss_pr)

        return {
            "rank": r.get("rank"),
            "player_id": r.get("player_id"),
            "display_name": r.get("display_name"),
            "score": score,
            "display_score": _display_score(
                score, offset=score_offset, multiplier=score_multiplier
            ),
            "exposure": r.get("exposure"),
            "win_pr": win_pr,
            "loss_pr": loss_pr,
            "win_loss_ratio": win_loss_ratio,
            "win_loss_diff": win_loss_diff,
            "tournament_count": r.get("tournament_count"),
            "last_active_ms": r.get("last_active_ms"),
        }

    items: List[Dict[str, Any]] = [to_item(dict(r)) for r in rows]

    return {
        "build_version": build_version,
        "calculated_at_ms": calc_ts,
        "limit": limit,
        "offset": offset,
        "total": total,
        "data": items,
    }


@router.get("/raw")
async def get_ripple_raw(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    build: Optional[str] = Query(None),
    ts_ms: Optional[int] = Query(None),
    min_tournaments: Optional[int] = Query(3, ge=0),
) -> Dict[str, Any]:
    """Return raw ripple rows as stored in the DB join (token-protected)."""
    async with async_session() as session:
        rows, total, calc_ts, build_version = await fetch_ripple_page(
            session,
            limit=limit,
            offset=offset,
            min_tournaments=min_tournaments,
            build=build,
            ts_ms=ts_ms,
        )

    items: List[Dict[str, Any]] = [dict(r) for r in rows]
    return {
        "build_version": build_version,
        "calculated_at_ms": calc_ts,
        "limit": limit,
        "offset": offset,
        "total": total,
        "data": items,
    }
