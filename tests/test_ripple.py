import orjson


def test_ripple_json_shape_no_sensitive_fields(client, monkeypatch, test_token):
    # Monkeypatch DB fetch to return deterministic rows
    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch_page(session, **kwargs):
        rows = [
            {
                "rank": 1,
                "player_id": "p1",
                "display_name": "Player 1",
                "score": 1.2345,
                "win_pr": 0.6,
                "loss_pr": 0.4,
                "tournament_count": 12,
                "last_active_ms": 1725000000000,
            }
        ]
        total = 1
        calc_ts = 1725148800000
        build_version = "2024.09.01"
        return rows, total, calc_ts, build_version

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch_page, raising=False
    )

    headers = {"Authorization": f"Bearer {test_token}"}
    res = client.get("/api/ripple", headers=headers)
    assert res.status_code == 200
    payload = res.json()

    # Envelope
    assert payload["build_version"] == "2024.09.01"
    assert payload["calculated_at_ms"] == 1725148800000
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert payload["total"] == 1

    assert isinstance(payload["data"], list) and len(payload["data"]) == 1
    item = payload["data"][0]

    # Sensitive/internal fields must not be present
    for forbidden in ("exposure", "win_pr", "loss_pr", "win_loss_diff"):
        assert forbidden not in item

    # Required fields
    assert item["rank"] == 1
    assert item["player_id"] == "p1"
    assert item["display_name"] == "Player 1"
    assert item["score"] == 1.2345
    # display_score = (score + 0.0) * 25.0 by default
    assert abs(item["display_score"] - (1.2345 * 25.0)) < 1e-6
    # Provided win_pr/loss_pr yields ratio 0.6/0.4 = 1.5
    assert abs(item["win_loss_ratio"] - 1.5) < 1e-9
    assert item["tournament_count"] == 12
    assert item["last_active_ms"] == 1725000000000


def test_ripple_docs_contains_expected_sections(client):
    res = client.get("/api/ripple/docs")
    assert res.status_code == 200
    # Content-Type may include charset
    assert res.headers.get("content-type", "").startswith("text/html")
    body = res.text
    assert "Ripple API Documentation" in body
    assert "/api/ripple" in body
    assert "win_loss_ratio" in body


def test_require_scopes_allows_and_denies(client, monkeypatch, fake_redis):
    # Patch fetch for ripple to avoid DB
    import fast_api_app.routes.ripple as ripple_mod
    from fast_api_app.auth import hash_secret
    from shared_lib.constants import (
        API_TOKEN_HASH_MAP_PREFIX,
        API_TOKEN_META_PREFIX,
        API_TOKEN_PREFIX,
        API_TOKENS_ACTIVE_SET,
    )

    async def fake_fetch_page(session, **kwargs):
        return [], 0, 1725148800000, "2024.09.01"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch_page, raising=False
    )

    # 1) Allowed token: has ripple.read
    token_id_allow = "00000000-0000-4000-8000-000000000002"
    secret_allow = "allow"
    token_allow = f"{API_TOKEN_PREFIX}_{token_id_allow}_{secret_allow}"
    h_allow = hash_secret(secret_allow, pepper="testpepper")
    fake_redis.sadd(API_TOKENS_ACTIVE_SET, h_allow)
    fake_redis.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h_allow}", token_id_allow)
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id_allow}",
        mapping={
            "id": token_id_allow,
            "scopes": '["ripple.read"]',
            "hash": h_allow,
        },
    )
    r = client.get(
        "/api/ripple", headers={"Authorization": f"Bearer {token_allow}"}
    )
    assert r.status_code == 200

    # 2) Denied token: scopes present but missing ripple.read
    token_id_deny = "00000000-0000-4000-8000-000000000003"
    secret_deny = "deny"
    token_deny = f"{API_TOKEN_PREFIX}_{token_id_deny}_{secret_deny}"
    h_deny = hash_secret(secret_deny, pepper="testpepper")
    fake_redis.sadd(API_TOKENS_ACTIVE_SET, h_deny)
    fake_redis.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h_deny}", token_id_deny)
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id_deny}",
        mapping={
            "id": token_id_deny,
            "scopes": '["misc.ping"]',
            "hash": h_deny,
        },
    )
    r2 = client.get(
        "/api/ripple", headers={"Authorization": f"Bearer {token_deny}"}
    )
    assert r2.status_code == 403
    assert r2.json().get("detail") == "Insufficient scope"
