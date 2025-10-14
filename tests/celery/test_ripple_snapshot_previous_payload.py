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
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_PREVIOUS_KEY,
    RIPPLE_STABLE_PREVIOUS_META_KEY,
)


def test_refresh_ripple_snapshots_preserves_previous_payload(monkeypatch):
    fake_redis = FakeRedis()
    previous_payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": 1_000,
        "generated_at_ms": 1_100,
        "query_params": {},
        "record_count": 1,
        "total": 1,
        "data": [
            {
                "player_id": "p1",
                "display_name": "Player One",
                "stable_score": 1.0,
                "display_score": 175.0,
                "stable_rank": 1,
            }
        ],
    }
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(previous_payload))
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.2,
            "rank": 1,
            "tournament_count": 6,
            "window_count": 5,
            "last_active_ms": 2_000,
        }
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 1, 2_000, "2024.09.02"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 2_000, "2024.09.02"

    async def fake_fetch_events(session, player_ids):
        return {
            "p1": {"latest_event_ms": 1_900, "tournament_count": 6},
        }

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
        return {"p1": 1.2}

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
    monkeypatch.setattr(
        snapshot_mod,
        "_first_scores_after_events",
        fake_first_scores,
        raising=False,
    )
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 3_000, raising=False)

    class FakeSession:
        async def execute(self, _query, params=None):
            class FakeResult:
                def __init__(self, value):
                    self._value = value

                def scalar(self):
                    return self._value

                def mappings(self):
                    return iter(())

            return FakeResult(None)

        @asynccontextmanager
        async def begin(self):
            yield

    @asynccontextmanager
    async def fake_session_context():
        yield FakeSession()

    class FakeScoped:
        def __call__(self):
            return fake_session_context()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    snapshot_mod.refresh_ripple_snapshots()

    preserved_raw = fake_redis.get(RIPPLE_STABLE_PREVIOUS_KEY)
    assert preserved_raw is not None
    preserved_payload = orjson.loads(preserved_raw)
    assert preserved_payload["data"][0]["stable_score"] == pytest.approx(1.0)

    meta_raw = fake_redis.get(RIPPLE_STABLE_PREVIOUS_META_KEY)
    assert meta_raw is not None
    meta = orjson.loads(meta_raw)
    assert meta["source"] == "redis_latest"
    assert meta["payload_generated_at_ms"] == 1_100


def test_refresh_ripple_snapshots_uses_preserved_payload_when_latest_missing(
    monkeypatch,
):
    fake_redis = FakeRedis()
    previous_payload = {
        "build_version": "2024.09.01",
        "calculated_at_ms": 1_000,
        "generated_at_ms": 1_050,
        "query_params": {},
        "record_count": 1,
        "total": 1,
        "data": [
            {
                "player_id": "p1",
                "display_name": "Player One",
                "stable_score": 0.95,
                "display_score": 173.75,
                "stable_rank": 1,
            }
        ],
    }
    fake_redis.set(RIPPLE_STABLE_PREVIOUS_KEY, orjson.dumps(previous_payload))
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    current_rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.05,
            "rank": 1,
            "tournament_count": 6,
            "window_count": 4,
            "last_active_ms": 2_500,
        }
    ]

    async def fake_fetch_page(session, **kwargs):
        return current_rows, 1, 2_500, "2024.09.02"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 2_500, "2024.09.02"

    async def fake_fetch_events(session, player_ids):
        return {
            "p1": {"latest_event_ms": 2_400, "tournament_count": 6},
        }

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
        return {"p1": 1.05}

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
    monkeypatch.setattr(
        snapshot_mod,
        "_first_scores_after_events",
        fake_first_scores,
        raising=False,
    )
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 3_000, raising=False)

    class FakeSession:
        async def execute(self, _query, params=None):
            class FakeResult:
                def __init__(self, value):
                    self._value = value

                def scalar(self):
                    return self._value

                def mappings(self):
                    return iter(())

            return FakeResult(None)

        @asynccontextmanager
        async def begin(self):
            yield

    @asynccontextmanager
    async def fake_session_context():
        yield FakeSession()

    class FakeScoped:
        def __call__(self):
            return fake_session_context()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    snapshot_mod.refresh_ripple_snapshots()

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    player_delta = delta_payload["players"]["p1"]
    assert player_delta["previous_score"] == pytest.approx(0.95)

    meta = orjson.loads(fake_redis.get(RIPPLE_STABLE_PREVIOUS_META_KEY))
    assert meta["source"] == "redis_previous"


def test_refresh_ripple_snapshots_backfills_previous_payload(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    current_rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.1,
            "rank": 1,
            "tournament_count": 6,
            "window_count": 5,
            "last_active_ms": 1_800,
        },
        {
            "player_id": "p2",
            "display_name": "Player Two",
            "score": 0.9,
            "rank": 2,
            "tournament_count": 4,
            "window_count": 3,
            "last_active_ms": 1_700,
        },
    ]

    previous_rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.0,
            "rank": 1,
            "tournament_count": 6,
            "window_count": 4,
            "last_active_ms": 1_200,
        },
        {
            "player_id": "p2",
            "display_name": "Player Two",
            "score": 0.95,
            "rank": 2,
            "tournament_count": 5,
            "window_count": 4,
            "last_active_ms": 1_150,
        },
    ]

    fetch_calls: list[int | None] = []

    async def fake_fetch_page(session, **kwargs):
        ts = kwargs.get("ts_ms")
        fetch_calls.append(ts)
        if ts is None:
            return current_rows, 2, 3_000, "2024.09.03"
        assert ts == 2_000
        return previous_rows, 2, 2_000, "2024.09.02"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 3_000, "2024.09.03"

    async def fake_fetch_events(session, player_ids):
        return {
            "p1": {"latest_event_ms": 1_950, "tournament_count": 6},
            "p2": {"latest_event_ms": 1_940, "tournament_count": 5},
        }

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
        if cutoff_ms is not None:
            return {
                player_id: 0.96 if player_id == "p1" else 0.88
                for player_id in player_events
            }
        return {"p1": 1.1, "p2": 0.9}

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
    monkeypatch.setattr(
        snapshot_mod,
        "_first_scores_after_events",
        fake_first_scores,
        raising=False,
    )
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 4_000, raising=False)

    class FakeSession:
        async def execute(self, _query, params=None):
            class FakeResult:
                def __init__(self, value):
                    self._value = value

                def scalar(self):
                    return self._value

            return FakeResult(2_000)

        @asynccontextmanager
        async def begin(self):
            yield

    @asynccontextmanager
    async def fake_session_context():
        yield FakeSession()

    class FakeScoped:
        def __call__(self):
            return fake_session_context()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    snapshot_mod.refresh_ripple_snapshots()

    assert fetch_calls == [None, 2_000]

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    assert delta_payload["baseline_generated_at_ms"] == 2_000
    players = delta_payload["players"]
    assert players["p1"]["score_delta"] == pytest.approx(0.14)
    assert players["p1"]["previous_score"] == pytest.approx(0.96)
    assert players["p2"]["score_delta"] == pytest.approx(0.02)
    assert players["p2"]["previous_score"] == pytest.approx(0.88)
