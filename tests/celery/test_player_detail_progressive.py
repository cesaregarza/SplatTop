import importlib
import os

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

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, nx=False, ex=None, px=None):
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
                "rotation_start": "2024-12-05T00:00:00.000Z",
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
            "rotation_start": "2024-12-05T00:00:00.000Z",
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
