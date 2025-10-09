"""FastAPI integration helpers for Prometheus metrics."""

from __future__ import annotations

from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from shared_lib.monitoring import (
    INFLIGHT_REQUESTS,
    METRICS_CONTENT_TYPE,
    REQUEST_COUNTER,
    REQUEST_LATENCY,
    ensure_collectors_registered,
    metrics_enabled,
    render_latest,
)


def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus middleware and endpoint when metrics are enabled."""

    if not metrics_enabled():
        return

    ensure_collectors_registered()
    app.add_middleware(PrometheusMiddleware)

    # Avoid registering the endpoint twice when the app reloads in dev.
    if not any(getattr(route, "path", None) == "/metrics" for route in app.routes):
        app.add_api_route(
            "/metrics",
            metrics_endpoint,
            methods=["GET"],
            include_in_schema=False,
            name="metrics",
        )


async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""

    return Response(content=render_latest(), media_type=METRICS_CONTENT_TYPE)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Minimal middleware that records request metrics."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not metrics_enabled() or request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = _resolve_route_path(request)

        start = perf_counter()
        INFLIGHT_REQUESTS.labels(method, path).inc()
        status_code = "500"
        try:
            response = await call_next(request)
            status_code = str(getattr(response, "status_code", "500"))
            return response
        finally:
            duration = perf_counter() - start
            INFLIGHT_REQUESTS.labels(method, path).dec()
            REQUEST_LATENCY.labels(method, path).observe(duration)
            REQUEST_COUNTER.labels(method, path, status_code).inc()


def _resolve_route_path(request: Request) -> str:
    route = request.scope.get("route")
    if route and getattr(route, "path", None):
        return route.path
    raw_path = request.url.path
    return raw_path.split("?")[0]
