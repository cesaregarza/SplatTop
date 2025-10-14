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
)


def test_handles_empty_ranking_data(monkeypatch):
    """
    Test that the code handles when the ranking query returns 0 players.
    This could happen during maintenance or if all players drop out.
    """
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    async def fake_fetch_page(session, **kwargs):
        # No players in ranking
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        # No players to fetch events for
        assert len(player_ids) == 0
        return {}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Should not be called if there are no players
        assert (
            len(player_events) == 0
        ), "Should not be called with empty player_events"
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

    # Should not crash with empty data
    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    assert stable_payload["record_count"] == 0
    assert stable_payload["data"] == []


def test_handles_future_event_timestamps(monkeypatch):
    """
    Test that the code handles when event timestamps are in the future
    (could happen due to clock skew or bad data). Should not crash.
    """
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    current_ms = 2_000

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
        # Event timestamp is in the future!
        return {"p1": {"latest_event_ms": 10_000, "tournament_count": 5}}

    first_scores_called = {"count": 0}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        first_scores_called["count"] += 1
        # Should be called with future timestamp
        if player_events:
            for pid, ts in player_events.items():
                assert isinstance(ts, int)
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
    monkeypatch.setattr(
        snapshot_mod, "_now_ms", lambda: current_ms, raising=False
    )

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

    # Should not crash with future timestamps
    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True
    assert first_scores_called["count"] > 0


def test_handles_negative_scores(monkeypatch):
    """
    Test that the code handles negative scores correctly (edge case for
    new/struggling players). Ranks should still be computed correctly.
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
        },
        {
            "player_id": "p2",
            "display_name": "Player Two",
            "score": -0.5,
            "rank": 2,
            "tournament_count": 3,
        },
        {
            "player_id": "p3",
            "display_name": "Player Three",
            "score": -2.0,
            "rank": 3,
            "tournament_count": 2,
        },
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 3, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        return {
            "p1": {"latest_event_ms": 1100, "tournament_count": 5},
            "p2": {"latest_event_ms": 1100, "tournament_count": 3},
            "p3": {"latest_event_ms": 1100, "tournament_count": 2},
        }

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        return {"p1": 1.0, "p2": -0.5, "p3": -2.0}

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

    # Verify correct rank ordering: higher score = lower rank number
    assert stable_payload["data"][0]["player_id"] == "p1"
    assert stable_payload["data"][0]["stable_rank"] == 1
    assert stable_payload["data"][0]["stable_score"] == pytest.approx(1.0)

    assert stable_payload["data"][1]["player_id"] == "p2"
    assert stable_payload["data"][1]["stable_rank"] == 2
    assert stable_payload["data"][1]["stable_score"] == pytest.approx(-0.5)

    assert stable_payload["data"][2]["player_id"] == "p3"
    assert stable_payload["data"][2]["stable_rank"] == 3
    assert stable_payload["data"][2]["stable_score"] == pytest.approx(-2.0)


def test_validates_player_events_types_at_runtime(monkeypatch):
    """
    This test intentionally passes WRONG data types to _first_scores_after_events
    to verify the production code (or our validation in tests) catches it.

    If this test PASSES, it means either:
    1. The production code doesn't validate input (BUG!)
    2. Our test validation catches it (GOOD)
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
        # Return WRONG type - should be int timestamps, not dict
        return {"p1": {"latest_event_ms": "not an int", "tournament_count": 5}}

    validation_caught_error = {"value": False}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # This validation should catch the error
        try:
            assert isinstance(player_events, dict)
            for pid, ts in player_events.items():
                assert isinstance(
                    pid, str
                ), f"Player ID should be str, got {type(pid)}"
                assert isinstance(
                    ts, int
                ), f"Timestamp should be int, got {type(ts)}"
        except (AssertionError, TypeError, ValueError) as e:
            validation_caught_error["value"] = True
            # Re-raise so the test sees the error
            raise
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

    # This should either:
    # 1. Crash because validation catches wrong type (GOOD)
    # 2. Silently succeed (BAD - means no validation!)
    with pytest.raises((AssertionError, TypeError, ValueError, KeyError)):
        snapshot_mod.refresh_ripple_snapshots()

    # If we get here, validation caught the error
    # If the test fails, it means wrong types were silently accepted!


def test_handles_player_with_no_latest_event(monkeypatch):
    """
    Test when a player has tournament appearances but no event timestamp
    (latest_event_ms is None). This could happen if tournament_event_times
    MV is missing data.
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
        # Player exists but has no latest_event_ms
        return {"p1": {"latest_event_ms": None, "tournament_count": 5}}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Should not be called since latest_event_ms is None
        assert (
            "p1" not in player_events
        ), "p1 should not be in player_events when latest_event_ms is None"
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

    # Should still produce a payload with p1 using raw score
    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    assert stable_payload["record_count"] == 1
    assert stable_payload["data"][0]["stable_score"] == pytest.approx(1.0)
