from __future__ import annotations

import os
from contextlib import asynccontextmanager

import orjson
import pytest

# Ensure DB env vars exist before importing modules that build SQLAlchemy engines
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")

from conftest import FakeRedis

from celery_app.tasks import ripple_snapshot as snapshot_mod
from shared_lib.constants import (
    RIPPLE_DANGER_LATEST_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_STATE_KEY,
)


def test_refresh_ripple_snapshots_persists_payloads(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.2,
            "rank": 1,
            "tournament_count": 5,
            "last_active_ms": 1000,
        },
        {
            "player_id": "p2",
            "display_name": "Player Two",
            "score": 0.9,
            "rank": 2,
            "tournament_count": 4,
            "last_active_ms": 900,
        },
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 2, 1234, "2024.09.01"

    danger_rows = [
        {
            "player_rank": 1,
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.2,
            "window_count": 3,
            "oldest_in_window_ms": 800,
            "next_expiry_ms": 1800,
            "ms_left": 1000,
        }
    ]

    async def fake_fetch_danger(session, **kwargs):
        return danger_rows, 1, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        return {
            "p1": {"latest_event_ms": 1100, "tournament_count": 6},
            "p2": {"latest_event_ms": 800, "tournament_count": 4},
        }

    current_ms = 2_000

    monkeypatch.setattr(
        snapshot_mod.ripple_queries,
        "fetch_ripple_page",
        fake_fetch_page,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod.ripple_queries,
        "fetch_ripple_danger",
        fake_fetch_danger,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod,
        "_fetch_player_events",
        fake_fetch_events,
        raising=False,
    )

    async def fake_first_score(session, player_id, event_ms):
        return {"p1": 1.2, "p2": 0.9}.get(player_id, 0.0)

    monkeypatch.setattr(
        snapshot_mod,
        "_first_score_after_event",
        fake_first_score,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod, "_now_ms", lambda: current_ms, raising=False
    )

    @asynccontextmanager
    async def fake_session():
        yield object()

    class FakeScoped:
        def __call__(self):
            return fake_session()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    snapshot_mod.refresh_ripple_snapshots()

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    assert stable_payload["record_count"] == 2
    assert stable_payload["data"][0]["player_id"] == "p1"
    assert stable_payload["data"][0]["stable_score"] == pytest.approx(1.2)
    assert stable_payload["data"][0]["stable_rank"] == 1
    assert stable_payload["data"][1]["player_id"] == "p2"

    danger_payload = orjson.loads(fake_redis.get(RIPPLE_DANGER_LATEST_KEY))
    assert danger_payload["record_count"] == 1
    assert danger_payload["data"][0]["player_id"] == "p1"
    assert danger_payload["data"][0]["days_left"] == pytest.approx(
        1000 / 86_400_000
    )

    meta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_META_KEY))
    assert meta_payload["stable_record_count"] == 2
    assert meta_payload["danger_record_count"] == 1

    state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    assert set(state.keys()) == {"p1", "p2"}
    assert state["p1"]["stable_score"] == pytest.approx(1.2)
    assert state["p1"]["tournament_count"] == 6


def test_existing_state_preserves_stable_score(monkeypatch):
    fake_redis = FakeRedis()
    # Prepopulate state with old tournament timestamp
    state_payload = {
        "p1": {
            "stable_score": 0.5,
            "last_tournament_ms": 500,
            "last_active_ms": 700,
            "tournament_count": 3,
            "updated_at_ms": 0,
        }
    }
    fake_redis.set(RIPPLE_STABLE_STATE_KEY, orjson.dumps(state_payload))
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 0.9,
            "rank": 1,
            "tournament_count": 4,
            "last_active_ms": 900,
        }
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 1, 2000, "2024.09.02"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 2000, "2024.09.02"

    async def fake_fetch_events(session, player_ids):
        return {"p1": {"latest_event_ms": 400, "tournament_count": 4}}

    monkeypatch.setattr(
        snapshot_mod.ripple_queries,
        "fetch_ripple_page",
        fake_fetch_page,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod.ripple_queries,
        "fetch_ripple_danger",
        fake_fetch_danger,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod,
        "_fetch_player_events",
        fake_fetch_events,
        raising=False,
    )

    async def fake_first_score(session, player_id, event_ms):
        return 0.9

    monkeypatch.setattr(
        snapshot_mod,
        "_first_score_after_event",
        fake_first_score,
        raising=False,
    )
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 4_000, raising=False)

    @asynccontextmanager
    async def fake_session():
        yield object()

    class FakeScoped:
        def __call__(self):
            return fake_session()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    snapshot_mod.refresh_ripple_snapshots()

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    item = stable_payload["data"][0]
    # Since latest_event_ms (400) <= stored last_tournament_ms (500), stable score stays 0.5
    assert item["stable_score"] == pytest.approx(0.5)
    assert item["last_tournament_ms"] == 500

    state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    assert state["p1"]["stable_score"] == pytest.approx(0.5)
    assert state["p1"]["updated_at_ms"] == 4_000
