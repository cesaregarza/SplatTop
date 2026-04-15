def test_archive_leaderboard_returns_final_season_results(client, monkeypatch):
    import fast_api_app.routes.front_page as front_page_mod

    archive_rows = [
        (2,),
        (1,),
    ]
    archive_columns = [
        "player_id",
        "splashtag",
        "rank",
        "x_power",
        "weapon_id",
    ]
    archive_result_rows = [
        ("p1", "fresh-tag", 1, 2500.1, 1010),
        ("p2", "player-two", 2, 2490.2, 2020),
    ]

    monkeypatch.setattr(
        front_page_mod,
        "lookup_fetchall",
        lambda query, params=(): archive_rows,
        raising=False,
    )
    monkeypatch.setattr(
        front_page_mod,
        "lookup_fetchall_with_columns",
        lambda query, params=(): (archive_columns, archive_result_rows),
        raising=False,
    )
    monkeypatch.setattr(
        front_page_mod,
        "get_weapon_image",
        lambda weapon_id: f"/weapons/{weapon_id}.png",
        raising=False,
    )

    response = client.get(
        "/api/leaderboard/archive?mode=Splat%20Zones&region=Tentatek&season=1"
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["season_number"] == 1
    assert payload["available_seasons"] == [2, 1]
    assert payload["players"]["rank"] == [1, 2]
    assert payload["players"]["splashtag"] == ["fresh-tag", "player-two"]
    assert payload["players"]["x_power"] == [2500.1, 2490.2]
    assert payload["players"]["weapon_image"] == [
        "/weapons/1010.png",
        "/weapons/2020.png",
    ]


def test_archive_leaderboard_returns_503_when_no_archive_data(
    client, monkeypatch
):
    response = client.get("/api/leaderboard/archive")
    assert response.status_code == 503
    assert (
        response.json()["detail"] == "Data is not available yet, please wait."
    )
