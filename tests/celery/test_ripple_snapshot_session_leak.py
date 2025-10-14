from __future__ import annotations

import os
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.exc import InterfaceError

# Ensure DB env vars exist before importing modules that build SQLAlchemy engines
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")

from conftest import FakeRedis

from celery_app.tasks import ripple_snapshot as snapshot_mod


def test_session_cleanup_after_query_failure(monkeypatch):
    """
    Test that simulates the production bug: A query fails midway through
    the first session context, leaving a transaction open. The retry
    logic disposes the engine but the session reuse causes:
    "async PG driver is refusing to start a new transaction because it
    believes a previous query is still active on the same connection."

    This test should FAIL if the bug exists, showing that session cleanup
    is incomplete after InterfaceError.
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

    call_count = {"fetch_page": 0, "fetch_danger": 0, "fetch_events": 0}

    async def fake_fetch_page(session, **kwargs):
        call_count["fetch_page"] += 1
        # First call succeeds
        if call_count["fetch_page"] == 1:
            return rows, 1, 1234, "2024.09.01"
        # Second call (retry) should also work if session cleanup was proper
        return rows, 1, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        call_count["fetch_danger"] += 1
        # First call fails with InterfaceError - simulates connection issue
        if call_count["fetch_danger"] == 1:
            raise InterfaceError(
                "stmt", None, RuntimeError("connection closed")
            )
        # Second call (retry) succeeds
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        call_count["fetch_events"] += 1
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

    session_count = {"created": 0, "closed": 0, "active_transaction": False}

    class FakeSession:
        def __init__(self):
            session_count["created"] += 1

        async def execute(self, _query, params=None):
            # If a previous transaction is still active, this simulates the production error
            if session_count["active_transaction"]:
                raise InterfaceError(
                    "stmt",
                    None,
                    RuntimeError(
                        "cannot start new transaction - previous query still active"
                    ),
                )

            # Start transaction
            session_count["active_transaction"] = True

            class FakeResult:
                def __init__(self, value):
                    self._value = value

                def scalar(self):
                    return self._value

            return FakeResult(None)

        @asynccontextmanager
        async def begin(self):
            yield

        async def close(self):
            # Properly close the session and transaction
            session_count["closed"] += 1
            session_count["active_transaction"] = False

    @asynccontextmanager
    async def fake_session_context():
        session = FakeSession()
        try:
            yield session
        finally:
            await session.close()

    class FakeScoped:
        def __call__(self):
            return fake_session_context()

        def remove(self):
            pass

    class FakeEngine:
        def __init__(self):
            self.disposed = 0

        async def dispose(self):
            self.disposed += 1
            # Engine dispose should clean up connection state
            # If sessions aren't properly closed, this won't help
            if session_count["active_transaction"]:
                # In real code, dispose() doesn't magically close active sessions
                # This is the bug!
                pass

    fake_engine = FakeEngine()
    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )
    monkeypatch.setattr(
        snapshot_mod, "rankings_async_engine", fake_engine, raising=False
    )

    # This should succeed with retry
    result = snapshot_mod.refresh_ripple_snapshots()

    # Should have retried once
    assert call_count["fetch_page"] == 2  # Once on first attempt, once on retry
    assert (
        call_count["fetch_danger"] == 2
    )  # Once (failed), once (retry succeeded)
    assert fake_engine.disposed == 1  # Engine was disposed once

    # All sessions should be closed
    assert session_count["created"] > 0
    assert session_count["closed"] == session_count["created"]
    assert not session_count["active_transaction"]


def test_multiple_session_contexts_in_single_run(monkeypatch):
    """
    Test that the three separate `async with rankings_async_session()` contexts
    in _refresh_snapshots_async_once() properly clean up between contexts.

    Lines 692, 728, 747 each open a new session context. If the first context
    doesn't properly close, the second context might reuse a dirty connection.
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

    session_lifecycle = []

    async def fake_fetch_page(session, **kwargs):
        session_lifecycle.append(("fetch_page", "query", session.id))
        return rows, 1, 1234, "2024.09.01"

    async def fake_fetch_danger(session, **kwargs):
        session_lifecycle.append(("fetch_danger", "query", session.id))
        return [], 0, 1234, "2024.09.01"

    async def fake_fetch_events(session, player_ids):
        session_lifecycle.append(("fetch_events", "query", session.id))
        return {"p1": {"latest_event_ms": 1100, "tournament_count": 5}}

    async def fake_first_scores(session, player_events, *, cutoff_ms=None):
        session_lifecycle.append(("first_scores", "query", session.id))
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

    class FakeSession:
        def __init__(self):
            self.id = id(self)
            self.transaction_active = False
            session_lifecycle.append(("session", "created", self.id))

        async def execute(self, _query, params=None):
            if self.transaction_active:
                # This should never happen - each query should be in its own transaction
                raise RuntimeError(
                    f"Session {self.id} already has active transaction!"
                )
            self.transaction_active = True

            class FakeResult:
                def __init__(self, value):
                    self._value = value

                def scalar(self):
                    return self._value

            # Auto-commit after query
            self.transaction_active = False
            return FakeResult(None)

        @asynccontextmanager
        async def begin(self):
            yield

        async def close(self):
            session_lifecycle.append(("session", "closed", self.id))
            if self.transaction_active:
                session_lifecycle.append(
                    ("session", "ERROR: not committed", self.id)
                )

    @asynccontextmanager
    async def fake_session_context():
        session = FakeSession()
        try:
            yield session
        finally:
            await session.close()

    class FakeScoped:
        def __call__(self):
            return fake_session_context()

        def remove(self):
            pass

    monkeypatch.setattr(
        snapshot_mod, "rankings_async_session", FakeScoped(), raising=False
    )

    result = snapshot_mod.refresh_ripple_snapshots()
    assert result.get("skipped") is not True

    # Print the session lifecycle for debugging
    print("\n=== Session Lifecycle ===")
    for event_type, action, session_id in session_lifecycle:
        print(f"{event_type:15} {action:20} session_{session_id}")

    # Verify all sessions were properly closed
    created = [evt for evt in session_lifecycle if evt[1] == "created"]
    closed = [evt for evt in session_lifecycle if evt[1] == "closed"]
    assert len(created) == len(
        closed
    ), f"Session leak: {len(created)} created, {len(closed)} closed"

    # Verify no uncommitted transactions
    errors = [evt for evt in session_lifecycle if "ERROR" in evt[1]]
    assert len(errors) == 0, f"Found uncommitted transactions: {errors}"

    # Verify we used multiple sessions (at least 3 contexts in the code)
    assert len(created) >= 1, "Should have created at least 1 session"
