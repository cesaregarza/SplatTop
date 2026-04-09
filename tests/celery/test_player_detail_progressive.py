import importlib
import os
from collections import namedtuple

import orjson

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")

from shared_lib.constants import PLAYER_LATEST_REDIS_KEY, PLAYER_PUBSUB_CHANNEL


class RedisSpy:
    def __init__(self):
        self.kv = {}
        self.published = []
        self.set_calls = []

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, nx=False, ex=None, px=None):
        self.set_calls.append(
            {"key": key, "value": value, "nx": nx, "ex": ex, "px": px}
        )
        if nx and key in self.kv:
            return False
        self.kv[key] = value
        return True

    def exists(self, key):
        return key in self.kv

    def publish(self, channel, message):
        self.published.append((channel, message))
        return 1

    def delete(self, key):
        self.kv.pop(key, None)
        return 1


def _decode_published_phases(redis_spy):
    return [
        orjson.loads(message)["phase"]
        for channel, message in redis_spy.published
        if channel == PLAYER_PUBSUB_CHANNEL
    ]


def test_fetch_player_data_publishes_snapshot_then_analysis_then_complete(
    monkeypatch,
):
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)
    redis_spy = RedisSpy()
    monkeypatch.setattr(mod, "redis_conn", redis_spy, raising=False)
    monkeypatch.setattr(
        mod,
        "_fetch_season_data",
        lambda player_id: [
            {
                "season_number": 6,
                "mode": "Rainmaker",
                "rank": 4,
                "x_power": 2801.1,
            }
        ],
    )
    monkeypatch.setattr(
        mod,
        "pull_all_latest_data",
        lambda player_id: [
            {
                "season_number": 5,
                "mode": "Rainmaker",
                "rank": 5,
                "x_power": 2798.4,
            }
        ],
    )
    monkeypatch.setattr(
        mod,
        "_fetch_player_data",
        lambda player_id: [
            {
                "season_number": 5,
                "mode": "Rainmaker",
                "timestamp": "2024-12-05T00:00:00.000Z",
                "updated": True,
                "weapon_id": 42,
                "rank": 4,
                "x_power": 2801.1,
            }
        ],
    )

    mod.fetch_player_data("player-1")

    assert _decode_published_phases(redis_spy) == [
        "snapshot",
        "analysis",
        "complete",
    ]

    snapshot_message = orjson.loads(redis_spy.published[0][1])
    assert snapshot_message["payload"]["aggregated_data"] == {
        "season_results": [
            {
                "season_number": 6,
                "mode": "Rainmaker",
                "rank": 4,
                "x_power": 2801.1,
            }
        ],
        "latest_data": [
            {
                "season_number": 5,
                "mode": "Rainmaker",
                "rank": 5,
                "x_power": 2798.4,
            }
        ],
    }

    analysis_message = orjson.loads(redis_spy.published[1][1])
    assert analysis_message["payload"]["player_data"] == [
        {
            "season_number": 5,
            "mode": "Rainmaker",
            "timestamp": "2024-12-05T00:00:00.000Z",
            "updated": True,
            "weapon_id": 42,
            "rank": 4,
            "x_power": 2801.1,
        }
    ]
    assert analysis_message["payload"]["aggregated_data"][
        "aggregate_season_data"
    ] == [{"season_number": 5, "mode": "Rainmaker", "peak_x_power": 2801.1}]

    cache_key = f"{PLAYER_LATEST_REDIS_KEY}:player-1"
    cached_payload = orjson.loads(redis_spy.get(cache_key))
    assert cached_payload["aggregated_data"]["season_results"][0]["rank"] == 4
    assert cached_payload["player_data"][0]["weapon_id"] == 42
    assert redis_spy.set_calls[-1] == {
        "key": cache_key,
        "value": redis_spy.get(cache_key),
        "nx": False,
        "ex": mod.PLAYER_CACHE_TTL_SECONDS,
        "px": None,
    }


def test_fetch_player_data_replays_cached_chunks_without_refetching(
    monkeypatch,
):
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)
    redis_spy = RedisSpy()
    cache_key = f"{PLAYER_LATEST_REDIS_KEY}:player-2"
    redis_spy.set(
        cache_key,
        orjson.dumps(
            {
                "player_data": [{"mode": "Rainmaker", "season_number": 5}],
                "aggregated_data": {
                    "season_results": [
                        {"season_number": 6, "mode": "Rainmaker", "rank": 2}
                    ],
                    "latest_data": [],
                    "aggregate_season_data": [],
                    "weapon_counts": [],
                    "weapon_winrate": [],
                },
            }
        ),
    )
    monkeypatch.setattr(mod, "redis_conn", redis_spy, raising=False)
    monkeypatch.setattr(
        mod,
        "_fetch_season_data",
        lambda player_id: (_ for _ in ()).throw(AssertionError("no refetch")),
    )
    monkeypatch.setattr(
        mod,
        "_fetch_player_data",
        lambda player_id: (_ for _ in ()).throw(AssertionError("no refetch")),
    )

    mod.fetch_player_data("player-2")

    assert _decode_published_phases(redis_spy) == [
        "snapshot",
        "analysis",
        "complete",
    ]


def test_fetch_player_data_preserves_snapshot_when_analysis_fails(
    monkeypatch,
):
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)
    redis_spy = RedisSpy()
    monkeypatch.setattr(mod, "redis_conn", redis_spy, raising=False)
    monkeypatch.setattr(
        mod,
        "_fetch_season_data",
        lambda player_id: [
            {"season_number": 6, "mode": "Rainmaker", "rank": 7}
        ],
    )
    monkeypatch.setattr(mod, "pull_all_latest_data", lambda player_id: [])
    monkeypatch.setattr(
        mod,
        "_fetch_player_data",
        lambda player_id: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    mod.fetch_player_data("player-3")

    assert _decode_published_phases(redis_spy) == [
        "snapshot",
        "error",
        "complete",
    ]

    error_message = orjson.loads(redis_spy.published[1][1])
    assert error_message["payload"] == {"message": "boom", "stage": "analysis"}

    cache_key = f"{PLAYER_LATEST_REDIS_KEY}:player-3"
    cached_payload = orjson.loads(redis_spy.get(cache_key))
    assert cached_payload["aggregated_data"]["season_results"] == [
        {"season_number": 6, "mode": "Rainmaker", "rank": 7}
    ]
    assert cached_payload["player_data"] == []


def test_fetch_player_data_uses_atomic_lock_and_skips_when_already_running(
    monkeypatch,
):
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)
    redis_spy = RedisSpy()
    redis_spy.set("fetch_player_data:player-4", "true")
    monkeypatch.setattr(mod, "redis_conn", redis_spy, raising=False)
    monkeypatch.setattr(
        mod,
        "_fetch_season_data",
        lambda player_id: (_ for _ in ()).throw(AssertionError("no refetch")),
    )

    mod.fetch_player_data("player-4")

    assert redis_spy.published == []
    assert redis_spy.set_calls[-1] == {
        "key": "fetch_player_data:player-4",
        "value": "true",
        "nx": True,
        "ex": mod.PLAYER_FETCH_LOCK_TTL_SECONDS,
        "px": None,
    }


def test_fetch_player_data_releases_lock_when_snapshot_fetch_fails(
    monkeypatch,
):
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)
    redis_spy = RedisSpy()
    monkeypatch.setattr(mod, "redis_conn", redis_spy, raising=False)
    monkeypatch.setattr(
        mod,
        "_fetch_season_data",
        lambda player_id: (_ for _ in ()).throw(RuntimeError("snapshot boom")),
    )

    import pytest

    with pytest.raises(RuntimeError, match="snapshot boom"):
        mod.fetch_player_data("player-5")

    assert redis_spy.get("fetch_player_data:player-5") is None


def test_aggregate_player_analysis_uses_minimal_rows_without_pandas():
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)

    payload = mod.aggregate_player_analysis(
        [
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-01T00:00:00+00:00",
                "x_power": 2700.0,
                "weapon_id": 10,
                "rank": 30,
                "updated": True,
            },
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-02T00:00:00+00:00",
                "x_power": 2715.5,
                "weapon_id": 10,
                "rank": 24,
                "updated": True,
            },
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-03T00:00:00+00:00",
                "x_power": 2680.5,
                "weapon_id": 12,
                "rank": 28,
                "updated": True,
            },
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-04T00:00:00+00:00",
                "x_power": 2725.0,
                "weapon_id": 12,
                "rank": 20,
                "updated": False,
            },
        ]
    )

    assert payload["weapon_counts"] == [
        {
            "mode": "Rainmaker",
            "weapon_id": 10,
            "season_number": 5,
            "count": 2,
        },
        {
            "mode": "Rainmaker",
            "weapon_id": 12,
            "season_number": 5,
            "count": 1,
        },
    ]
    assert payload["weapon_winrate"] == [
        {
            "mode": "Rainmaker",
            "weapon_id": 10,
            "season_number": 5,
            "sum": 1,
            "total_count": 1,
        },
        {
            "mode": "Rainmaker",
            "weapon_id": 12,
            "season_number": 5,
            "sum": 0,
            "total_count": 1,
        },
    ]
    assert payload["aggregate_season_data"] == [
        {
            "season_number": 5,
            "mode": "Rainmaker",
            "peak_x_power": 2725.0,
        }
    ]


def test_reduce_player_history_rows_keeps_changes_updates_and_endpoints():
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)

    reduced = mod.reduce_player_history_rows(
        [
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-01T00:00:00+00:00",
                "x_power": 2700.0,
                "weapon_id": 10,
                "rank": 30,
                "updated": False,
            },
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-02T00:00:00+00:00",
                "x_power": 2700.0,
                "weapon_id": 10,
                "rank": 30,
                "updated": False,
            },
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-03T00:00:00+00:00",
                "x_power": 2715.5,
                "weapon_id": 10,
                "rank": 24,
                "updated": False,
            },
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-04T00:00:00+00:00",
                "x_power": 2715.5,
                "weapon_id": 12,
                "rank": 24,
                "updated": True,
            },
            {
                "mode": "Rainmaker",
                "season_number": 5,
                "timestamp": "2024-12-05T00:00:00+00:00",
                "x_power": 2715.5,
                "weapon_id": 12,
                "rank": 24,
                "updated": False,
            },
            {
                "mode": "Splat Zones",
                "season_number": 5,
                "timestamp": "2024-12-06T00:00:00+00:00",
                "x_power": 2601.0,
                "weapon_id": 20,
                "rank": 50,
                "updated": False,
            },
            {
                "mode": "Splat Zones",
                "season_number": 5,
                "timestamp": "2024-12-07T00:00:00+00:00",
                "x_power": 2601.0,
                "weapon_id": 20,
                "rank": 50,
                "updated": False,
            },
        ]
    )

    assert [row["timestamp"] for row in reduced] == [
        "2024-12-01T00:00:00+00:00",
        "2024-12-02T00:00:00+00:00",
        "2024-12-03T00:00:00+00:00",
        "2024-12-04T00:00:00+00:00",
        "2024-12-05T00:00:00+00:00",
        "2024-12-06T00:00:00+00:00",
        "2024-12-07T00:00:00+00:00",
    ]


def test_pull_all_latest_data_queries_player_latest_rows(monkeypatch):
    mod = importlib.import_module("celery_app.tasks.player_detail")
    mod = importlib.reload(mod)
    captured = {}
    latest_row = namedtuple(
        "LatestRow",
        [
            "mode",
            "region",
            "season_number",
            "rank",
            "x_power",
            "weapon_id",
        ],
    )

    class FakeResult:
        def fetchall(self):
            return [
                latest_row(
                    "Rainmaker",
                    False,
                    5,
                    4,
                    2801.1,
                    42,
                )
            ]

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            captured["sql"] = str(query)
            captured["params"] = params
            return FakeResult()

    monkeypatch.setattr(mod, "Session", FakeSession)

    assert mod.pull_all_latest_data("player-6") == [
        {
            "mode": "Rainmaker",
            "region": False,
            "season_number": 5,
            "rank": 4,
            "x_power": 2801.1,
            "weapon_id": 42,
        }
    ]
    assert "xscraper.player_latest" in captured["sql"]
    assert captured["params"] == {"player_id": "player-6"}
