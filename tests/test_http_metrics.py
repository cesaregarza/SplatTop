"""Exercise HTTP metric cardinality without the production app's startup tasks."""

import asyncio

import httpx
import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import PlainTextResponse

from fast_api_app import metrics


@pytest.fixture
def instrumented(monkeypatch):
    registry = CollectorRegistry()
    monkeypatch.setattr(metrics, "metrics_enabled", lambda: True)
    monkeypatch.setattr(metrics, "ensure_collectors_registered", lambda: None)
    monkeypatch.setattr(
        metrics, "render_latest", lambda: generate_latest(registry)
    )
    monkeypatch.setattr(
        metrics,
        "REQUEST_COUNTER",
        Counter(
            "fastapi_requests_total",
            "Requests",
            ["method", "path", "status"],
            registry=registry,
        ),
    )
    monkeypatch.setattr(
        metrics,
        "REQUEST_LATENCY",
        Histogram(
            "fastapi_request_duration_seconds",
            "Latency",
            ["method", "path"],
            registry=registry,
        ),
    )
    monkeypatch.setattr(
        metrics,
        "INFLIGHT_REQUESTS",
        Gauge(
            "fastapi_requests_in_progress",
            "In flight",
            ["method", "path"],
            registry=registry,
        ),
    )
    app = FastAPI()
    metrics.setup_metrics(app)
    return app, registry


def _series(registry):
    return {
        (sample.name, tuple(sorted(sample.labels.items())))
        for family in registry.collect()
        for sample in family.samples
    }


def _count(registry, method, path, status):
    return registry.get_sample_value(
        "fastapi_requests_total",
        {"method": method, "path": path, "status": str(status)},
    )


def test_unique_players_searches_and_404s_do_not_grow_series(instrumented):
    app, registry = instrumented
    router = APIRouter(prefix="/api")

    @router.get("/players/{player_id}")
    async def player(player_id: str):
        return {"player_id": player_id}

    @router.get("/search/{query:path}")
    async def search(query: str):
        return {"query": query}

    app.include_router(router)
    with TestClient(app) as client:
        for index in range(101):
            assert (
                client.get(f"/api/players/private-{index}").status_code == 200
            )
            assert (
                client.get(
                    f"/api/search/private-{index}/more?q={index}"
                ).status_code
                == 200
            )
            assert client.get(f"/missing/private-{index}").status_code == 404
            if index == 0:
                initial_series = _series(registry)
        assert _series(registry) == initial_series
        body = client.get("/metrics").text
    assert "private-" not in body
    assert _count(registry, "GET", "/api/players/{player_id}", 200) == 101
    assert _count(registry, "GET", "/api/search/{query:path}", 200) == 101
    assert _count(registry, "GET", "unmatched", 404) == 101
    assert all(
        sample.value == 0
        for family in registry.collect()
        for sample in family.samples
        if sample.name == "fastapi_requests_in_progress"
    )


def test_nested_include_prefixes_are_preserved(instrumented):
    app, registry = instrumented
    nested = APIRouter()

    @nested.get("/players/{player_id}")
    async def player(player_id: str):
        return player_id

    parent = APIRouter(prefix="/api")
    parent.include_router(nested, prefix="/v1")
    app.include_router(parent, prefix="/public")
    with TestClient(app) as client:
        assert client.get("/public/api/v1/players/42").status_code == 200
    assert (
        _count(registry, "GET", "/public/api/v1/players/{player_id}", 200) == 1
    )


def test_full_method_match_wins_over_earlier_partial_match(instrumented):
    app, registry = instrumented

    @app.get("/items/{item_id}")
    async def get_item(item_id: str):
        return item_id

    @app.post("/items/fixed")
    async def post_item():
        return "posted"

    with TestClient(app) as client:
        assert client.post("/items/fixed").status_code == 200
        assert client.delete("/items/42").status_code == 405
    assert _count(registry, "POST", "/items/fixed", 200) == 1
    assert _count(registry, "DELETE", "/items/{item_id}", 405) == 1


def test_arbitrary_http_methods_share_one_label(instrumented):
    app, registry = instrumented

    @app.get("/items/{item_id}")
    async def get_item(item_id: str):
        return item_id

    with TestClient(app) as client:
        for index in range(30):
            assert (
                client.request(f"CUSTOM{index}", f"/items/{index}").status_code
                == 405
            )
            if index == 0:
                initial_series = _series(registry)
        assert _series(registry) == initial_series
    assert _count(registry, "OTHER", "/items/{item_id}", 405) == 30


@pytest.mark.parametrize("status", [404, 503, 500])
def test_error_responses_keep_template_and_clear_inflight(instrumented, status):
    app, registry = instrumented

    @app.get("/fail/{item_id}")
    async def fail(item_id: str):
        if status == 500:
            raise RuntimeError("test failure")
        raise HTTPException(status_code=status)

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/fail/42").status_code == status
    assert _count(registry, "GET", "/fail/{item_id}", status) == 1
    assert (
        registry.get_sample_value(
            "fastapi_requests_in_progress",
            {"method": "GET", "path": "/fail/{item_id}"},
        )
        == 0
    )


def test_redirects_use_a_fixed_fallback(instrumented):
    app, registry = instrumented

    @app.get("/items/{item_id}/")
    async def get_item(item_id: str):
        return item_id

    with TestClient(app, follow_redirects=False) as client:
        for index in range(10):
            assert client.get(f"/items/{index}").status_code == 307
    assert _count(registry, "GET", "unmatched", 307) == 10


def test_mount_templates_exclude_tenant_ids_and_missing_paths(instrumented):
    app, registry = instrumented
    child = FastAPI()

    @child.get("/items/{item_id}")
    async def get_item(item_id: str):
        return item_id

    app.mount("/tenants/{tenant_id}", child)
    with TestClient(app) as client:
        for index in range(10):
            assert (
                client.get(
                    f"/tenants/private-{index}/items/{index}"
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/tenants/private-{index}/missing/{index}"
                ).status_code
                == 404
            )
    assert (
        _count(registry, "GET", "/tenants/{tenant_id}/items/{item_id}", 200)
        == 10
    )
    assert _count(registry, "GET", "unmatched", 404) == 10
    assert "private-" not in generate_latest(registry).decode()


def test_opaque_asgi_mount_uses_registered_prefix(instrumented):
    app, registry = instrumented

    async def opaque(scope, receive, send):
        await PlainTextResponse("ok")(scope, receive, send)

    app.mount("/assets", opaque)
    with TestClient(app) as client:
        assert client.get("/assets/arbitrary/file.txt").status_code == 200
    assert _count(registry, "GET", "/assets/{path:path}", 200) == 1


def test_proxy_root_path_does_not_become_a_label(instrumented):
    app, registry = instrumented

    @app.get("/items/{item_id}")
    async def get_item(item_id: str):
        return item_id

    with TestClient(app, root_path="/proxy") as client:
        assert client.get("/proxy/items/42").status_code == 200
    assert _count(registry, "GET", "/items/{item_id}", 200) == 1


def test_metrics_scrapes_are_not_instrumented(instrumented):
    app, registry = instrumented
    with TestClient(app) as client:
        for _ in range(3):
            assert client.get("/metrics?format=prometheus").status_code == 200
    assert not _series(registry)


def test_inflight_is_counted_while_handler_is_running(instrumented):
    app, registry = instrumented

    async def exercise():
        entered = asyncio.Event()
        release = asyncio.Event()

        @app.get("/slow/{item_id}")
        async def slow(item_id: str):
            entered.set()
            await release.wait()
            return item_id

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            task = asyncio.create_task(client.get("/slow/private-id"))
            try:
                await asyncio.wait_for(entered.wait(), timeout=5)
                assert (
                    registry.get_sample_value(
                        "fastapi_requests_in_progress",
                        {"method": "GET", "path": "/slow/{item_id}"},
                    )
                    == 1
                )
            finally:
                release.set()
                response = await asyncio.wait_for(task, timeout=5)
            assert response.status_code == 200
        assert (
            registry.get_sample_value(
                "fastapi_requests_in_progress",
                {"method": "GET", "path": "/slow/{item_id}"},
            )
            == 0
        )

    asyncio.run(exercise())
