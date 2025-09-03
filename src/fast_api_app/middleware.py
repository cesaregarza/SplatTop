import time
from typing import Optional

import orjson
from fastapi import Request
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import Response

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
                # Only log ripple endpoints for now
                if request.url.path.startswith("/api/ripple"):
                    token_id: Optional[str] = getattr(
                        request.state, "token_id", None
                    )
                    event = {
                        "ts_ms": int(time.time() * 1000),
                        "token_id": token_id,
                        "path": str(request.url.path),
                        "ip": get_client_ip(request),
                        "status": int(getattr(response, "status_code", 0) or 0),
                        "latency_ms": int((time.time() - start) * 1000),
                        "ua": request.headers.get("user-agent"),
                    }
                    redis_conn.rpush(API_USAGE_QUEUE_KEY, orjson.dumps(event))
            except Exception:
                pass
        return response
