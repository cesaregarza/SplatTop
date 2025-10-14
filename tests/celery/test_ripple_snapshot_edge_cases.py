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
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_STATE_KEY,
)


def test_handles_missing_player_events(monkeypatch):
    """
    Test that the code doesn't crash when _fetch_player_events returns
    empty data for some players. This could happen if:
    - Player has no tournament appearances in the database
    - Database query fails partially
    - Player was deleted but still in rankings
    """
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.0,
            "rank": 1,
            "tournament_count": 5,
            "window_count": 3,
            "last_active_ms": 1000,
        },
        {
            "player_id": "p2",
            "display_name": "Player Two",
            "score": 0.9,
            "rank": 2,
            "tournament_count": 4,
            "window_count": 3,
            "last_active_ms": 900,
        },
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 2, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        # p2 has NO event data - returns empty dict for that player
        return {
            "p1": {"latest_event_ms": 1100, "tournament_count": 6},
            # p2 is missing!
        }

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        assert isinstance(player_events, dict)
        # Should only be called with p1 since p2 has no events
        assert (
            "p2" not in player_events
        ), "p2 should not be in player_events since it has no event data"
        return {"p1": 1.0}

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
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 2_000, raising=False)

    class FakeScoped:
        def __call__(self):
            @asynccontextmanager
            async def fake_session():
                class FakeResult:
                    def __init__(self, value):
                        self._value = value

                    def scalar(self):
                        return self._value

                class FakeSession:
                    async def execute(self, _query, params=None):
                        return FakeResult(None)

                    @asynccontextmanager
                    async def begin(self):
                        yield

                yield FakeSession()

            return fake_session()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    # Should not crash even though p2 has no event data
    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True

    # Both players should still be in the payload
    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    player_ids = {row["player_id"] for row in stable_payload["data"]}
    assert player_ids == {"p1", "p2"}

    # p2 should use raw score from rankings since no event override
    p2_data = next(r for r in stable_payload["data"] if r["player_id"] == "p2")
    assert p2_data["stable_score"] == pytest.approx(0.9)


def test_handles_missing_score_override(monkeypatch):
    """
    Test that the code handles when _first_scores_after_events doesn't
    return a score for a player (empty result). Should fall back to
    the raw ranking score.
    """
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.0,
            "rank": 1,
            "tournament_count": 5,
        }
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 1, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        return {"p1": {"latest_event_ms": 1100, "tournament_count": 6}}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Return empty dict - no scores found
        return {}

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
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 2_000, raising=False)

    class FakeScoped:
        def __call__(self):
            @asynccontextmanager
            async def fake_session():
                class FakeResult:
                    def __init__(self, value):
                        self._value = value

                    def scalar(self):
                        return self._value

                class FakeSession:
                    async def execute(self, _query, params=None):
                        return FakeResult(None)

                    @asynccontextmanager
                    async def begin(self):
                        yield

                yield FakeSession()

            return fake_session()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    # Should fall back to raw score (1.0)
    assert stable_payload["data"][0]["stable_score"] == pytest.approx(1.0)


def test_handles_identical_scores(monkeypatch):
    """
    Test that when multiple players have identical scores, ranks are
    assigned consistently (should use player_id as tiebreaker).
    """
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p3",
            "display_name": "Player Three",
            "score": 1.0,
            "rank": 1,
            "tournament_count": 5,
        },
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.0,
            "rank": 2,
            "tournament_count": 5,
        },
        {
            "player_id": "p2",
            "display_name": "Player Two",
            "score": 1.0,
            "rank": 3,
            "tournament_count": 5,
        },
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 3, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        return {
            "p1": {"latest_event_ms": 1100, "tournament_count": 5},
            "p2": {"latest_event_ms": 1100, "tournament_count": 5},
            "p3": {"latest_event_ms": 1100, "tournament_count": 5},
        }

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # All get same score
        return {pid: 1.0 for pid in player_events}

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
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 2_000, raising=False)

    class FakeScoped:
        def __call__(self):
            @asynccontextmanager
            async def fake_session():
                class FakeResult:
                    def __init__(self, value):
                        self._value = value

                    def scalar(self):
                        return self._value

                class FakeSession:
                    async def execute(self, _query, params=None):
                        return FakeResult(None)

                    @asynccontextmanager
                    async def begin(self):
                        yield

                yield FakeSession()

            return fake_session()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))

    # Verify all have same score
    for row in stable_payload["data"]:
        assert row["stable_score"] == pytest.approx(1.0)

    # Verify ranks are 1, 2, 3 and ordered by player_id (p1, p2, p3)
    ranks = [
        (row["player_id"], row["stable_rank"]) for row in stable_payload["data"]
    ]
    assert ranks == [("p1", 1), ("p2", 2), ("p3", 3)]


def test_handles_null_tournament_count(monkeypatch):
    """
    Test that the code handles when tournament_count is None/null in the data.
    """
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.0,
            "rank": 1,
            "tournament_count": None,  # NULL in database
            "window_count": None,
        }
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 1, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        return {"p1": {"latest_event_ms": 1100, "tournament_count": None}}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        return {"p1": 1.0}

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
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 2_000, raising=False)

    class FakeScoped:
        def __call__(self):
            @asynccontextmanager
            async def fake_session():
                class FakeResult:
                    def __init__(self, value):
                        self._value = value

                    def scalar(self):
                        return self._value

                class FakeSession:
                    async def execute(self, _query, params=None):
                        return FakeResult(None)

                    @asynccontextmanager
                    async def begin(self):
                        yield

                yield FakeSession()

            return fake_session()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    # Should not crash with None values
    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    # Should handle None gracefully (likely converted to None or 0)
    assert stable_payload["record_count"] == 1


def test_handles_corrupt_redis_state(monkeypatch):
    """
    Test that the code handles when Redis has corrupt/invalid JSON data.
    Should bootstrap from scratch rather than crash.
    """
    fake_redis = FakeRedis()
    # Put corrupt data in Redis
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, b"not valid json{{{")
    fake_redis.set(RIPPLE_STABLE_STATE_KEY, b"also corrupt")

    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 1.0,
            "rank": 1,
            "tournament_count": 5,
        }
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 1, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        return {"p1": {"latest_event_ms": 1100, "tournament_count": 5}}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        return {"p1": 1.0}

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
    monkeypatch.setattr(snapshot_mod, "_now_ms", lambda: 2_000, raising=False)

    class FakeScoped:
        def __call__(self):
            @asynccontextmanager
            async def fake_session():
                class FakeResult:
                    def __init__(self, value):
                        self._value = value

                    def scalar(self):
                        return self._value

                class FakeSession:
                    async def execute(self, _query, params=None):
                        return FakeResult(None)

                    @asynccontextmanager
                    async def begin(self):
                        yield

                yield FakeSession()

            return fake_session()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    # Should not crash even with corrupt Redis data - should bootstrap from scratch
    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True

    # Should have written valid data
    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    assert stable_payload["record_count"] == 1

    # Delta should have no baseline since previous was corrupt
    from shared_lib.constants import RIPPLE_STABLE_DELTAS_KEY

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    assert delta_payload["baseline_generated_at_ms"] is None
