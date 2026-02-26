import math
import time


def test_require_api_token_missing_pepper_fails_closed(client_factory):
    # Build an app where API_TOKEN_PEPPER is unset
    with client_factory(env={"API_TOKEN_PEPPER": None}) as c:
        # Any token format is fine; hashing should fail closed due to missing pepper
        r = c.get(
            "/api/ping",
            headers={
                "Authorization": "Bearer rpl_00000000-0000-4000-8000-000000000000_x"
            },
        )
        assert r.status_code == 401
        assert r.json().get("detail") == "API token system is not configured"


def test_require_api_token_expired_401(client, fake_redis, monkeypatch):
    # Create an expired token
    from fast_api_app.auth import hash_secret
    from shared_lib.constants import (
        API_TOKEN_HASH_MAP_PREFIX,
        API_TOKEN_META_PREFIX,
        API_TOKEN_PREFIX,
        API_TOKENS_ACTIVE_SET,
    )

    token_id = "00000000-0000-4000-8000-0000000000EE"
    secret = "expired"
    token = f"{API_TOKEN_PREFIX}_{token_id}_{secret}"
    h = hash_secret(secret, pepper="testpepper")
    fake_redis.sadd(API_TOKENS_ACTIVE_SET, h)
    fake_redis.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h}", token_id)
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id}",
        mapping={
            "id": token_id,
            "hash": h,
            "scopes": '["ripple.read"]',
            # Expired 1 second in the past
            "expires_at_ms": int(time.time() * 1000) - 1000,
        },
    )

    r = client.get("/api/ping", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json().get("detail") == "Expired API token"


def test_require_scopes_empty_scopes_allow(client, fake_redis, monkeypatch):
    # Empty scopes should allow access (backward-compat behavior)
    import fast_api_app.routes.ripple as ripple_mod
    from fast_api_app.auth import hash_secret
    from shared_lib.constants import (
        API_TOKEN_HASH_MAP_PREFIX,
        API_TOKEN_META_PREFIX,
        API_TOKEN_PREFIX,
        API_TOKENS_ACTIVE_SET,
    )

    async def fake_fetch(session, **kwargs):
        return [], 0, 1725000000000, "2024.09.01"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch, raising=False
    )

    token_id = "00000000-0000-4000-8000-0000000000OK"
    secret = "ok"
    token = f"{API_TOKEN_PREFIX}_{token_id}_{secret}"
    h = hash_secret(secret, pepper="testpepper")
    fake_redis.sadd(API_TOKENS_ACTIVE_SET, h)
    fake_redis.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h}", token_id)
    # Set empty scopes (stringified JSON)
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id}",
        mapping={"id": token_id, "hash": h, "scopes": "[]"},
    )

    r = client.get(
        "/api/ripple/leaderboard", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
