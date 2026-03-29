from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

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
PUBLIC_CORS_ORIGIN_REGEX = r"https?://.*"


@dataclass(frozen=True)
class DiscordAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str


def _environment_name() -> str:
    return os.getenv("ENV", "").strip().lower()


def is_secure_cookie_environment() -> bool:
    return _environment_name() not in {"", "development", "dev", "test"}


def get_comp_auth_session_secret() -> str:
    secret = os.getenv("COMP_AUTH_SESSION_SECRET", "").strip()
    if secret:
        return secret
    return DEFAULT_DEV_SESSION_SECRET


def get_comp_auth_session_middleware_kwargs() -> dict:
    return {
        "secret_key": get_comp_auth_session_secret(),
        "session_cookie": COMP_AUTH_SESSION_COOKIE,
        "same_site": "lax",
        "https_only": is_secure_cookie_environment(),
        "max_age": 60 * 60 * 24 * 30,
    }


def get_public_cors_origin_regex() -> str:
    return PUBLIC_CORS_ORIGIN_REGEX


def _parse_env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [
        value.strip().rstrip("/") for value in raw.split(",") if value.strip()
    ]


def get_comp_auth_allowed_origins() -> list[str]:
    configured = _parse_env_list("COMP_AUTH_ALLOWED_ORIGINS")
    if configured:
        return configured

    origins = {
        DEFAULT_LOCAL_COMP_FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        DEFAULT_COMP_FRONTEND_URL,
        "https://splat.top",
        "https://www.splat.top",
    }

    frontend_override = (
        os.getenv("COMP_AUTH_FRONTEND_URL", "").strip().rstrip("/")
    )
    if frontend_override:
        origins.add(frontend_override)

    return sorted(origins)


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
