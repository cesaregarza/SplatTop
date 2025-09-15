def test_admin_tokens_mint_list_revoke_smoke(client, monkeypatch, fake_redis):
    # Bypass admin auth using FastAPI dependency override to target the actual dependency callable
    import fast_api_app.routes.admin_tokens as admin_mod

    client.app.dependency_overrides[
        admin_mod.require_admin_token
    ] = lambda: True

    # Mint a token
    req = {"name": "CI token", "note": "test", "scopes": ["ripple.read"]}
    r = client.post("/api/admin/tokens", json=req)
    assert r.status_code == 200
    body = r.json()
    token_id = body["id"]
    assert body["name"] == "CI token"
    assert body["token"].startswith("rpl_")

    # List tokens contains the minted one
    r2 = client.get("/api/admin/tokens")
    assert r2.status_code == 200
    listed = r2.json().get("tokens", [])
    assert any(t.get("id") == token_id for t in listed)

    # Revoke
    r3 = client.delete(f"/api/admin/tokens/{token_id}")
    assert r3.status_code == 200
    assert r3.json().get("status") == "revoked"
