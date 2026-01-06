import importlib
import threading
import time
from types import ModuleType
from typing import Any, Optional

import pytest


class LockRedis:
    def __init__(
        self,
        barrier: Optional[threading.Barrier] = None,
        lock_ttl_override: Optional[float] = None,
    ) -> None:
        self._store: dict[str, Any] = {}
        self._expirations: dict[str, float] = {}
        self._barrier = barrier
        self._lock_ttl_override = lock_ttl_override
        self.publish_calls: list[tuple[str, Any]] = []

    def _is_expired(self, key: str) -> bool:
        expiry = self._expirations.get(key)
        if expiry is None:
            return False
        if time.time() >= expiry:
            self._expirations.pop(key, None)
            self._store.pop(key, None)
            return True
        return False

    def get(self, key: str) -> Any:
        if self._barrier is not None:
            self._barrier.wait()
        if self._is_expired(key):
            return None
        return self._store.get(key)

    def set(
        self,
        key: str,
        val: Any,
        nx: bool = False,
        ex: Optional[float] = None,
        px: Optional[float] = None,
    ) -> bool:
        if nx and key in self._store and not self._is_expired(key):
            return False
        self._store[key] = val
        ttl = ex
        if self._lock_ttl_override is not None and key.startswith(
            "fetch_player_data:"
        ):
            ttl = self._lock_ttl_override
        if ttl:
            self._expirations[key] = time.time() + float(ttl)
        return True

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._expirations.pop(key, None)

    def exists(self, key: str) -> bool:
        if self._is_expired(key):
            return False
        return key in self._store

    def publish(self, channel: str, message: Any) -> None:
        self.publish_calls.append((channel, message))


def _load_player_detail(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    module = importlib.import_module("celery_app.tasks.player_detail")
    return importlib.reload(module)


def _patch_player_detail(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    redis_conn: LockRedis,
    fetch_impl: Any,
) -> None:
    monkeypatch.setattr(module, "redis_conn", redis_conn, raising=False)
    monkeypatch.setattr(
        module, "_fetch_player_data", fetch_impl, raising=False
    )
    monkeypatch.setattr(
        module, "_fetch_season_data", lambda player_id: [], raising=False
    )
    monkeypatch.setattr(
        module,
        "aggregate_player_data",
        lambda *args, **kwargs: {},
        raising=False,
    )


def test_task_lock_is_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    barrier = threading.Barrier(2)
    redis_conn = LockRedis(barrier=barrier)
    calls = []

    player_detail = _load_player_detail(monkeypatch)

    def fake_fetch(player_id):
        calls.append(player_id)
        return []

    _patch_player_detail(monkeypatch, player_detail, redis_conn, fake_fetch)

    def run_task() -> None:
        player_detail.fetch_player_data("test-player")

    t1 = threading.Thread(target=run_task)
    t2 = threading.Thread(target=run_task)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(calls) == 1


def test_lock_released_on_task_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_conn = LockRedis()

    player_detail = _load_player_detail(monkeypatch)

    def fake_fetch(player_id):
        return []

    _patch_player_detail(monkeypatch, player_detail, redis_conn, fake_fetch)

    player_detail.fetch_player_data("test-player")

    assert redis_conn.get("fetch_player_data:test-player") is None


def test_lock_released_on_task_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_conn = LockRedis()

    player_detail = _load_player_detail(monkeypatch)

    def fake_fetch(player_id):
        raise ValueError("boom")

    _patch_player_detail(monkeypatch, player_detail, redis_conn, fake_fetch)

    with pytest.raises(ValueError):
        player_detail.fetch_player_data("test-player")

    assert redis_conn.get("fetch_player_data:test-player") is None


def test_lock_prevents_stale_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_conn = LockRedis(lock_ttl_override=0.01)
    calls = []

    player_detail = _load_player_detail(monkeypatch)

    def fake_fetch(player_id):
        calls.append(player_id)
        time.sleep(0.05)
        return []

    _patch_player_detail(monkeypatch, player_detail, redis_conn, fake_fetch)

    def run_task() -> None:
        player_detail.fetch_player_data("test-player")

    t1 = threading.Thread(target=run_task)
    t1.start()
    time.sleep(0.02)
    t2 = threading.Thread(target=run_task)
    t2.start()
    t1.join()
    t2.join()

    assert len(calls) == 1
