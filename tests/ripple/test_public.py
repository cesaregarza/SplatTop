import time

import orjson

from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def test_public_leaderboard_disabled_returns_404(client_factory, fake_redis):
    with client_factory(env={"COMP_LEADERBOARD_ENABLED": "false"}, redis=fake_redis) as client:
        res = client.get("/api/ripple/public")
        assert res.status_code == 404


def test_public_leaderboard_returns_cached_payload(client_factory, fake_redis):
    generated_at = _now_ms()
    payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {"limit": 200},
        "record_count": 2,
        "total": 2,
        "data": [
            {
                "player_id": "p1",
                "display_name": "Player 1",
                "stable_score": 12.3,
                "display_score": 307.5,
                "stable_rank": 1,
                "tournament_count": 10,
                "last_active_ms": generated_at,
                "last_tournament_ms": generated_at,
            },
            {
                "player_id": "p2",
                "display_name": "Player 2",
                "stable_score": 11.1,
                "display_score": 277.5,
                "stable_rank": 2,
                "tournament_count": 8,
                "last_active_ms": generated_at,
                "last_tournament_ms": generated_at,
            },
        ],
    }
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(payload))

    with client_factory(env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis) as client:
        res = client.get("/api/ripple/public")
        assert res.status_code == 200
        data = res.json()
        assert data["build_version"] == "2024.09.01"
        assert data["record_count"] == 2
        assert data["data"][0]["player_id"] == "p1"
        assert data["stale"] is False
        assert isinstance(data["retrieved_at_ms"], int)


def test_public_danger_returns_cached_payload(client_factory, fake_redis):
    generated_at = _now_ms()
    payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {"limit": 50},
        "record_count": 1,
        "total": 1,
        "data": [
            {
                "rank": 10,
                "player_id": "p3",
                "display_name": "Player 3",
                "display_score": 250.0,
                "window_tournament_count": 3,
                "oldest_in_window_ms": generated_at - 1000,
                "next_expiry_ms": generated_at + 1000,
                "days_left": 0.5,
            }
        ],
    }
    fake_redis.set(RIPPLE_DANGER_LATEST_KEY, orjson.dumps(payload))

    with client_factory(env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis) as client:
        res = client.get("/api/ripple/public/danger")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["data"][0]["player_id"] == "p3"
        assert data["stale"] is False


def test_public_meta_reports_presence(client_factory, fake_redis):
    generated_at = _now_ms()
    meta_payload = {
        "generated_at_ms": generated_at,
        "stable_calculated_at_ms": generated_at,
        "stable_record_count": 2,
        "danger_calculated_at_ms": generated_at,
        "danger_record_count": 1,
        "build_version": "2024.09.01",
    }
    stable_payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {},
        "record_count": 0,
        "total": 0,
        "data": [],
    }
    danger_payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": generated_at,
        "generated_at_ms": generated_at,
        "query_params": {},
        "record_count": 0,
        "total": 0,
        "data": [],
    }
    fake_redis.set(RIPPLE_STABLE_META_KEY, orjson.dumps(meta_payload))
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(stable_payload))
    fake_redis.set(RIPPLE_DANGER_LATEST_KEY, orjson.dumps(danger_payload))

    with client_factory(env={"COMP_LEADERBOARD_ENABLED": "true"}, redis=fake_redis) as client:
        res = client.get("/api/ripple/public/meta")
        assert res.status_code == 200
        data = res.json()
        assert data["meta"]["build_version"] == "2024.09.01"
        assert data["stable"]["present"] is True
        assert data["danger"]["present"] is True
        assert data["feature_flag"]["enabled"] is True
        assert isinstance(data["retrieved_at_ms"], int)
