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
    RIPPLE_SNAPSHOT_LOCK_KEY,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_STATE_KEY,
)


def test_refresh_ripple_snapshots_multiple_beat_runs(monkeypatch):
    """
    Simulates what happens when Celery Beat calls the task multiple times
    with gradually evolving data. Tests that:
    - Lock is properly released after each run
    - Previous payload is preserved and used for delta computation
    - State evolves correctly across runs
    - Deltas are computed against the previous run's data
    """
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    # Simulate 4 successive Beat runs with evolving player scores
    run_configs = [
        {
            "rows": [
                {
                    "player_id": "p1",
                    "display_name": "Player One",
                    "score": 1.0,
                    "rank": 1,
                    "tournament_count": 5,
                    "window_count": 3,
                },
                {
                    "player_id": "p2",
                    "display_name": "Player Two",
                    "score": 0.9,
                    "rank": 2,
                    "tournament_count": 4,
                    "window_count": 3,
                },
            ],
            "calc_ts": 1_000,
            "now_ms": 1_500,
            "events": {
                "p1": {"latest_event_ms": 800, "tournament_count": 5},
                "p2": {"latest_event_ms": 750, "tournament_count": 4},
            },
            "scores": {"p1": 1.0, "p2": 0.9},
            "expected_deltas": None,  # First run has no baseline
        },
        {
            "rows": [
                {
                    "player_id": "p1",
                    "display_name": "Player One",
                    "score": 1.1,
                    "rank": 1,
                    "tournament_count": 6,
                    "window_count": 4,
                },
                {
                    "player_id": "p2",
                    "display_name": "Player Two",
                    "score": 0.95,
                    "rank": 2,
                    "tournament_count": 5,
                    "window_count": 4,
                },
            ],
            "calc_ts": 2_000,
            "now_ms": 2_500,
            "events": {
                "p1": {"latest_event_ms": 1_800, "tournament_count": 6},
                "p2": {"latest_event_ms": 1_750, "tournament_count": 5},
            },
            "scores": {"p1": 1.1, "p2": 0.95},
            "expected_deltas": {
                "p1": {"score_delta": 0.1, "rank_delta": 0},
                "p2": {"score_delta": 0.05, "rank_delta": 0},
            },
        },
        {
            "rows": [
                {
                    "player_id": "p1",
                    "display_name": "Player One",
                    "score": 1.05,
                    "rank": 2,
                    "tournament_count": 7,
                    "window_count": 5,
                },
                {
                    "player_id": "p2",
                    "display_name": "Player Two",
                    "score": 1.2,
                    "rank": 1,
                    "tournament_count": 6,
                    "window_count": 5,
                },
                {
                    "player_id": "p3",
                    "display_name": "Player Three",
                    "score": 0.8,
                    "rank": 3,
                    "tournament_count": 3,
                    "window_count": 3,
                },
            ],
            "calc_ts": 3_000,
            "now_ms": 3_500,
            "events": {
                "p1": {"latest_event_ms": 2_800, "tournament_count": 7},
                "p2": {"latest_event_ms": 2_750, "tournament_count": 6},
                "p3": {"latest_event_ms": 2_700, "tournament_count": 3},
            },
            "scores": {"p1": 1.05, "p2": 1.2, "p3": 0.8},
            "expected_deltas": {
                "p1": {"score_delta": -0.05, "rank_delta": -1},
                "p2": {"score_delta": 0.25, "rank_delta": 1},
                "p3": {"is_new": True},
            },
        },
        {
            "rows": [
                {
                    "player_id": "p1",
                    "display_name": "Player One",
                    "score": 1.35,
                    "rank": 1,
                    "tournament_count": 8,
                    "window_count": 6,
                },
                {
                    "player_id": "p2",
                    "display_name": "Player Two",
                    "score": 1.2,
                    "rank": 2,
                    "tournament_count": 7,
                    "window_count": 6,
                },
            ],
            "calc_ts": 4_000,
            "now_ms": 4_500,
            "events": {
                "p1": {"latest_event_ms": 3_800, "tournament_count": 8},
                "p2": {"latest_event_ms": 3_750, "tournament_count": 7},
            },
            "scores": {"p1": 1.35, "p2": 1.2},
            "expected_deltas": {
                "p1": {
                    "score_delta": 0.30,
                    "rank_delta": 1,
                },  # Improved from rank 2 to 1
                "p2": {
                    "score_delta": 0.0,
                    "rank_delta": -1,
                },  # Dropped from rank 1 to 2
            },
        },
    ]

    run_index = {"current": 0}

    async def fake_fetch_page(session, **kwargs):
        # Check if this is a historical query (ts_ms parameter)
        ts_ms = kwargs.get("ts_ms")
        if ts_ms is not None:
            # Find the config that matches this timestamp
            for cfg in run_configs:
                if cfg["calc_ts"] == ts_ms:
                    return (
                        cfg["rows"],
                        len(cfg["rows"]),
                        cfg["calc_ts"],
                        "2024.09.01",
                    )
            # If timestamp doesn't match any config, return empty
            return [], 0, ts_ms, "2024.09.01"

        # Current query - return current run's data
        config = run_configs[run_index["current"]]
        return (
            config["rows"],
            len(config["rows"]),
            config["calc_ts"],
            "2024.09.01",
        )

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, run_configs[run_index["current"]]["calc_ts"], "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        config = run_configs[run_index["current"]]
        return {
            pid: config["events"][pid]
            for pid in player_ids
            if pid in config["events"]
        }

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input type
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)

        config = run_configs[run_index["current"]]
        if cutoff_ms is not None:
            # For baseline queries with cutoff, figure out which historical run this is
            # The cutoff_ms should match a calc_ts from a previous run
            for cfg in run_configs:
                if cfg["calc_ts"] == cutoff_ms:
                    return {
                        pid: cfg["scores"].get(pid, 1.0)
                        for pid in player_events
                    }
            # If no match, return default
            return {pid: 1.0 for pid in player_events}
        return {
            pid: config["scores"][pid]
            for pid in player_events
            if pid in config["scores"]
        }

    def fake_now():
        return run_configs[run_index["current"]]["now_ms"]

    class FakeSession:
        async def execute(self, _query, params=None):
            class FakeResult:
                def __init__(self, value):
                    self._value = value

                def scalar(self):
                    return self._value

            # Check if this is a query for yesterday's data (cutoff_ms param)
            # Since all runs are on the same "day", there is no yesterday data
            if params and "cutoff" in params:
                cutoff = params.get("cutoff")
                # Return None if cutoff is before all our data
                if cutoff is not None and cutoff < 1_000:
                    return FakeResult(None)

            # For other baseline queries, return previous calc_ts
            if run_index["current"] > 0:
                return FakeResult(
                    run_configs[run_index["current"] - 1]["calc_ts"]
                )
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
        snapshot_mod, "_fetch_player_events", fake_fetch_events, raising=False
    )
    monkeypatch.setattr(
        snapshot_mod,
        "_first_scores_after_events",
        fake_first_scores,
        raising=False,
    )
    monkeypatch.setattr(snapshot_mod, "_now_ms", fake_now, raising=False)
    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    # Run the task multiple times, simulating Celery Beat
    for i, config in enumerate(run_configs):
        run_index["current"] = i

        # Verify lock is not held before run
        lock = fake_redis.get(RIPPLE_SNAPSHOT_LOCK_KEY)
        assert (
            lock is None
        ), f"Run {i}: Lock should not be held before task starts"

        # Execute the task
        result = snapshot_mod.refresh_ripple_snapshots()
        assert (
            result.get("skipped") is not True
        ), f"Run {i}: Task should not be skipped"

        # Verify lock is released after run
        lock_after = fake_redis.get(RIPPLE_SNAPSHOT_LOCK_KEY)
        assert (
            lock_after is None
        ), f"Run {i}: Lock should be released after task completes"

        # Verify state was persisted
        state_raw = fake_redis.get(RIPPLE_STABLE_STATE_KEY)
        assert state_raw is not None, f"Run {i}: State should be persisted"
        state = orjson.loads(state_raw)

        # Verify all expected players are in state
        expected_player_ids = set(config["scores"].keys())
        assert (
            set(state.keys()) == expected_player_ids
        ), f"Run {i}: State should contain all players"

        # Verify stable payload was persisted
        stable_raw = fake_redis.get(RIPPLE_STABLE_LATEST_KEY)
        assert (
            stable_raw is not None
        ), f"Run {i}: Stable payload should be persisted"
        stable_payload = orjson.loads(stable_raw)
        assert stable_payload["record_count"] == len(
            config["rows"]
        ), f"Run {i}: Record count mismatch"

        # Verify delta computation
        delta_raw = fake_redis.get(RIPPLE_STABLE_DELTAS_KEY)
        assert (
            delta_raw is not None
        ), f"Run {i}: Delta payload should be persisted"
        delta_payload = orjson.loads(delta_raw)

        if config["expected_deltas"] is None:
            # First run: no baseline, so deltas should be empty
            assert (
                delta_payload["baseline_generated_at_ms"] is None
            ), f"Run {i}: No baseline on first run"
            assert (
                delta_payload["record_count"] == 0
            ), f"Run {i}: No deltas on first run"
        else:
            # Subsequent runs: verify deltas against previous run
            assert (
                delta_payload["baseline_generated_at_ms"] is not None
            ), f"Run {i}: Baseline should exist"
            players_deltas = delta_payload["players"]

            for player_id, expected in config["expected_deltas"].items():
                assert (
                    player_id in players_deltas
                ), f"Run {i}: Player {player_id} should have delta entry"
                player_delta = players_deltas[player_id]

                if "score_delta" in expected:
                    assert player_delta["score_delta"] == pytest.approx(
                        expected["score_delta"], abs=0.01
                    ), f"Run {i}: Player {player_id} score delta mismatch"

                if "rank_delta" in expected:
                    assert (
                        player_delta["rank_delta"] == expected["rank_delta"]
                    ), f"Run {i}: Player {player_id} rank delta mismatch"

                if "is_new" in expected:
                    assert (
                        player_delta["is_new"] is expected["is_new"]
                    ), f"Run {i}: Player {player_id} is_new flag mismatch"

    # Final verification: ensure state evolved correctly across all runs
    final_state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    final_config = run_configs[-1]

    for player_id, expected_score in final_config["scores"].items():
        assert (
            player_id in final_state
        ), f"Final state missing player {player_id}"
        assert final_state[player_id]["stable_score"] == pytest.approx(
            expected_score
        ), f"Final state score mismatch for {player_id}"
