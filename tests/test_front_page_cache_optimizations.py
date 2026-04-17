import asyncio
import importlib
import zlib

import orjson

from shared_lib.constants import PLAYER_LATEST_REDIS_KEY


def test_leaderboard_route_returns_precomputed_columnar_payload(
    client, fake_redis, monkeypatch
):
    import fast_api_app.routes.front_page as front_page_mod

    monkeypatch.setattr(front_page_mod, "redis_conn", fake_redis, raising=False)
    fake_redis.set(
        "leaderboard_data:Splat Zones:Tentatek",
        orjson.dumps(
            {
                "players": {
                    "player_id": ["p1"],
                    "splashtag": ["Alpha#1111"],
                    "rank": [1],
                }
            }
        ),
    )

    response = client.get(
        "/api/leaderboard?mode=Splat%20Zones&region=Tentatek"
    )

    assert response.status_code == 200
    assert response.json() == {
        "players": {
            "player_id": ["p1"],
            "splashtag": ["Alpha#1111"],
            "rank": [1],
        }
    }


def test_connection_manager_connect_replays_cached_progressive_payload(
    fake_redis, monkeypatch
):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    conn_mod = importlib.import_module("fast_api_app.connections")
    conn_mod = importlib.reload(conn_mod)

    monkeypatch.setattr(conn_mod, "redis_conn", fake_redis, raising=False)
    send_task_calls = []

    class _SpyCelery:
        def send_task(self, *args, **kwargs):
            send_task_calls.append((args, kwargs))
            return None

    monkeypatch.setattr(conn_mod, "celery", _SpyCelery(), raising=False)

    fake_redis.set(
        f"{PLAYER_LATEST_REDIS_KEY}:p1",
        orjson.dumps(
            {
                "player_data": [{"timestamp": "2026-04-17T00:00:00+00:00"}],
                "aggregated_data": {
                    "weapon_counts": [{"weapon_id": 101, "count": 3}],
                    "weapon_winrate": [{"weapon_id": 101, "win_rate": 0.75}],
                    "season_results": [{"season_number": 10, "rank": 2}],
                    "aggregate_season_data": [
                        {"season_number": 10, "peak_x_power": 4300.1}
                    ],
                    "latest_data": [{"mode": "Rainmaker", "x_power": 4300.1}],
                },
            }
        ),
    )

    class _DummyWebSocket:
        def __init__(self):
            self.accepted = False
            self.messages = []

        async def accept(self):
            self.accepted = True

        async def send_bytes(self, data):
            self.messages.append(data)

    websocket = _DummyWebSocket()
    manager = conn_mod.ConnectionManager()

    asyncio.run(manager.connect(websocket, "p1", "conn-1", progressive=True))

    assert websocket.accepted is True
    assert send_task_calls == []
    assert len(websocket.messages) == 3

    decoded_messages = [
        orjson.loads(zlib.decompress(message))
        for message in websocket.messages
    ]
    assert [message["phase"] for message in decoded_messages] == [
        "snapshot",
        "analysis",
        "complete",
    ]
    assert decoded_messages[0]["payload"]["aggregated_data"] == {
        "season_results": [{"season_number": 10, "rank": 2}],
        "latest_data": [{"mode": "Rainmaker", "x_power": 4300.1}],
    }
    assert decoded_messages[1]["payload"]["player_data"] == [
        {"timestamp": "2026-04-17T00:00:00+00:00"}
    ]
