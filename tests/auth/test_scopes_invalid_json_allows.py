from shared_lib.constants import (
    API_TOKEN_HASH_MAP_PREFIX,
    API_TOKEN_META_PREFIX,
    API_TOKENS_ACTIVE_SET,
)


def test_require_scopes_invalid_json_allows(client, fake_redis, monkeypatch):
    # Build a token with invalid JSON in scopes; should allow access
    from fast_api_app.auth import hash_secret
    from shared_lib.constants import API_TOKEN_PREFIX

    monkeypatch.setenv("API_TOKEN_PEPPER", "testpepper")
    tid = "00000000-0000-4000-8000-0000000000IV"
    secret = "s"
    token = f"{API_TOKEN_PREFIX}_{tid}_{secret}"
    h = hash_secret(secret, pepper="testpepper")
    fake_redis.sadd(API_TOKENS_ACTIVE_SET, h)
    fake_redis.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h}", tid)
    # invalid JSON string
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{tid}",
        mapping={"id": tid, "hash": h, "scopes": "not-json"},
    )

    # Avoid real DB by patching fetch_ripple_page
    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch(session, **kwargs):
        return [], 0, 1700000000000, "2024.09.02"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch, raising=False
    )

    r = client.get("/api/ripple", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
