"""Celery signal handlers that emit telemetry into Redis."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - unavailable on some platforms
    resource = None  # type: ignore[assignment]

from celery import signals

from celery_app.connections import redis_conn
from shared_lib.monitoring.config import metrics_enabled
from shared_lib.monitoring.constants import (
    CELERY_TASK_COUNT_HASH,
    CELERY_TASK_DURATION_HASH,
    CELERY_TASK_FAILURE_HASH,
    CELERY_TASK_INFLIGHT_SET,
    CELERY_TASK_LAST_RUN_HASH,
    CELERY_TASK_MEMORY_HASH,
    CELERY_TASK_START_HASH,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ProcessMemory:
    """One point-in-time process memory observation.

    ``hwm_bytes`` is the process lifetime high-water mark reported by the
    operating system. It is not a peak allocated by the current task.
    """

    rss_bytes: int | None
    hwm_bytes: int | None


# Signal handlers normally pair one prerun with one postrun. The cap also
# prevents a broken signal lifecycle from retaining an unbounded number of
# task ids in a worker process.
_MAX_TRACKED_MEMORY_STARTS = 4096
_task_memory_starts: dict[str, _ProcessMemory | None] = {}


def _parse_proc_memory_value(parts: list[str]) -> int | None:
    if len(parts) < 2 or parts[1] != "kB":
        return None
    try:
        value = int(parts[0])
    except (TypeError, ValueError):
        return None
    return value * 1024 if value >= 0 else None


def _read_process_memory() -> _ProcessMemory:
    """Read current RSS and lifetime HWM without polling or extra deps."""

    rss_bytes: int | None = None
    hwm_bytes: int | None = None

    try:
        with open("/proc/self/status", encoding="utf-8") as status:
            for line in status:
                key, _, raw_value = line.partition(":")
                if key not in {"VmRSS", "VmHWM"}:
                    continue
                parsed = _parse_proc_memory_value(raw_value.strip().split())
                if key == "VmRSS":
                    rss_bytes = parsed
                else:
                    hwm_bytes = parsed
                if rss_bytes is not None and hwm_bytes is not None:
                    break
    except (OSError, UnicodeError):
        pass

    if rss_bytes is None:
        try:
            with open("/proc/self/statm", encoding="ascii") as statm:
                fields = statm.read().split()
            rss_pages = int(fields[1])
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            if rss_pages >= 0 and page_size > 0:
                rss_bytes = rss_pages * page_size
        except (IndexError, OSError, TypeError, ValueError):
            pass

    if hwm_bytes is None:
        try:
            # Linux reports ru_maxrss in KiB. This fallback only supplies the
            # lifetime HWM; resource.getrusage cannot provide current RSS.
            if resource is not None and sys.platform.startswith("linux"):
                hwm_kib = int(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                )
                if hwm_kib >= 0:
                    hwm_bytes = hwm_kib * 1024
        except (AttributeError, OSError, TypeError, ValueError):
            pass

    return _ProcessMemory(rss_bytes=rss_bytes, hwm_bytes=hwm_bytes)


def _safe_read_process_memory() -> _ProcessMemory:
    """Keep an OS sampling failure from suppressing task telemetry."""

    try:
        return _read_process_memory()
    except Exception as exc:  # pragma: no cover - defensive signal boundary
        logger.debug("Failed to read celery process memory: %s", exc)
        return _ProcessMemory(rss_bytes=None, hwm_bytes=None)


def _remember_memory_start(task_id: str, memory: _ProcessMemory | None) -> None:
    if len(_task_memory_starts) >= _MAX_TRACKED_MEMORY_STARTS:
        oldest_task_id = next(iter(_task_memory_starts))
        _task_memory_starts.pop(oldest_task_id, None)
    _task_memory_starts[task_id] = memory


def _memory_payload(
    start: _ProcessMemory | None, end: _ProcessMemory
) -> dict[str, int | None] | None:
    before = start.rss_bytes if start is not None else None
    after = end.rss_bytes
    delta = after - before if before is not None and after is not None else None
    hwm_values = [
        memory.hwm_bytes
        for memory in (start, end)
        if memory is not None and memory.hwm_bytes is not None
    ]
    hwm = max(hwm_values) if hwm_values else None
    if before is None and after is None and hwm is None:
        return None
    return {
        "rss_before_bytes": before,
        "rss_after_bytes": after,
        "rss_delta_bytes": delta,
        "process_rss_hwm_bytes": hwm,
    }


def _now() -> float:
    return time.time()


@signals.task_prerun.connect
def record_task_start(
    sender: Any = None,
    task_id: str | None = None,
    task: Any | None = None,
    **_: Any,
) -> None:
    if task_id is None or not metrics_enabled():
        return

    _remember_memory_start(task_id, _safe_read_process_memory())

    try:
        pipe = redis_conn.pipeline()
        pipe.hset(CELERY_TASK_START_HASH, task_id, str(_now()))
        pipe.sadd(CELERY_TASK_INFLIGHT_SET, task_id)
        pipe.execute()
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("Failed to store celery task start metrics: %s", exc)


@signals.task_postrun.connect
def record_task_end(
    sender: Any = None,
    task_id: str | None = None,
    task: Any | None = None,
    retval: Any | None = None,
    state: str | None = None,
    **_: Any,
) -> None:
    start_memory = (
        _task_memory_starts.pop(task_id, None) if task_id is not None else None
    )
    if not metrics_enabled() or task_id is None or task is None:
        return

    end_memory = _safe_read_process_memory()
    memory_payload = _memory_payload(start_memory, end_memory)
    now = _now()
    duration: float | None = None

    try:
        start_raw = redis_conn.hget(CELERY_TASK_START_HASH, task_id)
        if start_raw is not None:
            try:
                duration = max(0.0, now - float(start_raw))
            except (TypeError, ValueError):
                duration = None
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Failed to read celery task start time: %s", exc)

    try:
        pipe = redis_conn.pipeline()
        pipe.hdel(CELERY_TASK_START_HASH, task_id)
        pipe.srem(CELERY_TASK_INFLIGHT_SET, task_id)
        pipe.hincrby(CELERY_TASK_COUNT_HASH, task.name, 1)
        if duration is not None:
            pipe.hincrbyfloat(CELERY_TASK_DURATION_HASH, task.name, duration)
        if state not in {"SUCCESS", None}:
            pipe.hincrby(CELERY_TASK_FAILURE_HASH, task.name, 1)
        pipe.hset(CELERY_TASK_LAST_RUN_HASH, task.name, str(now))
        # Clear the prior sample first so an unavailable reading cannot leave
        # stale gauges associated with a newer completion timestamp.
        pipe.hdel(CELERY_TASK_MEMORY_HASH, task.name)
        if memory_payload is not None:
            pipe.hset(
                CELERY_TASK_MEMORY_HASH,
                task.name,
                json.dumps(memory_payload, separators=(",", ":")),
            )
        pipe.execute()
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("Failed to store celery task completion metrics: %s", exc)
