from __future__ import annotations

import os

# Ensure DB env vars exist before importing modules that build SQLAlchemy engines
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "pass")
os.environ.setdefault("DB_NAME", "db")
os.environ.setdefault("RANKINGS_DB_NAME", "db")

from conftest import FakeRedis

from celery_app.tasks import ripple_snapshot as snapshot_mod
from shared_lib.constants import RIPPLE_SNAPSHOT_LOCK_KEY


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
