def test_ripple_raw_includes_raw_fields(client, monkeypatch, test_token):
    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch_page(session, **kwargs):
        rows = [
            {
                "rank": 1,
                "player_id": "p1",
                "display_name": "Player 1",
                "score": 1.0,
                "win_pr": 0.7,
                "loss_pr": 0.3,
                "win_loss_diff": 0.4,
            }
        ]
        return rows, 1, 1700000000000, "2024.09.02"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch_page, raising=False
    )

    headers = {"Authorization": f"Bearer {test_token}"}
    res = client.get("/api/ripple/leaderboard/raw", headers=headers)
    assert res.status_code == 200
    item = res.json()["data"][0]
    # Raw should include as-is fields like win_pr/loss_pr
    assert item["win_pr"] == 0.7
    assert item["loss_pr"] == 0.3
    assert item["win_loss_diff"] == 0.4


def test_ripple_danger_days_left_and_shape(client, monkeypatch, test_token):
    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch_danger(session, **kwargs):
        rows = [
            {
                "player_rank": 5,
                "player_id": "p1",
                "display_name": "Player 1",
                "score": 0.0,
                "window_count": 3,
                "oldest_in_window_ms": 1700000000000,
                "next_expiry_ms": 1700864000000,  # +10 days
                "ms_left": 10 * 86400000,
            }
        ]
        return rows, 1, 1700000000000, "2024.09.02"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_danger", fake_fetch_danger, raising=False
    )

    headers = {"Authorization": f"Bearer {test_token}"}
    res = client.get("/api/ripple/leaderboard/danger", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["limit"] == 20
    assert body["offset"] == 0
    item = body["data"][0]
    assert item["rank"] == 5
    assert item["window_tournament_count"] == 3
    assert abs(item["days_left"] - 10.0) < 1e-6


def test_ripple_danger_days_left_none_when_missing(
    client, monkeypatch, test_token
):
    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch_danger(session, **kwargs):
        rows = [
            {
                "player_rank": 2,
                "player_id": "px",
                "display_name": "P X",
                "score": 1.0,
                "window_count": 4,
                # ms_left intentionally None/missing
            }
        ]
        return rows, 1, 1700000000000, "2024.09.02"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_danger", fake_fetch_danger, raising=False
    )

    headers = {"authorization": f"Bearer {test_token}"}
    r = client.get("/api/ripple/leaderboard/danger", headers=headers)
    assert r.status_code == 200
    item = r.json()["data"][0]
    assert item.get("days_left") is None
    # display_score uses default multiplier/offset
    assert abs(item["display_score"] - 25.0) < 1e-6
