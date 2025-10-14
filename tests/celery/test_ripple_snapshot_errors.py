from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy.exc import InterfaceError

# Ensure DB env vars exist before importing modules that build SQLAlchemy engines
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")

from celery_app.tasks import ripple_snapshot as snapshot_mod


def test_refresh_snapshots_async_retries_on_interface_error(monkeypatch):
    calls = {"count": 0}
    sleep_calls = {"count": 0}

    async def fake_once():
        calls["count"] += 1
        if calls["count"] == 1:
            raise InterfaceError("stmt", None, RuntimeError("boom"))
        return {"ok": True}

    class FakeEngine:
        def __init__(self):
            self.disposed = 0

        async def dispose(self):
            self.disposed += 1

    async def fake_sleep(_delay):
        sleep_calls["count"] += 1

    fake_engine = FakeEngine()
    monkeypatch.setattr(
        snapshot_mod,
        "_refresh_snapshots_async_once",
        fake_once,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod,
        "rankings_async_engine",
        fake_engine,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod.asyncio,
        "sleep",
        fake_sleep,
        raising=False,
    )

    result = asyncio.run(snapshot_mod._refresh_snapshots_async())

    assert result == {"ok": True}
    assert calls["count"] == 2
    assert fake_engine.disposed == 1
    assert sleep_calls["count"] == 1


def test_refresh_snapshots_async_gives_up_after_max_retries(monkeypatch):
    attempts = {"count": 0}
    sleep_delays: list[float] = []

    async def fake_once():
        attempts["count"] += 1
        raise InterfaceError("stmt", None, RuntimeError("boom"))

    class FakeEngine:
        def __init__(self):
            self.disposed = 0

        async def dispose(self):
            self.disposed += 1

    async def fake_sleep(delay):
        sleep_delays.append(delay)

    fake_engine = FakeEngine()
    monkeypatch.setattr(
        snapshot_mod,
        "_refresh_snapshots_async_once",
        fake_once,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod,
        "rankings_async_engine",
        fake_engine,
        raising=False,
    )
    monkeypatch.setattr(
        snapshot_mod.asyncio,
        "sleep",
        fake_sleep,
        raising=False,
    )

    with pytest.raises(InterfaceError):
        asyncio.run(snapshot_mod._refresh_snapshots_async())

    assert attempts["count"] == snapshot_mod.MAX_REFRESH_RETRIES
    assert fake_engine.disposed == snapshot_mod.MAX_REFRESH_RETRIES - 1
    assert len(sleep_delays) == snapshot_mod.MAX_REFRESH_RETRIES - 1
    assert all(delay >= 0.5 for delay in sleep_delays)
