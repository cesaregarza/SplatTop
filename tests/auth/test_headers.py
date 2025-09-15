def test_x_api_token_header_auth_works(client, token_builder):
    token, token_id, _ = token_builder(
        scopes=["misc.ping"]
    )  # ping requires token only
    r = client.get("/api/ping", headers={"X-API-Token": token})
    assert r.status_code == 200


def test_missing_token_401(client):
    r = client.get("/api/ping")
    assert r.status_code == 401
    assert r.json().get("detail") == "Missing API token"
    assert r.headers.get("www-authenticate", "").lower() == "bearer"
