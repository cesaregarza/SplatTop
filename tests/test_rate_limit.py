from shared_lib.constants import API_USAGE_QUEUE_KEY


def test_rate_limit_per_token_exceeds_per_sec(client, test_token):
    headers = {"Authorization": f"Bearer {test_token}"}
    codes = []
    # Default per_sec=10; issue 12 requests quickly
    for _ in range(12):
        res = client.get("/api/ping", headers=headers)
        codes.append(res.status_code)

    # First 10 should be 200, some of the last should be 429
    assert codes.count(200) >= 10
    assert 429 in codes


def test_rate_limit_per_ip_without_token(client):
    # Unauthenticated, rate-limited route: ripple docs
    codes = [client.get("/api/ripple/docs").status_code for _ in range(12)]
    assert codes.count(200) >= 10
    assert 429 in codes


def test_rate_limit_redis_failure_fail_closed(client, monkeypatch):
    import fast_api_app.middleware as mw_mod

    # Make pipeline() raise to simulate Redis outage
    def _boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(mw_mod.redis_conn, "pipeline", _boom, raising=False)

    res = client.get("/api/ripple/docs")
    assert res.status_code == 429
    assert res.json().get("detail") == "Rate limit temporarily unavailable"


def test_usage_middleware_enqueues_minimal_event(
    client, test_token, fake_redis
):
    headers = {"Authorization": f"Bearer {test_token}"}
    res = client.get("/api/ping", headers=headers)
    assert res.status_code == 200

    # One event enqueued
    events = fake_redis._lists.get(API_USAGE_QUEUE_KEY, [])
    assert len(events) == 1
    import orjson

    evt = orjson.loads(events[0])
    # Basic fields
    for key in ("ts_ms", "token_id", "path", "status", "latency_ms"):
        assert key in evt
    assert evt["path"] == "/api/ping"
    assert evt["status"] == 200
