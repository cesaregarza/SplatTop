from __future__ import annotations

import logging
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from fast_api_app.comp_auth import (
    COMP_AUTH_PENDING_SESSION_KEY,
    COMP_AUTH_SCOPE,
    COMP_AUTH_USER_SESSION_KEY,
    DISCORD_AUTHORIZE_URL,
    DISCORD_TOKEN_URL,
    DISCORD_USER_URL,
    build_competition_frontend_redirect_url,
    ensure_comp_auth_request_origin_allowed,
    get_discord_auth_config,
    is_comp_admin_discord_id,
    is_discord_auth_configured,
    normalize_comp_auth_return_to,
    read_authenticated_comp_discord_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/comp-auth", tags=["competition-auth"])

DISCORD_HTTP_TIMEOUT = 10.0


def _now_ms() -> int:
    return int(time.time() * 1000)


async def exchange_discord_code_for_user_id(code: str) -> str:
    config = get_discord_auth_config()

    try:
        async with httpx.AsyncClient(timeout=DISCORD_HTTP_TIMEOUT) as client:
            token_response = await client.post(
                DISCORD_TOKEN_URL,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                    "scope": COMP_AUTH_SCOPE,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            token_response.raise_for_status()
            token_payload = token_response.json()

            access_token = str(token_payload.get("access_token") or "").strip()
            if not access_token:
                raise HTTPException(
                    status_code=502,
                    detail="Discord token response missing access token",
                )

            user_response = await client.get(
                DISCORD_USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_response.raise_for_status()
            user_payload = user_response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Discord auth HTTP failure: status=%s",
            exc.response.status_code,
        )
        raise HTTPException(
            status_code=502,
            detail="Discord auth request failed",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Discord auth request error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Discord auth request failed",
        ) from exc

    discord_id = str(user_payload.get("id") or "").strip()
    if not discord_id:
        raise HTTPException(
            status_code=502,
            detail="Discord user response missing id",
        )

    return discord_id


@router.get("/discord/login")
async def start_discord_login(
    request: Request,
    next_target: str | None = Query(default=None, alias="next"),
):
    config = get_discord_auth_config()
    state = secrets.token_urlsafe(24)
    request.session[COMP_AUTH_PENDING_SESSION_KEY] = {
        "state": state,
        "return_to": normalize_comp_auth_return_to(next_target),
        "created_at_ms": _now_ms(),
    }

    authorize_params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
        "scope": COMP_AUTH_SCOPE,
        "state": state,
    }
    return RedirectResponse(
        url=f"{DISCORD_AUTHORIZE_URL}?{urlencode(authorize_params)}",
        status_code=302,
    )


@router.get("/discord/callback")
async def finish_discord_login(
    request: Request,
    code: str | None = None,
    state: str | None = None,
):
    pending = request.session.get(COMP_AUTH_PENDING_SESSION_KEY)
    return_to = None
    if isinstance(pending, dict):
        return_to = pending.get("return_to")

    if (
        not code
        or not state
        or not isinstance(pending, dict)
        or state != pending.get("state")
    ):
        request.session.clear()
        raise HTTPException(
            status_code=400, detail="Invalid Discord login state"
        )

    request.session.pop(COMP_AUTH_PENDING_SESSION_KEY, None)
    discord_id = await exchange_discord_code_for_user_id(code)
    request.session[COMP_AUTH_USER_SESSION_KEY] = {
        "discord_id": discord_id,
        "authenticated_at_ms": _now_ms(),
    }

    return RedirectResponse(
        url=build_competition_frontend_redirect_url(request, return_to),
        status_code=302,
    )


@router.get("/me")
async def get_comp_auth_me(request: Request, response: Response):
    ensure_comp_auth_request_origin_allowed(request)
    response.headers["Cache-Control"] = "no-store"
    available = is_discord_auth_configured()

    discord_id = read_authenticated_comp_discord_id(request)
    if discord_id is None:
        request.session.pop(COMP_AUTH_USER_SESSION_KEY, None)
        return {
            "authenticated": False,
            "discord_id": None,
            "is_admin": False,
            "available": available,
        }

    return {
        "authenticated": True,
        "discord_id": discord_id,
        "is_admin": is_comp_admin_discord_id(discord_id),
        "available": available,
    }


@router.post("/logout")
async def logout_comp_auth(request: Request, response: Response):
    ensure_comp_auth_request_origin_allowed(request)
    response.headers["Cache-Control"] = "no-store"
    request.session.clear()
    return {
        "authenticated": False,
        "discord_id": None,
        "is_admin": False,
        "available": is_discord_auth_configured(),
    }
