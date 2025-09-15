def test_admin_mint_rejects_past_expiry(client, override_admin, monkeypatch):
    monkeypatch.setenv("API_TOKEN_ALLOWED_SCOPES", "")
    r = client.post(
        "/api/admin/tokens",
        json={"name": "t", "expires_at_ms": 1},  # clearly in the past
    )
    assert r.status_code == 400
    assert r.json().get("detail") == "expires_at_ms must be in the future"


def test_admin_mint_accepts_future_expiry(client, override_admin, monkeypatch):
    future = 2**31 * 1000  # far in the future
    r = client.post(
        "/api/admin/tokens",
        json={"name": "t2", "expires_at_ms": future},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("expires_at_ms") == future
