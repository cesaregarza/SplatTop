import importlib
import os

import orjson
import pandas as pd

from shared_lib.constants import RACE_TO_5000_REDIS_KEY

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")


def test_build_race_to_5000_payload_groups_and_sorts_runs():
    mod = importlib.import_module("celery_app.tasks.front_page")
    mod = importlib.reload(mod)

    current_df = pd.DataFrame(
        [
            {
                "player_id": "p1",
                "splashtag": "Alpha#1111",
                "rank": 2,
                "x_power": 4201.2,
                "timestamp": pd.Timestamp("2026-04-01T00:00:00Z"),
                "mode": "Rainmaker",
                "region": False,
                "season_number": 10,
            },
            {
                "player_id": "p1",
                "splashtag": "Alpha#1111",
                "rank": 1,
                "x_power": 4305.5,
                "timestamp": pd.Timestamp("2026-04-05T00:00:00Z"),
                "mode": "Rainmaker",
                "region": False,
                "season_number": 10,
            },
            {
                "player_id": "p2",
                "splashtag": "Beta#2222",
                "rank": 8,
                "x_power": 4102.4,
                "timestamp": pd.Timestamp("2026-04-04T00:00:00Z"),
                "mode": "Tower Control",
                "region": True,
                "season_number": 10,
            },
            {
                "player_id": "p3",
                "splashtag": "Gamma#3333",
                "rank": 5,
                "x_power": 4205.0,
                "timestamp": pd.Timestamp("2026-04-02T00:00:00Z"),
                "mode": "Splat Zones",
                "region": False,
                "season_number": 10,
            },
            {
                "player_id": "p3",
                "splashtag": "Gamma#3333",
                "rank": 12,
                "x_power": 3998.7,
                "timestamp": pd.Timestamp("2026-04-06T00:00:00Z"),
                "mode": "Splat Zones",
                "region": False,
                "season_number": 10,
            },
        ]
    )
    historical_df = pd.DataFrame(
        [
            {
                "player_id": "p3",
                "splashtag": "Gamma#3333",
                "rank": 1,
                "x_power": 5012.8,
                "timestamp": pd.Timestamp("2025-01-02T00:00:00Z"),
                "mode": "Splat Zones",
                "region": True,
                "season_number": 9,
            },
            {
                "player_id": "p3",
                "splashtag": "Gamma#3333",
                "rank": 1,
                "x_power": 5110.1,
                "timestamp": pd.Timestamp("2025-02-02T00:00:00Z"),
                "mode": "Splat Zones",
                "region": True,
                "season_number": 9,
            },
        ]
    )

    payload = mod.build_race_to_5000_payload(current_df, historical_df)

    assert payload["current_season"] == 10
    assert payload["current_threshold"] == 4000
    assert payload["historical_threshold"] == 5000
    assert [run["player_id"] for run in payload["current_runs"]] == ["p1", "p2"]
    assert payload["current_runs"][0]["peak_x_power"] == 4305.5
    assert payload["current_runs"][0]["current_x_power"] == 4305.5
    assert payload["current_runs"][0]["region"] == "Tentatek"
    assert len(payload["current_runs"][0]["points"]) == 2
    assert payload["historical_runs"][0]["peak_x_power"] == 5110.1
    assert payload["updated_at"] == "2026-04-05T00:00:00+00:00"


def test_race_to_5000_route_returns_cached_payload(client, fake_redis, monkeypatch):
    import fast_api_app.routes.front_page as front_page_mod

    monkeypatch.setattr(front_page_mod, "redis_conn", fake_redis, raising=False)
    fake_redis.set(
        RACE_TO_5000_REDIS_KEY,
        orjson.dumps(
            {
                "current_season": 10,
                "current_threshold": 4000,
                "historical_threshold": 5000,
                "current_runs": [],
                "historical_runs": [],
                "updated_at": None,
            }
        ),
    )

    response = client.get("/api/race-to-5000")

    assert response.status_code == 200
    assert response.json()["current_season"] == 10


def test_fetch_race_to_5000_stores_empty_payload_when_current_season_missing(
    fake_redis, monkeypatch
):
    mod = importlib.import_module("celery_app.tasks.front_page")
    mod = importlib.reload(mod)

    duration_calls = []
    row_calls = []

    class _MetricSpy:
        def labels(self, **kwargs):
            self._labels = kwargs
            return self

        def observe(self, value):
            duration_calls.append(value)

        def set(self, value):
            row_calls.append(value)

    monkeypatch.setattr(mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(mod, "fetch_current_season", lambda session: None)
    monkeypatch.setattr(mod, "metrics_enabled", lambda: True)
    monkeypatch.setattr(mod, "DATA_PULL_DURATION", _MetricSpy(), raising=False)
    monkeypatch.setattr(mod, "DATA_PULL_ROWS", _MetricSpy(), raising=False)
    monkeypatch.setattr(
        mod,
        "fetch_race_to_5000_rows",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not fetch rows")
        ),
    )

    mod.fetch_race_to_5000()

    payload = orjson.loads(fake_redis.get(RACE_TO_5000_REDIS_KEY))
    assert payload == {
        "current_season": None,
        "current_threshold": 4000,
        "historical_threshold": 5000,
        "current_runs": [],
        "historical_runs": [],
        "updated_at": None,
    }
    assert len(duration_calls) == 1
    assert row_calls == [0, 0]
