from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException


def _set_comp_auth_env(monkeypatch, frontend_url="http://comp.localhost:3000"):
    monkeypatch.setenv("COMP_AUTH_SESSION_SECRET", "test-comp-session-secret")
    monkeypatch.setenv("COMP_DISCORD_CLIENT_ID", "discord-client-id")
    monkeypatch.setenv("COMP_DISCORD_CLIENT_SECRET", "discord-client-secret")
    monkeypatch.setenv(
        "COMP_DISCORD_REDIRECT_URI",
        "http://localhost:5000/api/comp-auth/discord/callback",
    )
    monkeypatch.setenv("COMP_AUTH_FRONTEND_URL", frontend_url)


def _start_login(client):
    response = client.get(
        "/api/comp-auth/discord/login",
        params={
            "next": "http://comp.localhost:3000/u/p1?tab=history#match-ups"
        },
        follow_redirects=False,
    )
    query = parse_qs(urlparse(response.headers["location"]).query)
    return response, query["state"][0]


def test_comp_auth_login_redirects_to_discord_with_state(client, monkeypatch):
    _set_comp_auth_env(monkeypatch)

    response = client.get(
        "/api/comp-auth/discord/login",
        params={"next": "/u/p1"},
        follow_redirects=False,
    )

    assert response.status_code == 302

    redirect = urlparse(response.headers["location"])
    query = parse_qs(redirect.query)
    assert redirect.scheme == "https"
    assert redirect.netloc == "discord.com"
    assert redirect.path == "/oauth2/authorize"
    assert query["client_id"] == ["discord-client-id"]
    assert query["redirect_uri"] == [
        "http://localhost:5000/api/comp-auth/discord/callback"
    ]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["identify"]
    assert len(query["state"][0]) >= 20


def test_comp_auth_callback_success_sets_session_and_redirects(
    client, monkeypatch
):
    _set_comp_auth_env(monkeypatch)
    import fast_api_app.routes.comp_auth as comp_auth_mod

    async def _fake_exchange(code):
        assert code == "discord-code"
        return "123456789012345678"

    monkeypatch.setattr(
        comp_auth_mod,
        "exchange_discord_code_for_user_id",
        _fake_exchange,
    )

    _, state = _start_login(client)

    response = client.get(
        "/api/comp-auth/discord/callback",
        params={"code": "discord-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert (
        response.headers["location"]
        == "http://comp.localhost:3000/u/p1?tab=history#match-ups"
    )

    me_response = client.get("/api/comp-auth/me")
    assert me_response.status_code == 200
    assert me_response.json() == {
        "available": True,
        "authenticated": True,
        "discord_id": "123456789012345678",
    }


def test_comp_auth_callback_rejects_invalid_state(client, monkeypatch):
    _set_comp_auth_env(monkeypatch)

    _start_login(client)

    response = client.get(
        "/api/comp-auth/discord/callback",
        params={"code": "discord-code", "state": "wrong-state"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Discord login state"

    me_response = client.get("/api/comp-auth/me")
    assert me_response.json() == {
        "available": True,
        "authenticated": False,
        "discord_id": None,
    }


def test_comp_auth_callback_handles_discord_failure(client, monkeypatch):
    _set_comp_auth_env(monkeypatch)
    import fast_api_app.routes.comp_auth as comp_auth_mod

    async def _boom(_code):
        raise HTTPException(
            status_code=502, detail="Discord auth request failed"
        )

    monkeypatch.setattr(
        comp_auth_mod,
        "exchange_discord_code_for_user_id",
        _boom,
    )

    _, state = _start_login(client)

    response = client.get(
        "/api/comp-auth/discord/callback",
        params={"code": "discord-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Discord auth request failed"
    assert client.get("/api/comp-auth/me").json() == {
        "available": True,
        "authenticated": False,
        "discord_id": None,
    }


def test_comp_auth_me_and_logout(client, monkeypatch):
    _set_comp_auth_env(monkeypatch)
    import fast_api_app.routes.comp_auth as comp_auth_mod

    async def _fake_exchange(_code):
        return "24680"

    monkeypatch.setattr(
        comp_auth_mod,
        "exchange_discord_code_for_user_id",
        _fake_exchange,
    )

    assert client.get("/api/comp-auth/me").json() == {
        "available": True,
        "authenticated": False,
        "discord_id": None,
    }

    _, state = _start_login(client)
    callback_response = client.get(
        "/api/comp-auth/discord/callback",
        params={"code": "discord-code", "state": state},
        follow_redirects=False,
    )
    assert callback_response.status_code == 302

    logout_response = client.post("/api/comp-auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {
        "available": True,
        "authenticated": False,
        "discord_id": None,
    }
    assert client.get("/api/comp-auth/me").json() == {
        "available": True,
        "authenticated": False,
        "discord_id": None,
    }


def test_comp_auth_me_reports_unavailable_when_not_configured(client):
    response = client.get("/api/comp-auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "available": False,
        "authenticated": False,
        "discord_id": None,
    }
