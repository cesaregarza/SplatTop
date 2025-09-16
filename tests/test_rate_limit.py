from shared_lib.constants import API_USAGE_QUEUE_KEY


def test_rate_limit_per_token_exceeds_per_sec(
    client_factory, test_token, fake_redis
):
    # Use a fresh app instance with the same fake redis where the token exists
    with client_factory(redis=fake_redis) as c:
        headers = {"Authorization": f"Bearer {test_token}"}
        codes = []
        last_429 = None
        for _ in range(12):
            res = c.get("/api/ping", headers=headers)
            codes.append(res.status_code)
            if res.status_code == 429:
                last_429 = res

        assert codes.count(200) >= 10
        assert 429 in codes
        if last_429 is not None:
            assert last_429.json().get("detail") == "Rate limit exceeded"


def test_rate_limit_per_ip_without_token(client_factory):
    # Fresh app instance to avoid cross-test counters
    with client_factory() as c:
        last_429 = None
        codes = []
        for _ in range(12):
            r = c.get("/api/ripple/docs")
            codes.append(r.status_code)
            if r.status_code == 429:
                last_429 = r
        assert codes.count(200) >= 10
        assert 429 in codes
        if last_429 is not None:
            assert last_429.json().get("detail") == "Rate limit exceeded"


"""Rate limit core behavior tests (per-token, per-IP, and usage events).

Outage behavior has been consolidated under tests/rate_limit/test_rate_limit_config.py.
"""


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
    # Known token id from test_token fixture
    assert evt["token_id"] == "00000000-0000-4000-8000-000000000001"
