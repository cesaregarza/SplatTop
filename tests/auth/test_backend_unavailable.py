def test_require_api_token_redis_unavailable_returns_503(
    client, token_builder, monkeypatch
):
    token, tid, _ = token_builder(scopes=["misc.ping"])  # ping protected
    import fast_api_app.auth as auth_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(auth_mod.redis_conn, "sismember", _boom, raising=False)
    r = client.get("/api/ping", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 503
    assert r.json().get("detail") == "Auth backend unavailable"


def test_require_scopes_redis_error_returns_503(
    client, test_token, monkeypatch
):
    import fast_api_app.auth as auth_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("down")

    # Break meta fetch during scope check
    monkeypatch.setattr(auth_mod.redis_conn, "hgetall", _boom, raising=False)
    r = client.get(
        "/api/ripple", headers={"authorization": f"Bearer {test_token}"}
    )
    assert r.status_code == 503
    assert r.json().get("detail") == "Auth backend unavailable"
