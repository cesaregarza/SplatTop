from hashlib import sha256


def test_admin_header_allows_when_hashed_matches(client, monkeypatch):
    secret = "adm1n"
    monkeypatch.setenv("ADMIN_TOKEN_PEPPER", "pep")
    hashed = sha256(("pep" + secret).encode()).hexdigest()
    monkeypatch.setenv("ADMIN_API_TOKENS_HASHED", hashed)

    r = client.get(
        "/api/admin/tokens", headers={"Authorization": f"Bearer {secret}"}
    )
    assert r.status_code == 200


def test_admin_header_invalid_returns_401(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN_PEPPER", "pep")
    # Configure some other hash
    monkeypatch.setenv(
        "ADMIN_API_TOKENS_HASHED",
        sha256(("pep" + "other").encode()).hexdigest(),
    )
    r = client.get(
        "/api/admin/tokens", headers={"Authorization": "Bearer nope"}
    )
    assert r.status_code == 401
    assert r.json().get("detail") == "Admin token required"
