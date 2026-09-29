import json
from types import SimpleNamespace

import pytest

from shared_lib.monitoring.constants import (
    CELERY_TASK_COUNT_HASH,
    CELERY_TASK_FAILURE_HASH,
    CELERY_TASK_LAST_RUN_HASH,
    CELERY_TASK_MEMORY_HASH,
)


@pytest.fixture()
def metrics_module(monkeypatch):
    for key, value in {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_USER": "user",
        "DB_PASSWORD": "pass",
        "DB_NAME": "db",
        "RANKINGS_DB_NAME": "db",
    }.items():
        monkeypatch.setenv(key, value)
    import celery_app.metrics as module

    module._task_memory_starts.clear()
    monkeypatch.setattr(module, "metrics_enabled", lambda: True)
    yield module
    module._task_memory_starts.clear()


def test_task_memory_sample_is_coherent_and_keeps_negative_delta(
    metrics_module, fake_redis, monkeypatch
):
    before = metrics_module._ProcessMemory(rss_bytes=10_000, hwm_bytes=12_000)
    after = metrics_module._ProcessMemory(rss_bytes=9_000, hwm_bytes=12_000)
    readings = iter((before, after))
    monkeypatch.setattr(
        metrics_module, "_read_process_memory", lambda: next(readings)
    )
    monkeypatch.setattr(metrics_module, "redis_conn", fake_redis)
    monkeypatch.setattr(metrics_module, "_now", lambda: 123.0)

    task = SimpleNamespace(name="tasks.memory")
    metrics_module.record_task_start(task_id="task-1", task=task)
    metrics_module.record_task_end(
        task_id="task-1",
        task=task,
        state="FAILURE",
        retval=RuntimeError("boom"),
    )

    sample = json.loads(fake_redis.hget(CELERY_TASK_MEMORY_HASH, task.name))
    assert sample == {
        "rss_before_bytes": 10_000,
        "rss_after_bytes": 9_000,
        "rss_delta_bytes": -1_000,
        "process_rss_hwm_bytes": 12_000,
    }
    assert fake_redis.hget(CELERY_TASK_COUNT_HASH, task.name) == "1"
    assert fake_redis.hget(CELERY_TASK_FAILURE_HASH, task.name) == "1"
    assert "task-1" not in metrics_module._task_memory_starts


def test_disabled_metrics_do_not_read_memory_or_redis(
    metrics_module, monkeypatch
):
    metrics_module._task_memory_starts["task-2"] = (
        metrics_module._ProcessMemory(rss_bytes=1, hwm_bytes=1)
    )
    monkeypatch.setattr(metrics_module, "metrics_enabled", lambda: False)

    def fail_read():
        raise AssertionError(
            "memory must not be read while metrics are disabled"
        )

    class NoRedis:
        def __getattr__(self, name):
            raise AssertionError(
                "Redis must not be read while metrics are disabled: " f"{name}"
            )

    monkeypatch.setattr(metrics_module, "_read_process_memory", fail_read)
    monkeypatch.setattr(metrics_module, "redis_conn", NoRedis())

    metrics_module.record_task_start(task_id="task-3")
    metrics_module.record_task_end(
        task_id="task-2",
        task=SimpleNamespace(name="tasks.memory"),
        state="SUCCESS",
    )
    assert metrics_module._task_memory_starts == {}


def test_memory_reading_falls_back_and_ignores_malformed_proc(
    metrics_module, monkeypatch
):
    import builtins

    module = metrics_module

    files = {
        "/proc/self/status": "VmRSS: broken kB\nVmHWM: 7 kB\n",
        "/proc/self/statm": "100 3 0 0 0 0 0\n",
    }

    class FakeFile:
        def __init__(self, text):
            self.text = text

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __iter__(self):
            return iter(self.text.splitlines())

        def read(self):
            return self.text

    def fake_open(path, *args, **kwargs):
        if path in files:
            return FakeFile(files[path])
        raise AssertionError(path)

    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(module.os, "sysconf", lambda name: 4096)

    memory = module._read_process_memory()
    assert memory.rss_bytes == 3 * 4096
    assert memory.hwm_bytes == 7 * 1024


def test_same_name_completions_keep_coherent_pairs_when_finishing_in_reverse_order(
    metrics_module, fake_redis, monkeypatch
):
    readings = iter(
        (
            metrics_module._ProcessMemory(100, 120),
            metrics_module._ProcessMemory(110, 125),
            metrics_module._ProcessMemory(200, 220),
            metrics_module._ProcessMemory(190, 225),
        )
    )
    monkeypatch.setattr(
        metrics_module, "_read_process_memory", lambda: next(readings)
    )
    monkeypatch.setattr(metrics_module, "redis_conn", fake_redis)
    monkeypatch.setattr(metrics_module, "_now", lambda: 123.0)
    task = SimpleNamespace(name="tasks.same_name")

    metrics_module.record_task_start(task_id="task-a", task=task)
    metrics_module.record_task_start(task_id="task-b", task=task)
    metrics_module.record_task_end(task_id="task-b", task=task, state="SUCCESS")
    first_sample = json.loads(
        fake_redis.hget(CELERY_TASK_MEMORY_HASH, task.name)
    )
    assert first_sample["rss_before_bytes"] == 110
    assert first_sample["rss_after_bytes"] == 200
    assert first_sample["rss_delta_bytes"] == 90
    assert "task-a" in metrics_module._task_memory_starts
    assert "task-b" not in metrics_module._task_memory_starts
    metrics_module.record_task_end(task_id="task-a", task=task, state="SUCCESS")

    # The last completion wins as one serialized sample, so its pair cannot
    # be mixed with the other in-flight task's readings.
    sample = json.loads(fake_redis.hget(CELERY_TASK_MEMORY_HASH, task.name))
    assert sample["rss_before_bytes"] == 100
    assert sample["rss_after_bytes"] == 190
    assert sample["rss_delta_bytes"] == 90
    assert "task-a" not in metrics_module._task_memory_starts
    assert "task-b" not in metrics_module._task_memory_starts


def test_redis_completion_failure_still_cleans_local_memory_start(
    metrics_module, monkeypatch
):
    class FailingRedis:
        def hget(self, key, field):
            raise RuntimeError("redis unavailable")

        def pipeline(self):
            raise RuntimeError("redis unavailable")

    readings = iter(
        (
            metrics_module._ProcessMemory(100, 120),
            metrics_module._ProcessMemory(110, 125),
        )
    )
    monkeypatch.setattr(
        metrics_module, "_read_process_memory", lambda: next(readings)
    )
    monkeypatch.setattr(metrics_module, "redis_conn", FailingRedis())
    task = SimpleNamespace(name="tasks.redis_failure")

    metrics_module.record_task_start(task_id="task-fail", task=task)
    metrics_module.record_task_end(
        task_id="task-fail", task=task, state="FAILURE"
    )

    assert metrics_module._task_memory_starts == {}


def test_sampling_failure_clears_stale_sample_and_keeps_completion_metrics(
    metrics_module, fake_redis, monkeypatch
):
    readings = iter(
        (
            metrics_module._ProcessMemory(100, 120),
            metrics_module._ProcessMemory(110, 125),
        )
    )
    monkeypatch.setattr(
        metrics_module, "_read_process_memory", lambda: next(readings)
    )
    times = iter((10.0, 11.0, 20.0, 21.0))
    monkeypatch.setattr(metrics_module, "_now", lambda: next(times))
    monkeypatch.setattr(metrics_module, "redis_conn", fake_redis)
    task = SimpleNamespace(name="tasks.unavailable_memory")

    metrics_module.record_task_start(task_id="task-good", task=task)
    metrics_module.record_task_end(
        task_id="task-good", task=task, state="SUCCESS"
    )
    assert fake_redis.hget(CELERY_TASK_MEMORY_HASH, task.name) is not None

    def sampling_failure():
        raise OSError("/proc unavailable")

    monkeypatch.setattr(
        metrics_module, "_read_process_memory", sampling_failure
    )
    metrics_module.record_task_start(task_id="task-bad", task=task)
    metrics_module.record_task_end(
        task_id="task-bad", task=task, state="SUCCESS"
    )

    assert fake_redis.hget(CELERY_TASK_MEMORY_HASH, task.name) is None
    assert fake_redis.hget(CELERY_TASK_COUNT_HASH, task.name) == "2"
    assert fake_redis.hget(CELERY_TASK_LAST_RUN_HASH, task.name) == "21.0"


def test_collector_parser_ignores_malformed_and_nonfinite_memory_fields():
    from shared_lib.monitoring.prometheus import _parse_memory_sample

    sample = _parse_memory_sample(
        json.dumps(
            {
                "rss_before_bytes": "nan",
                "rss_after_bytes": 2_000,
                "rss_delta_bytes": "-inf",
                "process_rss_hwm_bytes": "bad",
            }
        )
    )
    assert sample == {"rss_after_bytes": 2_000.0}
    assert _parse_memory_sample("not-json") is None
