from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fast_api_app.connections import redis_conn
from shared_lib.constants import RIPPLE_PLAYER_OWNER_DISCORD_HASH_KEY

COMP_AUTH_SESSION_COOKIE = "comp_auth_session"
COMP_AUTH_PENDING_SESSION_KEY = "comp_auth_pending"
COMP_AUTH_USER_SESSION_KEY = "comp_auth_user"
COMP_AUTH_SCOPE = "identify"

DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USER_URL = "https://discord.com/api/users/@me"

DEFAULT_COMP_FRONTEND_URL = "https://comp.splat.top"
DEFAULT_LOCAL_COMP_FRONTEND_URL = "http://comp.localhost:3000"
DEFAULT_DEV_SESSION_SECRET = "development-comp-auth-session-secret"
_ENV_LIST_SPLIT_RE = re.compile(r"[\n,]+")
_DEFAULT_LOCAL_COMP_AUTH_ORIGINS = frozenset(
    {
        "http://comp.localhost",
        "http://comp.localhost:3000",
        "http://comp.localhost:4000",
        "http://comp.localhost:8080",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:4000",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4000",
        "http://127.0.0.1:8080",
    }
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscordAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str


def _environment_name() -> str:
    return os.getenv("ENV", "").strip().lower()


def is_development_like_environment() -> bool:
    return _environment_name() in {"", "development", "dev", "test"}


def is_secure_cookie_environment() -> bool:
    return not is_development_like_environment()


def get_comp_auth_session_secret() -> str:
    secret = os.getenv("COMP_AUTH_SESSION_SECRET", "").strip()
    if secret:
        return secret

    if is_development_like_environment():
        return DEFAULT_DEV_SESSION_SECRET

    raise RuntimeError(
        "COMP_AUTH_SESSION_SECRET must be configured outside development/test"
    )


def get_comp_auth_session_middleware_kwargs() -> dict:
    return {
        "secret_key": get_comp_auth_session_secret(),
        "session_cookie": COMP_AUTH_SESSION_COOKIE,
        "same_site": "lax",
        "https_only": is_secure_cookie_environment(),
        "max_age": 60 * 60 * 24 * 30,
    }


def _parse_env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [
        value.strip().rstrip("/") for value in raw.split(",") if value.strip()
    ]


def _parse_env_token_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [
        value.strip()
        for value in _ENV_LIST_SPLIT_RE.split(raw)
        if value.strip()
    ]


def _default_comp_auth_allowed_origins() -> set[str]:
    origins = {
        DEFAULT_COMP_FRONTEND_URL,
        "https://splat.top",
        "https://www.splat.top",
        *_DEFAULT_LOCAL_COMP_AUTH_ORIGINS,
    }

    frontend_override = (
        os.getenv("COMP_AUTH_FRONTEND_URL", "").strip().rstrip("/")
    )
    if frontend_override:
        origins.add(frontend_override)

    return origins


def get_comp_auth_allowed_origins() -> list[str]:
    configured = _parse_env_list("COMP_AUTH_ALLOWED_ORIGINS")
    origins = _default_comp_auth_allowed_origins()
    origins.update(configured)
    return sorted(origins)


def get_comp_auth_cors_allowed_origins() -> list[str]:
    return get_comp_auth_allowed_origins()


def get_comp_auth_admin_discord_ids() -> frozenset[str]:
    return frozenset(_parse_env_token_list("COMP_AUTH_ADMIN_DISCORD_IDS"))


def is_comp_admin_discord_id(discord_id: str | None) -> bool:
    if not discord_id:
        return False
    return str(discord_id).strip() in get_comp_auth_admin_discord_ids()


def get_comp_auth_player_owner_map() -> dict[str, frozenset[str]]:
    entries: dict[str, set[str]] = {}

    for token in _parse_env_token_list("COMP_AUTH_PLAYER_OWNERS"):
        player_id, separator, discord_id = token.partition("=")
        player_key = player_id.strip()
        discord_key = discord_id.strip()

        if separator != "=" or not player_key or not discord_key:
            continue

        entries.setdefault(player_key, set()).add(discord_key)

    return {
        player_id: frozenset(discord_ids)
        for player_id, discord_ids in entries.items()
    }


def is_comp_player_owner(
    player_id: str | None,
    discord_id: str | None,
) -> bool:
    if not player_id or not discord_id:
        return False

    player_key = str(player_id).strip()
    discord_key = str(discord_id).strip()
    if not player_key or not discord_key:
        return False

    if discord_key in get_comp_auth_player_owner_map().get(
        player_key, frozenset()
    ):
        return True

    try:
        cached_discord_id = redis_conn.hget(
            RIPPLE_PLAYER_OWNER_DISCORD_HASH_KEY, player_key
        )
    except Exception as exc:
        logger.warning(
            "Failed to read cached competition player owner map: %s", exc
        )
        return False

    cached_discord_key = str(cached_discord_id or "").strip()
    if not cached_discord_key:
        return False

    return cached_discord_key == discord_key


def read_authenticated_comp_discord_id(request: Request) -> str | None:
    session_payload = request.session.get(COMP_AUTH_USER_SESSION_KEY)
    if not isinstance(session_payload, dict):
        return None

    discord_id = str(session_payload.get("discord_id") or "").strip()
    if not discord_id:
        return None

    return discord_id


def require_comp_auth_user(request: Request) -> str:
    discord_id = read_authenticated_comp_discord_id(request)
    if discord_id is None:
        raise HTTPException(
            status_code=401,
            detail="Competition authentication is required",
        )

    return discord_id


def require_comp_admin(request: Request) -> str:
    discord_id = require_comp_auth_user(request)

    if not is_comp_admin_discord_id(discord_id):
        raise HTTPException(
            status_code=403,
            detail="Competition admin access is required",
        )

    return discord_id


def ensure_comp_auth_request_origin_allowed(request: Request) -> None:
    origin = request.headers.get("origin", "").strip().rstrip("/")
    if not origin:
        return

    allowed_origins = set(get_comp_auth_allowed_origins())
    if origin in allowed_origins:
        return

    raise HTTPException(
        status_code=403,
        detail="Competition auth origin is not allowed",
    )


def is_discord_auth_configured() -> bool:
    return all(
        [
            os.getenv("COMP_DISCORD_CLIENT_ID", "").strip(),
            os.getenv("COMP_DISCORD_CLIENT_SECRET", "").strip(),
            os.getenv("COMP_DISCORD_REDIRECT_URI", "").strip(),
        ]
    )


def get_discord_auth_config() -> DiscordAuthConfig:
    client_id = os.getenv("COMP_DISCORD_CLIENT_ID", "").strip()
    client_secret = os.getenv("COMP_DISCORD_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("COMP_DISCORD_REDIRECT_URI", "").strip()

    if is_discord_auth_configured():
        return DiscordAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

    raise HTTPException(
        status_code=503,
        detail="Competition Discord auth is not configured",
    )


def normalize_comp_auth_return_to(next_target: str | None) -> str:
    if not next_target:
        return "/"

    target = str(next_target).strip()
    if not target:
        return "/"

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        if parsed.fragment:
            target = f"{target}#{parsed.fragment}"

    if not target.startswith("/") or target.startswith("//"):
        return "/"

    return target


def get_competition_frontend_base_url(request: Request) -> str:
    override = os.getenv("COMP_AUTH_FRONTEND_URL", "").strip().rstrip("/")
    if override:
        return override

    host = request.headers.get("host", "").strip().lower()
    if host.startswith("comp.") or host.startswith("www.comp."):
        return f"{request.url.scheme}://{host}"

    if host.startswith("comp.localhost"):
        return f"{request.url.scheme}://{host}"

    if "localhost" in host or host.startswith("127.0.0.1"):
        return DEFAULT_LOCAL_COMP_FRONTEND_URL

    referer = request.headers.get("referer", "").strip()
    if referer:
        parsed = urlsplit(referer)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin.rstrip("/") in set(get_comp_auth_allowed_origins()):
                return origin.rstrip("/")

    return DEFAULT_COMP_FRONTEND_URL


def build_competition_frontend_redirect_url(
    request: Request,
    next_target: str | None,
) -> str:
    base_url = get_competition_frontend_base_url(request).rstrip("/")
    return_to = normalize_comp_auth_return_to(next_target)
    return f"{base_url}{return_to}"
