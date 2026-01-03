"""Proxy routes for sendou.ink turbo-stream endpoints.

Fetches data from sendou.ink's new turbo-stream format (.data endpoints)
and returns plain JSON compatible with the legacy ?_data format.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import httpx
import orjson
from fastapi import APIRouter, HTTPException, Path

from shared_lib.turbo_stream import TurboStreamDecoder

router = APIRouter(prefix="/api/sendou", tags=["sendou-proxy"])

logger = logging.getLogger(__name__)

SENDOU_BASE_URL = "https://sendou.ink"
REQUEST_TIMEOUT = 10.0

# Route keys for different sendou.ink endpoints
ROUTE_KEY_TOURNAMENT_MATCH = (
    "features/tournament-bracket/routes/to.$id.matches.$mid"
)


async def _fetch_turbo_stream(url: str) -> bytes:
    """Fetch turbo-stream data from sendou.ink."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _decode_and_extract(
    raw_data: bytes,
    route_key: str,
) -> Dict[str, Any]:
    """Decode turbo-stream data and extract route-specific data."""
    try:
        parsed = orjson.loads(raw_data)
    except orjson.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {e}")

    if not isinstance(parsed, list):
        raise ValueError("Expected turbo-stream array format")

    decoder = TurboStreamDecoder(parsed)
    route_data = decoder.get_route_data(route_key)

    if route_data is None:
        # Return the full decoded data if route key not found
        return decoder.decode()

    return route_data


@router.get(
    "/to/{tournament_id}/matches/{match_id}",
    name="sendou-tournament-match",
    summary="Get tournament match data from sendou.ink",
    description=(
        "Proxies the sendou.ink turbo-stream endpoint and returns plain JSON. "
        "Equivalent to the legacy ?_data format."
    ),
)
async def get_tournament_match(
    tournament_id: int = Path(..., description="Tournament ID on sendou.ink"),
    match_id: int = Path(..., description="Match ID within the tournament"),
) -> Dict[str, Any]:
    """Fetch and decode tournament match data from sendou.ink."""
    url = f"{SENDOU_BASE_URL}/to/{tournament_id}/matches/{match_id}.data"

    try:
        raw_data = await _fetch_turbo_stream(url)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "sendou.ink returned %s for tournament=%s match=%s",
            e.response.status_code,
            tournament_id,
            match_id,
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"sendou.ink returned {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error("Failed to fetch from sendou.ink: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch from sendou.ink",
        )

    try:
        data = _decode_and_extract(raw_data, ROUTE_KEY_TOURNAMENT_MATCH)
    except ValueError as e:
        logger.error("Failed to decode turbo-stream data: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Failed to decode sendou.ink response",
        )

    return data
