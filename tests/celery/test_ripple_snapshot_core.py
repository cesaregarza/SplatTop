from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import orjson
import pytest
from sqlalchemy import BigInteger

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
    RIPPLE_PLAYER_INDEX_LATEST_KEY,
    RIPPLE_PLAYER_INDEX_META_KEY,
    RIPPLE_PLAYER_INDEX_PLAYER_PREFIX,
    RIPPLE_STABLE_DELTAS_KEY,
    RIPPLE_STABLE_LATEST_KEY,
    RIPPLE_STABLE_META_KEY,
    RIPPLE_STABLE_STATE_KEY,
)


def _player_index_key(player_id: str) -> str:
    return f"{RIPPLE_PLAYER_INDEX_PLAYER_PREFIX}{player_id}"


def test_fetch_player_ranked_history_limits_and_sorts():
    rows = [
        {
            "player_id": "p1",
            "tournament_id": 10_000,
            "event_ms": 10_000,
            "tournament_name": None,
            "is_ranked": False,
        },
        {
            "player_id": "p2",
            "tournament_id": 42,
            "event_ms": 2_000,
            "tournament_name": "Weekend Cup",
            "is_ranked": True,
            "team_id": 77,
            "team_name": "Weekend Warriors",
            "wins": 3,
            "losses": 1,
        },
    ]
    for idx in range(30):
        rows.append(
            {
                "player_id": "p1",
                "tournament_id": 1_000 + idx,
                "event_ms": 1_000 + idx,
                "tournament_name": None,
                "is_ranked": True,
                "team_id": 2_000 + idx,
                "team_name": None,
                "wins": 1,
                "losses": 2,
            }
        )

    class FakeMappings:
        def all(self):
            return rows

    class FakeResult:
        def mappings(self):
            return FakeMappings()

    class FakeSession:
        async def execute(self, _query, params=None):
            assert params is not None
            assert params["max_per_player"] == 25
            assert isinstance(
                _query._bindparams["max_per_player"].type,
                BigInteger,
            )
            return FakeResult()

    history = asyncio.run(
        snapshot_mod._fetch_player_ranked_history(
            FakeSession(),
            ["p1", "p2"],
            max_per_player=25,
        )
    )

    assert len(history["p1"]) == 25
    assert history["p1"][0]["event_ms"] == 1_029
    assert history["p1"][-1]["event_ms"] == 1_005
    assert all(item["ranked"] is True for item in history["p1"])
    assert all(item["tournament_id"] != 10_000 for item in history["p1"])
    assert history["p1"][0]["tournament_name"] == "Tournament 1029"
    assert history["p1"][0]["result_summary"] == "1W-2L"
    assert history["p2"][0]["tournament_name"] == "Weekend Cup"
    assert history["p2"][0]["team_name"] == "Weekend Warriors"
    assert history["p2"][0]["team_id"] == 77
    assert history["p2"][0]["result_summary"] == "3W-1L"


def test_fetch_player_ranked_history_allows_unbounded_fetch():
    rows = []
    for idx in range(30):
        rows.append(
            {
                "player_id": "p1",
                "tournament_id": 1_000 + idx,
                "event_ms": 1_000 + idx,
                "tournament_name": None,
                "is_ranked": True,
                "team_id": 2_000 + idx,
                "team_name": None,
                "wins": 1,
                "losses": 2,
            }
        )

    class FakeMappings:
        def all(self):
            return rows

    class FakeResult:
        def mappings(self):
            return FakeMappings()

    class FakeSession:
        async def execute(self, _query, params=None):
            assert params is not None
            assert params["max_per_player"] is None
            assert isinstance(
                _query._bindparams["max_per_player"].type,
                BigInteger,
            )
            return FakeResult()

        async def rollback(self):
            raise AssertionError("rollback should not be called")

    history = asyncio.run(
        snapshot_mod._fetch_player_ranked_history(
            FakeSession(),
            ["p1"],
            max_per_player=None,
        )
    )

    assert len(history["p1"]) == 30
    assert history["p1"][0]["event_ms"] == 1_029
    assert history["p1"][-1]["event_ms"] == 1_000
    assert history["p1"][0]["tournament_name"] == "Tournament 1029"


def test_fetch_player_ranked_history_rolls_back_after_query_error():
    class FakeSession:
        def __init__(self):
            self.rollback_calls = 0

        async def execute(self, _query, params=None):
            raise RuntimeError("boom")

        async def rollback(self):
            self.rollback_calls += 1

    session = FakeSession()

    history = asyncio.run(
        snapshot_mod._fetch_player_ranked_history(
            session,
            ["p1"],
            max_per_player=25,
        )
    )

    assert history == {}
    assert session.rollback_calls == 1


def test_fetch_player_match_loo_impacts_rolls_back_after_query_error():
    class FakeSession:
        def __init__(self):
            self.rollback_calls = 0

        async def execute(self, _query, params=None):
            raise RuntimeError("boom")

        async def rollback(self):
            self.rollback_calls += 1

    session = FakeSession()

    impacts = asyncio.run(
        snapshot_mod._fetch_player_match_loo_impacts(
            session,
            ["p1"],
            calculated_at_ms=1234,
            build_version="2024.09.01",
            max_per_player=20,
        )
    )

    assert impacts == {}
    assert session.rollback_calls == 1


def test_fetch_player_match_loo_impacts_formats_rows():
    rows = [
        {
            "player_id": "p1",
            "match_id": 501,
            "tournament_id": 42,
            "tournament_name": "Weekend Cup",
            "event_ms": 2_000,
            "player_rank": 7,
            "player_score": 1.75,
            "is_win": False,
            "exact_score_delta": 0.36,
            "exact_abs_delta": 0.36,
            "player_team_id": 101,
            "player_team_name": "Weekend Warriors",
            "opponent_team_id": 202,
            "opponent_team_name": "Night Shift",
            "player_team_score": 1,
            "opponent_team_score": 3,
            "player_team_players": [
                "Alpha",
                "Bravo",
                "Charlie",
                "Delta",
            ],
            "opponent_team_players": [
                "Echo",
                "Foxtrot",
                "Golf",
                "Hotel",
            ],
        },
        {
            "player_id": "p2",
            "match_id": 999,
            "tournament_id": 88,
            "tournament_name": None,
            "event_ms": None,
            "player_rank": 22,
            "player_score": 0.8,
            "is_win": True,
            "exact_score_delta": -0.41,
            "exact_abs_delta": 0.41,
            "player_team_id": 404,
            "player_team_name": None,
            "opponent_team_id": 505,
            "opponent_team_name": None,
            "player_team_score": 3,
            "opponent_team_score": 0,
            "player_team_players": ["9001", "9002"],
            "opponent_team_players": ["9101", "9102"],
        },
    ]

    class FakeMappings:
        def all(self):
            return rows

    class FakeResult:
        def mappings(self):
            return FakeMappings()

    class FakeSession:
        async def execute(self, _query, params=None):
            assert params is not None
            assert params["calculated_at_ms"] == 1234
            assert params["build_version"] == "2024.09.01"
            assert params["match_any_build_version"] is False
            return FakeResult()

    impacts = asyncio.run(
        snapshot_mod._fetch_player_match_loo_impacts(
            FakeSession(),
            ["p1", "p2"],
            calculated_at_ms=1234,
            build_version="2024.09.01",
            max_per_player=20,
        )
    )

    assert impacts["p1"][0]["match_id"] == 501
    assert impacts["p1"][0]["tournament_name"] == "Weekend Cup"
    assert impacts["p1"][0]["is_win"] is False
    assert impacts["p1"][0]["exact_score_delta"] == pytest.approx(0.36)
    assert impacts["p1"][0]["player_team_name"] == "Weekend Warriors"
    assert impacts["p1"][0]["opponent_team_name"] == "Night Shift"
    assert impacts["p1"][0]["player_team_score"] == 1
    assert impacts["p1"][0]["opponent_team_score"] == 3
    assert impacts["p1"][0]["player_team_players"] == [
        "Alpha",
        "Bravo",
        "Charlie",
        "Delta",
    ]
    assert impacts["p2"][0]["tournament_name"] == "Tournament 88"
    assert impacts["p2"][0]["is_win"] is True
    assert impacts["p2"][0]["player_team_name"] == "Team 404"
    assert impacts["p2"][0]["opponent_team_name"] == "Team 505"
    assert impacts["p2"][0]["player_team_players"] == ["9001", "9002"]


def test_fetch_player_match_loo_impacts_falls_back_to_latest_snapshot():
    strict_rows = [
        {
            "player_id": "p1",
            "match_id": 501,
            "tournament_id": 42,
            "tournament_name": "Weekend Cup",
            "event_ms": 2_000,
            "player_rank": 7,
            "player_score": 1.75,
            "is_win": False,
            "exact_score_delta": 0.36,
            "exact_abs_delta": 0.36,
            "player_team_id": 101,
            "player_team_name": "Weekend Warriors",
            "opponent_team_id": 202,
            "opponent_team_name": "Night Shift",
            "player_team_score": 1,
            "opponent_team_score": 3,
            "player_team_players": ["Alpha"],
            "opponent_team_players": ["Echo"],
        }
    ]
    fallback_rows = [
        {
            "player_id": "p2",
            "match_id": 777,
            "tournament_id": 88,
            "tournament_name": "Fallback Finals",
            "event_ms": 1_000,
            "player_rank": 12,
            "player_score": 0.8,
            "is_win": True,
            "exact_score_delta": -0.41,
            "exact_abs_delta": 0.41,
            "player_team_id": 404,
            "player_team_name": "Fallback Force",
            "opponent_team_id": 505,
            "opponent_team_name": "Patch Notes",
            "player_team_score": 3,
            "opponent_team_score": 0,
            "player_team_players": ["9001", "9002"],
            "opponent_team_players": ["9101", "9102"],
        }
    ]

    class FakeMappings:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return FakeMappings(self._rows)

    class FakeSession:
        def __init__(self):
            self.calls = []

        async def execute(self, _query, params=None):
            assert params is not None
            self.calls.append(dict(params))
            if "calculated_at_ms" not in params:
                assert params["player_ids"] == ["p2"]
                return FakeResult(
                    [
                        {
                            "player_id": "p2",
                            "calculated_at_ms": 999,
                            "build_version": "2024.08.20",
                        }
                    ]
                )

            if params["player_ids"] == ["p1", "p2"]:
                assert params["calculated_at_ms"] == 1234
                assert params["build_version"] == "2024.09.01"
                assert params["match_any_build_version"] is False
                return FakeResult(strict_rows)

            assert params["player_ids"] == ["p2"]
            assert params["calculated_at_ms"] == 999
            assert params["build_version"] == "2024.08.20"
            assert params["match_any_build_version"] is False
            return FakeResult(fallback_rows)

    session = FakeSession()

    impacts = asyncio.run(
        snapshot_mod._fetch_player_match_loo_impacts(
            session,
            ["p1", "p2"],
            calculated_at_ms=1234,
            build_version="2024.09.01",
            max_per_player=20,
        )
    )

    assert impacts["p1"][0]["match_id"] == 501
    assert impacts["p2"][0]["match_id"] == 777
    assert impacts["p2"][0]["player_team_name"] == "Fallback Force"
    assert len(session.calls) == 3


def test_select_player_match_loo_rows_keeps_helpful_and_harmful_sides():
    rows = []
    for idx in range(14):
        rows.append(
            {
                "match_id": 2_000 + idx,
                "exact_score_delta": 1.4 - idx * 0.1,
                "exact_abs_delta": 1.4 - idx * 0.1,
            }
        )
    for idx in range(6):
        rows.append(
            {
                "match_id": 3_000 + idx,
                "exact_score_delta": -0.6 + idx * 0.05,
                "exact_abs_delta": 0.6 - idx * 0.05,
            }
        )

    selected = snapshot_mod._select_player_match_loo_rows(
        rows, max_per_player=10
    )

    assert len(selected) == 10
    harmful = [row for row in selected if row["exact_score_delta"] > 0]
    helpful = [row for row in selected if row["exact_score_delta"] < 0]
    assert len(harmful) == 5
    assert len(helpful) == 5
    assert [row["match_id"] for row in harmful] == [
        2000,
        2001,
        2002,
        2003,
        2004,
    ]
    assert [row["match_id"] for row in helpful] == [
        3000,
        3001,
        3002,
        3003,
        3004,
    ]
    assert [row["exact_abs_delta"] for row in selected] == sorted(
        [row["exact_abs_delta"] for row in selected],
        reverse=True,
    )


def test_select_player_match_loo_rows_backfills_from_dominant_side():
    rows = [
        {
            "match_id": 4_000 + idx,
            "exact_score_delta": 2.0 - idx * 0.1,
            "exact_abs_delta": 2.0 - idx * 0.1,
        }
        for idx in range(12)
    ]

    selected = snapshot_mod._select_player_match_loo_rows(
        rows, max_per_player=10
    )

    assert len(selected) == 10
    assert all(row["exact_score_delta"] > 0 for row in selected)
    assert [row["match_id"] for row in selected] == [
        4000,
        4001,
        4002,
        4003,
        4004,
        4005,
        4006,
        4007,
        4008,
        4009,
    ]


def test_select_player_match_loo_rows_prefers_leftover_signed_rows_over_neutral():
    rows = [
        {
            "match_id": 5_000 + idx,
            "exact_score_delta": 1.5 - idx * 0.1,
            "exact_abs_delta": 1.5 - idx * 0.1,
        }
        for idx in range(7)
    ]
    rows.extend(
        [
            {
                "match_id": 5_100,
                "exact_score_delta": -0.4,
                "exact_abs_delta": 0.4,
            },
            {
                "match_id": 5_101,
                "exact_score_delta": -0.3,
                "exact_abs_delta": 0.3,
            },
            {
                "match_id": 5_200,
                "exact_score_delta": 0.0,
                "exact_abs_delta": 0.95,
            },
            {
                "match_id": 5_201,
                "exact_score_delta": 0.0,
                "exact_abs_delta": 0.9,
            },
        ]
    )

    selected = snapshot_mod._select_player_match_loo_rows(
        rows, max_per_player=8
    )

    assert len(selected) == 8
    assert [row["match_id"] for row in selected] == [
        5000,
        5001,
        5002,
        5003,
        5004,
        5005,
        5100,
        5101,
    ]
    assert all(row["match_id"] not in {5200, 5201} for row in selected)


def test_refresh_ripple_snapshots_persists_payloads(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(snapshot_mod, "redis_conn", fake_redis, raising=False)
    fake_redis.set(
        RIPPLE_PLAYER_INDEX_LATEST_KEY,
        orjson.dumps(
            {
                "generated_at_ms": 1,
                "record_count": 2,
                "player_ids": ["p1", "stale-player"],
            }
        ),
    )
    fake_redis.set(
        _player_index_key("stale-player"),
        orjson.dumps({"player_id": "stale-player"}),
    )

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

    async def fake_fetch_history(session, player_ids, *, max_per_player=25):
        assert set(player_ids) == {"p1", "p2"}
        assert max_per_player == 25
        return {
            "p1": [
                {
                    "tournament_id": 9,
                    "tournament_name": "Winter Open",
                    "event_ms": 1_100,
                    "ranked": True,
                    "placement_label": None,
                    "result_summary": None,
                    "team_name": None,
                    "team_id": None,
                }
            ]
        }

    async def fake_fetch_match_loo_impacts(
        session,
        player_ids,
        *,
        calculated_at_ms,
        build_version,
        max_per_player=20,
    ):
        assert set(player_ids) == {"p1", "p2"}
        assert calculated_at_ms == 1234
        assert build_version == "2024.09.01"
        assert max_per_player == 20
        return {
            "p1": [
                {
                    "match_id": 501,
                    "tournament_id": 9,
                    "tournament_name": "Winter Open",
                    "event_ms": 1_100,
                    "player_rank": 1,
                    "player_score": 1.2,
                    "is_win": False,
                    "exact_score_delta": 0.32,
                    "exact_abs_delta": 0.32,
                    "player_team_id": 70,
                    "player_team_name": "Ink Storm",
                    "opponent_team_id": 71,
                    "opponent_team_name": "Tidal Wave",
                    "player_team_score": 2,
                    "opponent_team_score": 3,
                    "player_team_players": [
                        "Player One",
                        "Player Two",
                        "Player Three",
                        "Player Four",
                    ],
                    "opponent_team_players": [
                        "Opponent One",
                        "Opponent Two",
                        "Opponent Three",
                        "Opponent Four",
                    ],
                }
            ]
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
    monkeypatch.setattr(
        snapshot_mod,
        "_fetch_player_ranked_history",
        fake_fetch_history,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod,
        "_fetch_player_match_loo_impacts",
        fake_fetch_match_loo_impacts,
        raising=False,
    )

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
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

    player_index_payload = orjson.loads(
        fake_redis.get(RIPPLE_PLAYER_INDEX_LATEST_KEY)
    )
    assert player_index_payload["record_count"] == 2
    assert set(player_index_payload["player_ids"]) == {"p1", "p2"}

    player_one_payload = orjson.loads(fake_redis.get(_player_index_key("p1")))
    assert player_one_payload["eligible"] is True
    assert player_one_payload["minimum_required_tournaments"] == 3
    assert player_one_payload["history_record_count"] == 1
    assert (
        player_one_payload["tournament_history_ranked"][0]["tournament_name"]
        == "Winter Open"
    )
    assert player_one_payload["match_loo_record_count"] == 1
    assert player_one_payload["match_loo_impacts"][0]["match_id"] == 501
    assert (
        player_one_payload["match_loo_impacts"][0]["player_team_name"]
        == "Ink Storm"
    )
    assert (
        player_one_payload["match_loo_impacts"][0]["player_team_players"][0]
        == "Player One"
    )

    player_two_payload = orjson.loads(fake_redis.get(_player_index_key("p2")))
    assert player_two_payload["history_record_count"] == 0
    assert player_two_payload["match_loo_record_count"] == 0
    assert fake_redis.get(_player_index_key("stale-player")) is None

    player_index_meta = orjson.loads(
        fake_redis.get(RIPPLE_PLAYER_INDEX_META_KEY)
    )
    assert player_index_meta["record_count"] == 2

    state = orjson.loads(fake_redis.get(RIPPLE_STABLE_STATE_KEY))
    assert set(state.keys()) == {"p1", "p2"}
    assert state["p1"]["stable_score"] == pytest.approx(1.2)
    assert state["p1"]["tournament_count"] == 6


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
    monkeypatch.setattr(
        snapshot_mod,
        "_fetch_player_ranked_history",
        AsyncMock(return_value={}),
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod,
        "_fetch_player_match_loo_impacts",
        AsyncMock(return_value={}),
        raising=False,
    )

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        # Validate input: player_events should be Dict[str, int]
        assert isinstance(player_events, dict)
        for pid, ts in player_events.items():
            assert isinstance(pid, str)
            assert isinstance(ts, int)
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


def test_build_player_index_payload_preserves_private_scores_for_admins():
    payload, _meta, players = snapshot_mod._build_player_index_payload(
        all_rows=[
            {
                "player_id": "p1",
                "display_name": "Player 1",
                "tournament_count": 2,
                "window_count": 2,
            }
        ],
        stable_rows=[
            {
                "player_id": "p1",
                "display_name": "Player 1",
                "stable_rank": 21,
                "stable_score": 1.75,
                "display_score": 193.75,
                "tournament_count": 2,
            }
        ],
        danger_rows=[],
        tournament_history_by_player={},
        match_loo_impacts_by_player={},
        delta_payload={},
        generated_at_ms=1_700_000_000_000,
        calculated_at_ms=1_700_000_000_000,
        build_version="2024.09.01",
    )

    player_payload = players["p1"]
    assert payload["record_count"] == 1
    assert player_payload["stable_rank"] is None
    assert player_payload["stable_score"] is None
    assert player_payload["display_score"] is None
    assert player_payload["private_stable_rank"] == 21
    assert player_payload["private_stable_score"] == pytest.approx(1.75)
    assert player_payload["private_display_score"] == pytest.approx(193.75)
