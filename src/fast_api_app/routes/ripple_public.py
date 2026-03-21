from __future__ import annotations

from html import escape
import time
from typing import Any, Dict, Optional
from urllib.parse import quote

import orjson
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from fast_api_app.connections import redis_conn
from fast_api_app.feature_flags import is_comp_leaderboard_enabled
from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_META_KEY,
    RIPPLE_PLAYER_INDEX_PLAYER_PREFIX,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_PERCENTILES_KEY,
)

router = APIRouter(prefix="/api/ripple/public", tags=["ripple-public"])
share_router = APIRouter(tags=["ripple-public-share"])


_STALENESS_THRESHOLD_MS = 24 * 60 * 60 * 1000  # 24 hours
_SHARE_CARD_WIDTH = 1200
_SHARE_CARD_HEIGHT = 630
_SHARE_SCORE_OFFSET = 150.0
_SHARE_SCORE_TARGET = 250.0


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


def _extract_player_from_legacy_index(
    payload: Dict[str, Any], player_id: str
) -> Optional[Dict[str, Any]]:
    players = payload.get("players")
    if not isinstance(players, dict):
        return None

    player = players.get(player_id)
    return player if isinstance(player, dict) else None


def _load_public_player_payload(player_id: str) -> Optional[Dict[str, Any]]:
    meta_payload = _load_payload(RIPPLE_PLAYER_INDEX_META_KEY)
    if not isinstance(meta_payload, dict):
        meta_payload = None

    player = _load_payload(_player_index_key(player_id))
    latest_payload: Dict[str, Any] | None = None
    if not isinstance(player, dict):
        latest_payload = _load_payload(RIPPLE_PLAYER_INDEX_LATEST_KEY)
        if isinstance(latest_payload, dict):
            player = _extract_player_from_legacy_index(latest_payload, player_id)
            if meta_payload is None:
                meta_payload = latest_payload

    if not isinstance(player, dict):
        return None

    if meta_payload is None:
        meta_payload = (
            latest_payload
            if isinstance(latest_payload, dict)
            else _load_payload(RIPPLE_PLAYER_INDEX_LATEST_KEY)
        )
    if not isinstance(meta_payload, dict):
        meta_payload = _empty_player_index_payload()

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
    "/player/{player_id}",
    name="public-ripple-player",
    summary="Get public competition player profile",
)
async def get_public_ripple_player(player_id: str) -> Dict[str, Any]:
    _ensure_enabled()
    player = _load_public_player_payload(player_id)
    if not isinstance(player, dict):
        raise HTTPException(
            status_code=404,
            detail="Player not found in competition index",
        )
    return player


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
    return f"{_share_origin(request)}/share/u/{quote(player_id, safe='')}/image.svg"


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
    display_name = player.get("display_name") or player.get("player_id") or "Player"
    return f"{display_name} · {_share_rank_label(player)} · splat.top Competitive"


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: max(0, limit - 1)].rstrip()}…"


def _share_card_svg(player: Dict[str, Any]) -> str:
    display_name = str(
        player.get("display_name") or player.get("player_id") or "Unknown player"
    )
    player_id = str(player.get("player_id") or "unknown")
    title_name = escape(_truncate_text(display_name, 28))
    subtitle = escape(player_id)
    rank_label = escape(_share_rank_label(player))
    status_label = escape(_share_status_label(player))
    description = escape(_share_description(player))
    last_active = escape(_share_last_active_label(player))

    score = _share_rank_score(player)
    score_label = escape(
        f"{score:.2f} / {_SHARE_SCORE_TARGET:.0f}" if score is not None else "Hidden"
    )
    progress_pct = 0.0
    if score is not None:
        progress_pct = max(0.0, min((score / _SHARE_SCORE_TARGET) * 100.0, 100.0))
    progress_width = round(560 * progress_pct / 100.0, 2)

    active_window = escape(
        f"{int(player.get('window_tournament_count') or 0)}/"
        f"{int(player.get('minimum_required_tournaments') or 3)}"
    )
    lifetime = escape(
        str(int(player.get("lifetime_ranked_tournaments") or 0))
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{_SHARE_CARD_WIDTH}" height="{_SHARE_CARD_HEIGHT}" viewBox="0 0 {_SHARE_CARD_WIDTH} {_SHARE_CARD_HEIGHT}" role="img" aria-label="{escape(_share_title(player))}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#08111d" />
      <stop offset="55%" stop-color="#101c2d" />
      <stop offset="100%" stop-color="#07111d" />
    </linearGradient>
    <radialGradient id="glow" cx="85%" cy="15%" r="75%">
      <stop offset="0%" stop-color="rgba(34,211,238,0.34)" />
      <stop offset="100%" stop-color="rgba(34,211,238,0)" />
    </radialGradient>
    <linearGradient id="bar" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#22d3ee" />
      <stop offset="100%" stop-color="#a78bfa" />
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)" />
  <rect width="1200" height="630" fill="url(#glow)" />
  <rect x="36" y="36" width="1128" height="558" rx="26" fill="rgba(9,18,31,0.86)" stroke="rgba(148,163,184,0.22)" />
  <text x="72" y="96" fill="#8ea2b8" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="24" letter-spacing="2">SPLAT.TOP / COMPETITIVE</text>
  <text x="72" y="182" fill="#f8fafc" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="64" font-weight="700">{title_name}</text>
  <text x="72" y="224" fill="#9fb1c4" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="24">{subtitle}</text>

  <rect x="72" y="262" width="136" height="54" rx="14" fill="rgba(167,139,250,0.14)" stroke="rgba(167,139,250,0.28)" />
  <text x="100" y="296" fill="#f3e8ff" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="30" font-weight="700">{rank_label}</text>
  <rect x="224" y="262" width="250" height="54" rx="14" fill="rgba(34,211,238,0.1)" stroke="rgba(34,211,238,0.22)" />
  <text x="250" y="296" fill="#e0fbff" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="24">{status_label}</text>

  <text x="72" y="368" fill="#8ea2b8" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="20" letter-spacing="1.4">RANK SCORE</text>
  <text x="72" y="420" fill="#f8fafc" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="44" font-weight="700">{score_label}</text>
  <rect x="72" y="442" width="560" height="14" rx="7" fill="rgba(20,33,48,0.94)" />
  <rect x="72" y="442" width="{progress_width}" height="14" rx="7" fill="url(#bar)" />
  <text x="72" y="486" fill="#8ea2b8" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="22">Path to XX+</text>

  <rect x="700" y="338" width="180" height="112" rx="18" fill="rgba(11,22,35,0.78)" stroke="rgba(148,163,184,0.14)" />
  <text x="726" y="376" fill="#8ea2b8" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="18">ACTIVE WINDOW</text>
  <text x="726" y="424" fill="#f8fafc" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="40" font-weight="700">{active_window}</text>

  <rect x="898" y="338" width="230" height="112" rx="18" fill="rgba(11,22,35,0.78)" stroke="rgba(148,163,184,0.14)" />
  <text x="924" y="376" fill="#8ea2b8" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="18">LIFETIME RANKED</text>
  <text x="924" y="424" fill="#f8fafc" font-family="'Fira Mono', ui-monospace, SFMono-Regular, Menlo, monospace" font-size="40" font-weight="700">{lifetime}</text>

  <text x="72" y="544" fill="#d8e2ee" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="26">{description}</text>
  <text x="72" y="582" fill="#8ea2b8" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="22">Last active: {last_active}</text>
</svg>"""


@share_router.get(
    "/share/u/{player_id}",
    response_class=HTMLResponse,
    summary="Shareable competition player preview",
)
async def get_public_ripple_player_share(
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

    html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}" />
    <meta property="og:title" content="{escape(title)}" />
    <meta property="og:description" content="{escape(description)}" />
    <meta property="og:image" content="{escape(image_url)}" />
    <meta property="og:image:type" content="image/svg+xml" />
    <meta property="og:image:width" content="{_SHARE_CARD_WIDTH}" />
    <meta property="og:image:height" content="{_SHARE_CARD_HEIGHT}" />
    <meta property="og:image:alt" content="{escape(description)}" />
    <meta property="og:url" content="{escape(profile_url)}" />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{escape(title)}" />
    <meta name="twitter:description" content="{escape(description)}" />
    <meta name="twitter:image" content="{escape(image_url)}" />
    <meta http-equiv="refresh" content="0;url={escape(profile_url)}" />
    <script>window.location.replace({orjson.dumps(profile_url).decode()});</script>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #020617;
        color: #e2e8f0;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      a {{ color: #67e8f9; }}
    </style>
  </head>
  <body>
    <p>Redirecting to <a href="{escape(profile_url)}">{escape(title)}</a>…</p>
  </body>
</html>"""
    return HTMLResponse(content=html)


@share_router.get(
    "/share/u/{player_id}/image.svg",
    summary="Shareable competition player summary image",
)
async def get_public_ripple_player_share_image(
    player_id: str,
) -> Response:
    _ensure_enabled()
    player = _load_public_player_payload(player_id)
    if not isinstance(player, dict):
        raise HTTPException(
            status_code=404,
            detail="Player not found in competition index",
        )

    return Response(
        content=_share_card_svg(player),
        media_type="image/svg+xml",
    )
