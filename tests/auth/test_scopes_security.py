from typing import Any

import pytest

from shared_lib.constants import API_TOKEN_META_PREFIX


def _mock_ripple(monkeypatch: pytest.MonkeyPatch) -> None:
    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch(session, **kwargs):
        return [], 0, 1700000000000, "2024.09.02"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch, raising=False
    )


def test_invalid_json_scopes_denies_access(
    client: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
    token_builder: Any,
) -> None:
    _mock_ripple(monkeypatch)
    token, token_id, _ = token_builder(scopes=["ripple.read"])
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id}",
        mapping={"scopes": "not-valid-json"},
    )

    response = client.get(
        "/api/ripple", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in (401, 503)


def test_empty_scopes_allows_access(
    client: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
    token_builder: Any,
) -> None:
    _mock_ripple(monkeypatch)
    token, token_id, _ = token_builder(scopes=[])
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id}",
        mapping={"scopes": "[]"},
    )

    response = client.get(
        "/api/ripple", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_valid_scopes_with_required_scope_allows(
    client: Any, monkeypatch: pytest.MonkeyPatch, token_builder: Any
) -> None:
    _mock_ripple(monkeypatch)
    token, _, _ = token_builder(scopes=["ripple.read"])

    response = client.get(
        "/api/ripple", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_valid_scopes_without_required_scope_denies(
    client: Any, monkeypatch: pytest.MonkeyPatch, token_builder: Any
) -> None:
    _mock_ripple(monkeypatch)
    token, _, _ = token_builder(scopes=["other.scope"])

    response = client.get(
        "/api/ripple", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_corrupted_redis_scope_data_denies(
    client: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
    token_builder: Any,
) -> None:
    _mock_ripple(monkeypatch)
    token, token_id, _ = token_builder(scopes=["ripple.read"])
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id}",
        mapping={"scopes": 12345},
    )

    response = client.get(
        "/api/ripple", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in (401, 503)
