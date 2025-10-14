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


def test_refresh_ripple_snapshots_computes_deltas(monkeypatch):
    fake_redis = FakeRedis()

    previous_payload = {
        "generated_at_ms": 1_000,
        "record_count": 2,
        "data": [
            {
                "player_id": "p1",
                "display_name": "Player One",
                "stable_rank": 1,
                "stable_score": 1.0,
                "display_score": 175.0,
            },
            {
                "player_id": "p2",
                "display_name": "Player Two",
                "stable_rank": 2,
                "stable_score": 0.9,
                "display_score": 172.5,
            },
        ],
    }
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(previous_payload))

    previous_state = {
        "p1": {
            "stable_score": 1.0,
            "last_tournament_ms": 900,
            "last_active_ms": 900,
            "tournament_count": 6,
            "updated_at_ms": 0,
            "recent_score_delta": None,
            "recent_score_delta_ms": None,
        },
        "p2": {
            "stable_score": 0.9,
            "last_tournament_ms": 900,
            "last_active_ms": 900,
            "tournament_count": 5,
            "updated_at_ms": 0,
            "recent_score_delta": None,
            "recent_score_delta_ms": None,
        },
    }
    fake_redis.set(RIPPLE_STABLE_STATE_KEY, orjson.dumps(previous_state))

    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 0.7,
            "rank": 1,
            "tournament_count": 7,
        },
        {
            "player_id": "p3",
            "display_name": "Player Three",
            "score": 0.5,
            "rank": 2,
            "tournament_count": 4,
        },
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 2, 3_000, "2024.09.03"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 3_000, "2024.09.03"

    async def fake_fetch_events(session, player_ids):
        return {
            "p1": {"latest_event_ms": 1_500, "tournament_count": 7},
            "p3": {"latest_event_ms": 1_400, "tournament_count": 4},
        }

    observed_requests = {}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
        observed_requests["value"] = dict(player_events)
        if cutoff_ms is not None:
            return {pid: 1.0 for pid in player_events}
        return {"p1": 1.25, "p3": 0.82}

    current_ms = 4_000

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

    snapshot_mod.refresh_ripple_snapshots()

    assert observed_requests["value"] == {"p1": 1_500, "p3": 1_400}

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    assert delta_payload["baseline_generated_at_ms"] == 1_000
    players = delta_payload["players"]
    assert players["p1"]["rank_delta"] == 0
    assert players["p1"]["score_delta"] == pytest.approx(0.25)
    assert players["p1"]["display_score_delta"] == pytest.approx(6.25)
    assert players["p1"]["is_new"] is False
    assert players["p3"]["is_new"] is True
    assert delta_payload["newcomers"] == ["p3"]
    dropout_ids = {entry["player_id"] for entry in delta_payload["dropouts"]}
    assert dropout_ids == {"p2"}

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    assert stable_payload["record_count"] == 2
    score_map = {
        entry["player_id"]: entry["stable_score"]
        for entry in stable_payload["data"]
    }
    assert score_map["p1"] == pytest.approx(1.25)
    assert score_map["p3"] == pytest.approx(0.82)


def test_delta_resets_after_followup_snapshot(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    previous_payload = {
        "generated_at_ms": 900,
        "record_count": 1,
        "data": [
            {
                "player_id": "p1",
                "display_name": "Player One",
                "stable_rank": 1,
                "stable_score": 0.7,
                "display_score": snapshot_mod._display_score(0.7),
            }
        ],
    }
    fake_redis.set(RIPPLE_STABLE_LATEST_KEY, orjson.dumps(previous_payload))

    previous_state = {
        "p1": {
            "stable_score": 0.7,
            "last_tournament_ms": 1_000,
            "last_active_ms": 1_000,
            "tournament_count": 4,
            "updated_at_ms": 800,
            "recent_score_delta": None,
            "recent_score_delta_ms": None,
        }
    }
    fake_redis.set(RIPPLE_STABLE_STATE_KEY, orjson.dumps(previous_state))

    rows = [
        {
            "player_id": "p1",
            "display_name": "Player One",
            "score": 0.8,
            "rank": 1,
            "tournament_count": 5,
            "window_count": 3,
        }
    ]

    async def fake_fetch_page(session, **kwargs):
        return rows, 1, 4_000, "2024.09.04"

    async def fake_fetch_danger(session, **kwargs):
        return [], 0, 4_000, "2024.09.04"

    async def fake_fetch_events(session, player_ids):
        return {"p1": {"latest_event_ms": 2_000, "tournament_count": 5}}

    first_score_calls: list[dict] = []

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
        first_score_calls.append(
            {"events": dict(player_events), "cutoff_ms": cutoff_ms}
        )
        return {"p1": 0.8}

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

    now_values = [
        2_500,
        2_500 + snapshot_mod.MS_PER_DAY,
    ]

    def fake_now():
        return now_values.pop(0)

    monkeypatch.setattr(snapshot_mod, "_now_ms", fake_now, raising=False)

    baseline_values = [4_000]

    class FakeSession:
        async def execute(self, _query, params=None):
            class FakeResult:
                def __init__(self, value):
                    self._value = value

                def scalar(self):
                    return self._value

            value = baseline_values.pop(0) if baseline_values else 4_000
            return FakeResult(value)

        @asynccontextmanager
        async def begin(self):
            yield

    @asynccontextmanager
    async def fake_session_ctx():
        yield FakeSession()

    class FakeScoped:
        def __call__(self):
            return fake_session_ctx()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    snapshot_mod.refresh_ripple_snapshots()

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    player_delta = delta_payload["players"]["p1"]
    assert player_delta["score_delta"] == pytest.approx(0.1)
    assert player_delta["display_score_delta"] == pytest.approx(2.5)
    assert first_score_calls == [{"events": {"p1": 2_000}, "cutoff_ms": None}]

    snapshot_mod.refresh_ripple_snapshots()

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    player_delta = delta_payload["players"]["p1"]
    assert player_delta["score_delta"] in (None, pytest.approx(0.0))
    assert player_delta["display_score_delta"] in (None, pytest.approx(0.0))
