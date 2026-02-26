def test_display_score_params_affect_output(client, monkeypatch, test_token):
    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch_page(session, **kwargs):
        rows = [
            {
                "rank": 1,
                "player_id": "p1",
                "display_name": "Player 1",
                "score": 2.0,
                "tournament_count": 3,
                "last_active_ms": 1700000000000,
            }
        ]
        return rows, 1, 1700000000000, "2024.09.02"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch_page, raising=False
    )

    headers = {"Authorization": f"Bearer {test_token}"}
    # offset=1.5, multiplier=10 -> (2.0 + 1.5) * 10 = 35
    res = client.get(
        "/api/ripple/leaderboard?score_offset=1.5&score_multiplier=10",
        headers=headers,
    )
    assert res.status_code == 200
    item = res.json()["data"][0]
    assert abs(item["display_score"] - 35.0) < 1e-6


def test_win_loss_ratio_fallback_to_exp_when_missing_prs(
    client, monkeypatch, test_token
):
    import math

    import fast_api_app.routes.ripple as ripple_mod

    async def fake_fetch_page(session, **kwargs):
        rows = [
            {
                "rank": 1,
                "player_id": "p1",
                "display_name": "Player 1",
                "score": 0.5,
                # win_pr/loss_pr intentionally omitted
                "tournament_count": 3,
                "last_active_ms": 1700000000000,
            }
        ]
        return rows, 1, 1700000000000, "2024.09.02"

    monkeypatch.setattr(
        ripple_mod, "fetch_ripple_page", fake_fetch_page, raising=False
    )

    headers = {"Authorization": f"Bearer {test_token}"}
    res = client.get("/api/ripple/leaderboard", headers=headers)
    assert res.status_code == 200
    item = res.json()["data"][0]
    assert abs(item["win_loss_ratio"] - math.exp(0.5)) < 1e-9
