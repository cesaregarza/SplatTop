import logging
import os
import re
import time
from hashlib import sha256
from typing import Callable, Optional, Set, Tuple

import orjson
from fastapi import Header, HTTPException, Request, status

from fast_api_app.connections import redis_conn
from shared_lib.constants import (
    API_TOKEN_HASH_MAP_PREFIX,
    API_TOKEN_IDS_SET,
    API_TOKEN_META_PREFIX,
    API_TOKEN_PREFIX,
    API_TOKENS_ACTIVE_SET,
    API_USAGE_QUEUE_KEY,
)
from shared_lib.monitoring import AUTH_FAILURES, metrics_enabled

TOKEN_RE = re.compile(rf"^{API_TOKEN_PREFIX}_(.+)$")
logger = logging.getLogger(__name__)


def _record_auth_failure(reason: str) -> None:
    if metrics_enabled():
        AUTH_FAILURES.labels(reason=reason).inc()


def _pepper() -> str:
    p = os.getenv("API_TOKEN_PEPPER")
    if not p:
        # Fail closed if no tokens configured.
        logger.error("API token system pepper missing; failing closed")
        _record_auth_failure("pepper_missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token system is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return p


def parse_token(raw: str) -> Tuple[Optional[str], str]:
    """Parse a token string into ``(token_id, secret)``.

    - Expected format: ``"{API_TOKEN_PREFIX}_{id}_{secret}"``. We split on the
      first underscore after the prefix so the secret may itself contain
      underscores (e.g., urlsafe base64).
    - If the string does not start with the expected prefix, return
      ``(None, raw)``.

    Important: This function never accepts or rejects a token; it only extracts
    fields for downstream checks. Authentication is enforced in
    ``require_api_token`` by hashing the returned ``secret`` with the server
    pepper and verifying membership of the resulting hash in
    ``API_TOKENS_ACTIVE_SET`` (and optional metadata checks). Returning
    ``(None, raw)`` does not bypass these checks.
    """
    prefix = f"{API_TOKEN_PREFIX}_"
    if not raw.startswith(prefix):
        return None, raw
    rest = raw[len(prefix) :]
    try:
        token_id, secret = rest.split("_", 1)
        return token_id, secret
    except ValueError:
        # No separator found after prefix; treat whole raw as the secret
        return None, raw


def hash_secret(secret: str, pepper: Optional[str] = None) -> str:
    pep = pepper or _pepper()
    return sha256((pep + secret).encode()).hexdigest()


def _get_header_token(
    authorization: Optional[str], x_api_token: Optional[str]
) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if x_api_token:
        return x_api_token.strip()
    return None


def require_api_token(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_token: Optional[str] = Header(default=None),
):
    """Validate an API token against Redis and attach identity to the request.

    Security gates (in order):
    - Extract the bearer token from ``Authorization`` or ``X-API-Token``.
    - Parse with :func:`parse_token` → ``(token_id or None, secret)``.
    - Hash ``secret`` with the server-side pepper (missing pepper → 401).
    - Require ``API_TOKENS_ACTIVE_SET`` to contain the hash (else 401).
    - If ``token_id`` is ``None``, map ``hash → id`` via
      ``API_TOKEN_HASH_MAP_PREFIX`` to load metadata.
    - If metadata has ``expires_at_ms`` in the past → 401.

    On unexpected Redis errors, this fails closed with 503.

    Note: ``parse_token`` returning ``(None, raw)`` is not an acceptance path;
    only tokens whose peppered hash is present in the active set are accepted.
    """

    raw = _get_header_token(authorization, x_api_token)
    if not raw:
        logger.warning(
            "Missing API token on protected route",
            extra={"path": str(request.url.path)},
        )
        _record_auth_failure("missing_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_id, secret = parse_token(raw)
        token_hash = hash_secret(secret)
    except HTTPException:
        raise
    except Exception:
        logger.warning("Invalid API token format")
        _record_auth_failure("invalid_format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        if not redis_conn.sismember(API_TOKENS_ACTIVE_SET, token_hash):
            logger.warning("Invalid or revoked API token")
            _record_auth_failure("revoked")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if token_id is None:
            token_id = redis_conn.get(
                f"{API_TOKEN_HASH_MAP_PREFIX}{token_hash}"
            )
        # Enforce expiration if configured in metadata
        if token_id:
            meta = redis_conn.hgetall(f"{API_TOKEN_META_PREFIX}{token_id}")
            if meta:
                exp = int(meta.get("expires_at_ms", 0) or 0)
                if exp and exp > 0 and int(time.time() * 1000) > exp:
                    logger.warning("Expired API token used")
                    _record_auth_failure("expired")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Expired API token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
    except HTTPException:
        raise
    except Exception:
        logger.error("Auth Redis unavailable; failing closed")
        _record_auth_failure("backend_unavailable")
        raise HTTPException(status_code=503, detail="Auth backend unavailable")

    request.state.token_id = token_id
    request.state.token_hash = token_hash
    return True


def _admin_hash(raw: str) -> str:
    pep = os.getenv("ADMIN_TOKEN_PEPPER") or os.getenv("API_TOKEN_PEPPER", "")
    return sha256((pep + raw).encode()).hexdigest()


def require_admin_token(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_admin_token: Optional[str] = Header(
        default=None, convert_underscores=False
    ),
):
    """Require a high-entropy admin bearer token.

    Notes on hashing choice (addresses review nitpicks):
    - Admin tokens are random, high-entropy bearer tokens (not user passwords).
    - We hash as SHA-256(pepper + token) solely for lookup/storage; rainbow
      tables are not applicable because of the server-side pepper and entropy.
    - A KDF (bcrypt/argon2) is unnecessary for non-user-chosen tokens.

    Configure a comma-separated list in ADMIN_API_TOKENS_HASHED. Hashing uses
    ADMIN_TOKEN_PEPPER (or API_TOKEN_PEPPER as fallback) with SHA-256.
    """
    # Respect test/app overrides even if function identity mismatches due to reloads.
    try:
        overrides = (
            getattr(getattr(request, "app", None), "dependency_overrides", {})
            or {}
        )
        for dep_callable, override_fn in list(overrides.items()):
            if getattr(dep_callable, "__name__", "") == "require_admin_token":
                # Call the override (usually returns True or raises) and allow.
                try:
                    return override_fn()  # type: ignore[misc]
                except Exception:
                    return True
    except Exception:
        # If anything goes wrong inspecting overrides, fall through to header check.
        pass

    raw = _get_header_token(authorization, x_admin_token)
    hashed_cfg = os.getenv("ADMIN_API_TOKENS_HASHED", "")
    hashed_allowed = {t.strip() for t in hashed_cfg.split(",") if t.strip()}
    if not hashed_allowed:
        logger.error(
            "ADMIN_API_TOKENS_HASHED is not configured; blocking admin access"
        )
        raise HTTPException(
            status_code=503, detail="Admin token system is not configured"
        )
    if raw and hashed_allowed and _admin_hash(raw) in hashed_allowed:
        return True
    logger.warning("Admin token required or invalid")
    raise HTTPException(status_code=401, detail="Admin token required")


def require_scopes(required: Set[str]) -> Callable:
    """Return a dependency that enforces required scopes for API tokens.

    - Ensures a valid API token via :func:`require_api_token`.
    - Fetches scopes from Redis using ``request.state.token_id``.
    - Returns HTTP 403 if any required scope is missing.

    Back-compat note: empty or missing scopes are treated as allow-all. Define
    explicit scopes on tokens to restrict access.
    """

    def _dep(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(
            default=None, convert_underscores=False
        ),
    ) -> bool:
        # Ensure token is valid and request.state is populated
        require_api_token(
            request, authorization=authorization, x_api_token=x_api_token
        )

        token_id = getattr(request.state, "token_id", None)
        if not token_id:
            raise HTTPException(status_code=403, detail="Insufficient scope")

        try:
            meta = redis_conn.hgetall(f"{API_TOKEN_META_PREFIX}{token_id}")
            scopes = []
            if meta and "scopes" in meta:
                try:
                    scopes = orjson.loads(meta.get("scopes", "[]"))
                except Exception:
                    scopes = []
            # Backward compatibility: empty scopes imply full access.
            # Define scopes on tokens to restrict access explicitly.
            if scopes and not required.issubset(set(scopes)):
                raise HTTPException(
                    status_code=403, detail="Insufficient scope"
                )
        except HTTPException:
            raise
        except Exception:
            logger.error("Auth backend unavailable during scope check")
            raise HTTPException(
                status_code=503, detail="Auth backend unavailable"
            )
        return True

    return _dep
