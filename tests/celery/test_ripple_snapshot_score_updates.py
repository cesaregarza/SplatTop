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
    RIPPLE_STABLE_STATE_KEY,
)


def test_refresh_ripple_snapshots_waits_for_post_event_scores(monkeypatch):
    fake_redis = FakeRedis()

    previous_payload = {
        "generated_at_ms": 1_000,
        "record_count": 1,
        "data": [
            {
                "player_id": "p1",
                "display_name": "Player One",
                "stable_rank": 1,
                "stable_score": 1.0,
                "display_score": 175.0,
            }
        ],
    }
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(previous_payload))

    previous_state = {
        "p1": {
            "stable_score": 1.0,
            "last_tournament_ms": 900,
            "last_active_ms": 900,
            "tournament_count": 6,
            "updated_at_ms": 900,
            "recent_score_delta": None,
            "recent_score_delta_ms": None,
        }
    }
    fake_redis.set(RIPPLE_STABLE_STATE_KEY, orjson.dumps(previous_state))

    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    page_rows = [
        (
            [
                {
                    "player_id": "p1",
                    "display_name": "Player One",
                    "score": 1.0,
                    "rank": 1,
                    "tournament_count": 6,
                }
            ],
            1,
            2_000,
            "2024.09.02",
        ),
        (
            [
                {
                    "player_id": "p1",
                    "display_name": "Player One",
                    "score": 1.3,
                    "rank": 1,
                    "tournament_count": 7,
                }
            ],
            1,
            3_000,
            "2024.09.03",
        ),
    ]

    async def fake_fetch_page(session, **kwargs):
        rows, total, calc_ts, build = page_rows.pop(0)
        return rows, total, calc_ts, build

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 2_000, "2024.09.02"

    async def fake_fetch_events(session, player_ids):
        return {"p1": {"latest_event_ms": 1_500, "tournament_count": 7}}

    pending_scores = {"result": {}}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
        pending_scores.setdefault("calls", []).append(
            {"events": dict(player_events), "cutoff_ms": cutoff_ms}
        )
        if cutoff_ms is not None:
            # Baseline fallback still uses previous stable scores
            return {pid: 1.0 for pid in player_events}
        return dict(pending_scores["result"])

    now_values = [4_000, 5_000]

    def fake_now():
        return now_values.pop(0)

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
    monkeypatch.setattr(snapshot_mod, "_now_ms", fake_now, raising=False)

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
                        return FakeResult(2_000)

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

    # First run: ranking snapshot still old; score override missing
    snapshot_mod.refresh_ripple_snapshots()
    assert pending_scores["calls"] == [
        {"events": {"p1": 1_500}, "cutoff_ms": None}
    ]

    state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    assert state["p1"]["stable_score"] == pytest.approx(1.0)
    assert state["p1"]["last_tournament_ms"] == 1_500

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    players = delta_payload["players"]
    assert players["p1"]["score_delta"] in (None, 0.0)

    # Second run: rankings available; provide override
    pending_scores["result"] = {"p1": 1.35}
    snapshot_mod.refresh_ripple_snapshots()
    assert pending_scores["calls"][-1] == {
        "events": {"p1": 1_500},
        "cutoff_ms": None,
    }

    state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    assert state["p1"]["stable_score"] == pytest.approx(1.35)
    assert state["p1"]["last_tournament_ms"] == 1_500

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    players = delta_payload["players"]
    assert players["p1"]["score_delta"] == pytest.approx(0.35)

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    entry = stable_payload["data"][0]
    assert entry["stable_score"] == pytest.approx(1.35)
    assert entry["last_tournament_ms"] == 1_500
