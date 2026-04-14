import sqlite3


def _build_archive_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE aliases (
            alias TEXT,
            player_id TEXT,
            last_seen DATETIME
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE season_results (
            player_id TEXT,
            season_number INTEGER,
            mode TEXT,
            region BOOLEAN,
            weapon_id INTEGER,
            x_power REAL,
            rank INTEGER
        )
        """
    )
    conn.commit()
    return conn, cursor


def test_archive_leaderboard_returns_final_season_results(client, monkeypatch):
    import fast_api_app.routes.front_page as front_page_mod

    conn, cursor = _build_archive_db()
    cursor.executemany(
        "INSERT INTO aliases (alias, player_id, last_seen) VALUES (?, ?, ?)",
        [
            ("older-tag", "p1", "2024-01-01T00:00:00"),
            ("fresh-tag", "p1", "2024-02-01T00:00:00"),
            ("player-two", "p2", "2024-02-03T00:00:00"),
        ],
    )
    cursor.executemany(
        """
        INSERT INTO season_results (
            player_id,
            season_number,
            mode,
            region,
            weapon_id,
            x_power,
            rank
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("p1", 2, "Splat Zones", 0, 1010, 2500.1, 1),
            ("p2", 2, "Splat Zones", 0, 2020, 2490.2, 2),
            ("p3", 3, "Splat Zones", 0, 3030, 2600.3, 1),
        ],
    )
    conn.commit()

    monkeypatch.setattr(front_page_mod, "sqlite_cursor", cursor, raising=False)
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


def test_archive_leaderboard_returns_503_when_no_archive_data(client, monkeypatch):
    import fast_api_app.routes.front_page as front_page_mod

    conn, cursor = _build_archive_db()
    monkeypatch.setattr(front_page_mod, "sqlite_cursor", cursor, raising=False)

    response = client.get("/api/leaderboard/archive")
    assert response.status_code == 503
    assert response.json()["detail"] == "Data is not available yet, please wait."
