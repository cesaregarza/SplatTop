"""FastAPI integration helpers for Prometheus metrics."""

from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.routing import iter_route_contexts
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.routing import BaseRoute, Host, Match, Mount
from starlette.types import Scope

from shared_lib.monitoring import (
    INFLIGHT_REQUESTS,
    METRICS_CONTENT_TYPE,
    REQUEST_COUNTER,
    REQUEST_LATENCY,
    ensure_collectors_registered,
    metrics_enabled,
    render_latest,
)

_HTTP_METHODS = frozenset(
    {
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "DELETE",
        "CONNECT",
        "OPTIONS",
        "TRACE",
        "PATCH",
    }
)


def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus middleware and endpoint when metrics are enabled."""

    if not metrics_enabled():
        return

    ensure_collectors_registered()
    app.add_middleware(PrometheusMiddleware)

    # Avoid registering the endpoint twice when the app reloads in dev.
    if not any(
        getattr(route, "path", None) == "/metrics" for route in app.routes
    ):
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

        method = request.method if request.method in _HTTP_METHODS else "OTHER"
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
    # Middleware runs before routing, so scope["route"] is not set yet. Match
    # registered templates without executing the endpoint or labeling raw URLs.
    return _match_route_path(request.scope, request.app.routes) or "unmatched"


def _match_route_path(scope: Scope, routes: Sequence[BaseRoute]) -> str | None:
    partial_path = None
    # FastAPI includes routers lazily. Its public contexts retain include_router
    # prefixes and match semantics that are absent on the original route object.
    for route in iter_route_contexts(routes):
        match, child_scope = route.matches(scope)
        if match == Match.NONE:
            continue
        if isinstance(route.original_route, (Mount, Host)):
            prefix = route.path or ""
            if not route.routes:
                return prefix + "/{path:path}"
            child_path = _match_route_path(
                {**scope, **child_scope}, route.routes
            )
            return prefix + child_path if child_path is not None else None
        if match == Match.FULL:
            return route.path
        # Keep the first method mismatch for 405s, but let a later full match
        # win just as the application router does.
        if partial_path is None:
            partial_path = route.path
    return partial_path
