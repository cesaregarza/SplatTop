import pytest


@pytest.mark.parametrize(
    "path,fetch_attr",
    [
        ("/api/ripple/raw?limit=7&offset=3", "fetch_ripple_page"),
        ("/api/ripple/danger?limit=9&offset=4", "fetch_ripple_danger"),
    ],
)
def test_echoes_limit_offset_parametrized(
    client, monkeypatch, test_token, path, fetch_attr
):
    import fast_api_app.routes.ripple as ripple_mod

    async def _fake_fetch(session, **kwargs):
        return [], 0, 1700000000000, "2024.09.02"

    monkeypatch.setattr(ripple_mod, fetch_attr, _fake_fetch, raising=False)

    headers = {"authorization": f"Bearer {test_token}"}
    r = client.get(path, headers=headers)
    assert r.status_code == 200
    body = r.json()
    # Pull limit/offset from the query in the parametrized path
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(path).query)
    expected_limit = int(qs.get("limit", [0])[0])
    expected_offset = int(qs.get("offset", [0])[0])
    assert body["limit"] == expected_limit
    assert body["offset"] == expected_offset
