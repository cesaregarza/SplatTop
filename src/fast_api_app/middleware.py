import os
import time
from typing import Optional

import orjson
from fastapi import Request
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import JSONResponse, Response

from fast_api_app.auth import _get_header_token
from fast_api_app.connections import redis_conn
from fast_api_app.utils import get_client_ip
from shared_lib.constants import API_USAGE_QUEUE_KEY


class APITokenUsageMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.time()
        response: Response
        try:
            response = await call_next(request)
        finally:
            # Best-effort logging; do not raise.
            try:
                # Log API endpoints (exclude admin)
                if request.url.path.startswith(
                    "/api/"
                ) and not request.url.path.startswith("/api/admin"):
                    token_id: Optional[str] = getattr(
                        request.state, "token_id", None
                    )
                    event = {
                        "ts_ms": int(time.time() * 1000),
                        "token_id": token_id,
                        "path": str(request.url.path),
                        "method": request.method,
                        "ip": get_client_ip(request),
                        "status": int(getattr(response, "status_code", 0) or 0),
                        "latency_ms": int((time.time() - start) * 1000),
                        "ua": request.headers.get("user-agent"),
                    }
                    redis_conn.rpush(API_USAGE_QUEUE_KEY, orjson.dumps(event))
            except Exception:
                pass
        return response


class APITokenRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-token and per-IP fixed-window rate limiting using Redis.

    Defaults (override via env):
      - API_RL_PER_SEC (default 10)
      - API_RL_PER_MIN (default 120)
    Applies to /api/* except /api/admin/*.
    Identity: a stable SHA-256 hash of the provided token header when present,
    otherwise the client IP. This deliberately does not use the auth pepper to
    avoid coupling rate-limiting identity to auth configuration.
    """

    def __init__(self, app):
        super().__init__(app)
        try:
            self.per_sec = int(os.getenv("API_RL_PER_SEC", "10"))
        except Exception:
            self.per_sec = 10
        try:
            self.per_min = int(os.getenv("API_RL_PER_MIN", "120"))
        except Exception:
            self.per_min = 120
        # Fail-open toggle (default false = fail-closed)
        self.fail_open = os.getenv("API_RL_FAIL_OPEN", "0").lower() in (
            "1",
            "true",
            "yes",
        )

    def _identity(self, request: Request) -> str:
        # Prefer token-based identity when a token header is present.
        # Use a stable hash of the entire provided token string so malformed
        # tokens cannot switch identity and bypass limits.
        raw = _get_header_token(
            request.headers.get("authorization"),
            request.headers.get("x-api-token"),
        )
        if raw:
            # Use a simple, stable hash independent of auth pepper.
            import hashlib

            th = hashlib.sha256(raw.encode()).hexdigest()
            return f"tok:{th}"
        return f"ip:{get_client_ip(request)}"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path or ""
        if path.startswith("/api/") and not path.startswith("/api/admin"):
            now = int(time.time())
            ident = self._identity(request)
            sec_key = f"api:rl:sec:{ident}:{now}"
            min_key = f"api:rl:min:{ident}:{now // 60}"
            try:
                pipe = redis_conn.pipeline()
                pipe.incr(sec_key)
                pipe.expire(sec_key, 2)
                pipe.incr(min_key)
                pipe.expire(min_key, 120)
                sec_count, _, min_count, _ = pipe.execute()
                if (self.per_sec and int(sec_count) > self.per_sec) or (
                    self.per_min and int(min_count) > self.per_min
                ):
                    # Too many requests
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"},
                    )
            except Exception:
                # Redis unavailable: fail-closed by default (configurable)
                if not self.fail_open:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit temporarily unavailable"
                        },
                    )

        return await call_next(request)
