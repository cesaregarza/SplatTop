import asyncio
import importlib

import pytest


class _DummyManager:
    def __init__(
        self,
        table_name: str,
        *,
        should_fail: bool,
        cadence: int = 600,
        retry_cadence: int = 60,
    ):
        self.table_name = table_name
        self.redis_key = f"{table_name}_key"
        self.cadence = cadence
        self.retry_cadence = retry_cadence
        self.should_fail = should_fail
        self.calls = 0
        self.initialized = 0

    def initialize_table(self) -> None:
        self.initialized += 1

    def insert_data(self, data: dict) -> None:
        return None

    def update_database(self) -> None:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError("redis miss")


def test_background_runner_retries_failed_table_independently(
    monkeypatch,
):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    bg_mod = importlib.import_module("fast_api_app.background_tasks")
    bg_mod = importlib.reload(bg_mod)

    slow_manager = _DummyManager("slow_table", should_fail=False)
    retrying_manager = _DummyManager("retry_table", should_fail=True)
    runner = bg_mod.BackgroundRunner([slow_manager, retrying_manager])

    real_sleep = asyncio.sleep

    class _StopLoop(Exception):
        pass

    async def fake_sleep(seconds: int):
        if seconds == slow_manager.cadence:
            await asyncio.Future()
            return

        if seconds == retrying_manager.retry_cadence:
            if retrying_manager.calls >= 2:
                raise _StopLoop
            await real_sleep(0)
            return

        await real_sleep(0)

    monkeypatch.setattr(bg_mod.asyncio, "sleep", fake_sleep)

    with pytest.raises(_StopLoop):
        asyncio.run(asyncio.wait_for(runner.run(), timeout=0.2))

    assert slow_manager.initialized == 1
    assert retrying_manager.initialized == 1
    assert slow_manager.calls == 1
    assert retrying_manager.calls >= 2
