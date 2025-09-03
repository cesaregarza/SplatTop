import os
import re
import time
from hashlib import sha256
from typing import Optional, Tuple

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

TOKEN_RE = re.compile(rf"^{API_TOKEN_PREFIX}_([0-9a-fA-F-]+)_(.+)$")


def _pepper() -> str:
    p = os.getenv("API_TOKEN_PEPPER")
    if not p:
        # Fail closed if no tokens configured.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token system is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return p


def parse_token(raw: str) -> Tuple[Optional[str], str]:
    m = TOKEN_RE.match(raw)
    if m:
        return m.group(1), m.group(2)
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
    x_api_token: Optional[str] = Header(
        default=None, convert_underscores=False
    ),
):
    """Redis-backed token validation; stores token_id for usage logging."""

    raw = _get_header_token(authorization, x_api_token)
    if not raw:
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not redis_conn.sismember(API_TOKENS_ACTIVE_SET, token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_id is None:
        token_id = redis_conn.get(f"{API_TOKEN_HASH_MAP_PREFIX}{token_hash}")
    request.state.token_id = token_id
    request.state.token_hash = token_hash
    return True


def require_admin_token(
    authorization: Optional[str] = Header(default=None),
    x_admin_token: Optional[str] = Header(
        default=None, convert_underscores=False
    ),
):
    configured = os.getenv("ADMIN_API_TOKENS", "")
    allowed = {t.strip() for t in configured.split(",") if t.strip()}
    raw = _get_header_token(authorization, x_admin_token)
    if not allowed or not raw or raw not in allowed:
        raise HTTPException(status_code=401, detail="Admin token required")
    return True
