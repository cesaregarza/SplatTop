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
    RIPPLE_SNAPSHOT_LOCK_KEY,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_PREVIOUS_KEY,
    RIPPLE_STABLE_PREVIOUS_META_KEY,
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

    async def fake_first_scores(session, events, *, cutoff_ms=None):
        return {"p1": 1.2, "p2": 0.9}

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

    delta_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_DELTAS_KEY))
    assert delta_payload["baseline_generated_at_ms"] is None
    assert delta_payload["record_count"] == 0
    assert delta_payload["players"] == {}

    state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    assert set(state.keys()) == {"p1", "p2"}
    assert state["p1"]["stable_score"] == pytest.approx(1.2)
    assert state["p1"]["tournament_count"] == 6


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


def test_bootstrap_rebuilds_stable_state(monkeypatch):
    fake_redis = FakeRedis()
    # Prepopulate state with old tournament timestamp
    state_payload = {
        "p1": {
            "stable_score": 0.5,
            "last_tournament_ms": 500,
            "last_active_ms": 700,
            "tournament_count": 3,
            "updated_at_ms": 0,
            "recent_score_delta": None,
            "recent_score_delta_ms": None,
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

    async def fake_first_scores(session, events):
        return {"p1": 0.9}

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

    stable_payload = orjson.loads(fake_redis.get(RIPPLE_STABLE_LATEST_KEY))
    item = stable_payload["data"][0]
    # Bootstrap ignores previously cached stable score and rebuilds from source data.
    assert item["stable_score"] == pytest.approx(0.9)
    assert item["last_tournament_ms"] == 400

    state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    assert state["p1"]["stable_score"] == pytest.approx(0.9)
    assert state["p1"]["updated_at_ms"] == 4_000


def test_refresh_ripple_snapshots_skips_when_locked(monkeypatch):
    fake_redis = FakeRedis()
    fake_redis.set(RIPPLE_SNAPSHOT_LOCK_KEY, "existing")
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)

    called = {"value": False}

    async def _should_not_run():
        called["value"] = True
        return {}

    monkeypatch.setattr(
        snapshot_mod,
        "_refresh_snapshots_async",
        _should_not_run,
        raising=False,
    )

    result = snapshot_mod.refresh_ripple_snapshots()
    assert result == {"skipped": True, "reason": "locked"}
    assert called["value"] is False
