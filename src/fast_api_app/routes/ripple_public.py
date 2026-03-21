from __future__ import annotations

from html import escape
from io import BytesIO
import time
from typing import Any, Dict, Optional
from urllib.parse import quote

import orjson
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from PIL import Image, ImageDraw, ImageFont

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
_SHARE_FONT_REGULAR_PATH = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
)
_SHARE_FONT_BOLD_PATH = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
)


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
    display_name = player.get("display_name") or player.get("player_id") or "Player"
    return f"{display_name} · {_share_rank_label(player)} · splat.top Competitive"


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
        player.get("display_name") or player.get("player_id") or "Unknown player"
    )
    player_id = str(player.get("player_id") or "unknown")
    rank_label = _share_rank_label(player)
    status_label = _share_status_label(player)
    description = _share_description(player)
    last_active = _share_last_active_label(player)

    score = _share_rank_score(player)
    score_label = (
        f"{score:.2f} / {_SHARE_SCORE_TARGET:.0f}" if score is not None else "Hidden"
    )
    progress_pct = 0.0
    if score is not None:
        progress_pct = max(0.0, min((score / _SHARE_SCORE_TARGET) * 100.0, 100.0))
    progress_width = round(520 * progress_pct / 100.0, 2)

    active_window = (
        f"{int(player.get('window_tournament_count') or 0)}/"
        f"{int(player.get('minimum_required_tournaments') or 3)}"
    )
    lifetime = str(int(player.get("lifetime_ranked_tournaments") or 0))

    image = Image.new("RGBA", (_SHARE_CARD_WIDTH, _SHARE_CARD_HEIGHT), "#08111d")
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
            f'<main><h1>{escape(title)}</h1>'
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
