import os

import orjson
import pandas as pd
import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")

from celery_app.tasks import leaderboard as leaderboard_mod


def _frame(rows):
    return pd.DataFrame(rows).set_index(leaderboard_mod.idx_columns)


def test_aggregate_weapon_rows_normalizes_alt_kits_and_usage():
    rows = [
        {
            "player_id": "p1",
            "season_number": 14,
            "mode": "Splat Zones",
            "region": False,
            "weapon_id": 40,
            "max_x_power": 2500.0,
            "games_played": 6,
        },
        {
            "player_id": "p1",
            "season_number": 14,
            "mode": "Splat Zones",
            "region": False,
            "weapon_id": 1101,
            "max_x_power": 2600.0,
            "games_played": 4,
        },
        {
            "player_id": "p1",
            "season_number": 14,
            "mode": "Splat Zones",
            "region": False,
            "weapon_id": 50,
            "max_x_power": 2550.0,
            "games_played": 10,
        },
    ]

    result = leaderboard_mod._aggregate_weapon_rows(
        rows, {"1101": "40"}
    ).reset_index()

    canonical = result[result["weapon_id"] == "40"].iloc[0]
    other = result[result["weapon_id"] == "50"].iloc[0]
    assert canonical["max_x_power"] == 2600.0
    assert canonical["games_played"] == 10
    assert canonical["percent_games_played"] == pytest.approx(0.5)
    assert other["percent_games_played"] == pytest.approx(0.5)
    assert result["percent_games_played"].sum() == pytest.approx(1.0)


def test_missing_completed_seasons_finds_rollover_gap():
    assert leaderboard_mod._completed_seasons_to_derive(
        archived_seasons=set(range(1, 14)),
        current_season=15,
    ) == [14]


def test_latest_completed_season_is_derived_during_archive_handoff():
    assert leaderboard_mod._completed_seasons_to_derive(
        archived_seasons=set(range(1, 15)),
        current_season=15,
    ) == [14]


def test_no_completed_season_exists_below_supported_floor():
    assert (
        leaderboard_mod._completed_seasons_to_derive(
            archived_seasons=set(),
            current_season=leaderboard_mod.FIRST_WEAPON_LEADERBOARD_SEASON,
        )
        == []
    )


def test_combine_weapon_leaderboards_keeps_archive_on_collision():
    archive = _frame(
        [
            {
                "player_id": "p1",
                "season_number": 13,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": 40,
                "max_x_power": 2500.0,
                "games_played": 20,
                "percent_games_played": 1.0,
            }
        ]
    )
    derived = _frame(
        [
            {
                "player_id": "p1",
                "season_number": 13,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": "40",
                "max_x_power": 9999.0,
                "games_played": 1,
                "percent_games_played": 1.0,
            },
            {
                "player_id": "p1",
                "season_number": 14,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": "40",
                "max_x_power": 2600.0,
                "games_played": 30,
                "percent_games_played": 1.0,
            },
        ]
    )
    live = _frame(
        [
            {
                "player_id": "p1",
                "season_number": 15,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": "40",
                "max_x_power": 2700.0,
                "games_played": 5,
                "percent_games_played": 1.0,
            }
        ]
    )

    result = leaderboard_mod._combine_weapon_leaderboards(
        [archive, derived, live]
    ).reset_index()

    assert result["season_number"].tolist() == [13, 14, 15]
    assert (
        result.loc[result["season_number"] == 13, "max_x_power"].item()
        == 2500.0
    )
    assert (
        not result.assign(weapon_id_key=result["weapon_id"].astype(str))
        .duplicated(subset=leaderboard_mod.idx_columns + ["weapon_id_key"])
        .any()
    )


class _FakeRow:
    def __init__(self, values):
        self.values = values

    def __getitem__(self, index):
        return list(self.values.values())[index]

    def _asdict(self):
        return self.values


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _FakeSession:
    def __init__(self):
        self.derived_seasons = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params):
        season_number = params["season_number"]
        self.derived_seasons.append(season_number)
        return _FakeResult(
            [
                _FakeRow(
                    {
                        "player_id": "p1",
                        "season_number": season_number,
                        "mode": "Splat Zones",
                        "region": False,
                        "weapon_id": 40,
                        "max_x_power": 2600.0,
                        "games_played": 10,
                    }
                )
            ]
        )


def test_fetch_missing_completed_rows_only_queries_archive_gap(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(leaderboard_mod, "Session", lambda: session)

    result = leaderboard_mod.fetch_completed_weapon_leaderboard_fallback_data(
        archived_seasons=set(range(1, 14)),
        current_season=15,
        alt_kits={},
    ).reset_index()

    assert session.derived_seasons == [14]
    assert result["season_number"].tolist() == [14]
    assert result["percent_games_played"].tolist() == [1.0]


def test_fetch_weapon_leaderboard_publishes_archive_fallback_and_live(
    monkeypatch,
):
    archive = _frame(
        [
            {
                "player_id": "archived",
                "season_number": 13,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": 40,
                "max_x_power": 2500.0,
                "games_played": 20,
                "percent_games_played": 1.0,
            },
            {
                "player_id": "collision",
                "season_number": 14,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": 40,
                "max_x_power": 2600.0,
                "games_played": 30,
                "percent_games_played": 1.0,
            },
        ]
    )
    fallback = _frame(
        [
            {
                "player_id": "collision",
                "season_number": 14,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": "40",
                "max_x_power": 9999.0,
                "games_played": 1,
                "percent_games_played": 1.0,
            },
            {
                "player_id": "recovered",
                "season_number": 14,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": "40",
                "max_x_power": 2700.0,
                "games_played": 40,
                "percent_games_played": 1.0,
            },
        ]
    )
    live = _frame(
        [
            {
                "player_id": "live",
                "season_number": 15,
                "mode": "Splat Zones",
                "region": False,
                "weapon_id": "40",
                "max_x_power": 2800.0,
                "games_played": 5,
                "percent_games_played": 1.0,
            }
        ]
    )
    calls = {}

    class _CurrentSeasonSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    class _Redis:
        def __init__(self):
            self.values = {}

        def set(self, key, value):
            self.values[key] = value

    redis = _Redis()

    def fetch_fallback(archived_seasons, current_season, alt_kits):
        calls["fallback"] = (archived_seasons, current_season, alt_kits)
        return fallback

    def fetch_live(current_season, alt_kits):
        calls["live"] = (current_season, alt_kits)
        return live

    monkeypatch.setattr(
        leaderboard_mod, "fetch_past_weapon_leaderboard_data", lambda: archive
    )
    monkeypatch.setattr(
        leaderboard_mod,
        "fetch_completed_weapon_leaderboard_fallback_data",
        fetch_fallback,
    )
    monkeypatch.setattr(
        leaderboard_mod, "fetch_live_weapon_leaderboard_data", fetch_live
    )
    monkeypatch.setattr(
        leaderboard_mod, "Session", lambda: _CurrentSeasonSession()
    )
    monkeypatch.setattr(
        leaderboard_mod, "fetch_current_season", lambda session: 15
    )
    monkeypatch.setattr(
        leaderboard_mod, "get_all_alt_kits", lambda: {"1101": "40"}
    )
    monkeypatch.setattr(leaderboard_mod, "redis_conn", redis)

    leaderboard_mod.fetch_weapon_leaderboard()

    assert calls == {
        "fallback": ({13, 14}, 15, {"1101": "40"}),
        "live": (15, {"1101": "40"}),
    }
    payload = orjson.loads(
        redis.values[leaderboard_mod.WEAPON_LEADERBOARD_PEAK_REDIS_KEY]
    )
    assert len(payload) == 4
    collision = next(row for row in payload if row["player_id"] == "collision")
    assert collision["max_x_power"] == 2600.0
    assert {row["season_number"] for row in payload} == {13, 14, 15}
    assert (
        not pd.DataFrame(payload)
        .assign(weapon_id_key=lambda frame: frame["weapon_id"].astype(str))
        .duplicated(subset=leaderboard_mod.idx_columns + ["weapon_id_key"])
        .any()
    )
