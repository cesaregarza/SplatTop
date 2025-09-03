import os
from typing import Optional, Set

from fastapi import Header, HTTPException, status


def _load_tokens() -> Set[str]:
    """Load allowed API tokens from environment.

    Order of precedence:
    - RIPPLE_API_TOKENS (comma-separated)
    - API_TOKENS (comma-separated)
    """

    value = os.getenv("RIPPLE_API_TOKENS") or os.getenv("API_TOKENS") or ""
    tokens = {t.strip() for t in value.split(",") if t.strip()}
    return tokens


ALLOWED_TOKENS = _load_tokens()


def require_api_token(
    authorization: Optional[str] = Header(default=None),
    x_api_token: Optional[str] = Header(
        default=None, convert_underscores=False
    ),
):
    """FastAPI dependency enforcing Bearer or X-API-Token authentication.

    - Accepts `Authorization: Bearer <token>` or `X-API-Token: <token>`.
    - Compares against tokens from env; raises 401 if missing/invalid.
    """

    if not ALLOWED_TOKENS:
        # Fail closed if no tokens configured.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token authentication is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_token:
        token = x_api_token.strip()

    if not token or token not in ALLOWED_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
