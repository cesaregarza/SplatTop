def test_admin_mint_unknown_scope_400(client, monkeypatch, override_admin):
    import fast_api_app.routes.admin_tokens as admin_mod

    # Only allow ripple.read
    monkeypatch.setenv("API_TOKEN_ALLOWED_SCOPES", "ripple.read")

    r = client.post(
        "/api/admin/tokens",
        json={"name": "t", "scopes": ["unknown.scope"]},
    )
    assert r.status_code == 400
    assert "Unknown scopes" in r.json().get("detail", "")


def test_admin_mint_invalid_scope_format_400(
    client, monkeypatch, override_admin
):
    import fast_api_app.routes.admin_tokens as admin_mod

    # Clear allowlist -> regex validation applies
    monkeypatch.delenv("API_TOKEN_ALLOWED_SCOPES", raising=False)

    r = client.post(
        "/api/admin/tokens",
        json={"name": "t", "scopes": ["bad scope"]},
    )
    assert r.status_code == 400
    assert "Invalid scope format" in r.json().get("detail", "")


def test_admin_token_limit_reached_429(
    client, monkeypatch, fake_redis, override_admin
):
    import fast_api_app.routes.admin_tokens as admin_mod
    from shared_lib.constants import API_TOKENS_ACTIVE_SET

    # Cap at 1 and pre-seed one id
    monkeypatch.setenv("ADMIN_MAX_API_TOKENS", "1")
    fake_redis.sadd(API_TOKENS_ACTIVE_SET, "existing-hash")
    r = client.post("/api/admin/tokens", json={"name": "t"})
    assert r.status_code == 429
    assert "limit" in r.json().get("detail", "")
