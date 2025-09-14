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

from fast_api_app.auth import _get_header_token, hash_secret, parse_token
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
    Identity: token hash if provided, else client IP.
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

    def _identity(self, request: Request) -> str:
        # Prefer token-based identity when available
        try:
            raw = _get_header_token(
                request.headers.get("authorization"),
                request.headers.get("x-api-token"),
            )
            if raw:
                token_id, secret = parse_token(raw)
                if secret:
                    th = hash_secret(secret)
                    return f"tok:{th}"
        except Exception:
            # Fallback to IP
            pass
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
                        content={
                            "detail": "Rate limit exceeded",
                            "identity": ident.split(":", 1)[0],
                        },
                    )
            except Exception:
                # In case Redis is unavailable, fail-open
                pass

        return await call_next(request)
