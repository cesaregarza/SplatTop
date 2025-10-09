"""Celery signal handlers that emit telemetry into Redis."""

from __future__ import annotations

import logging
import time
from typing import Any

from celery import signals

from celery_app.connections import redis_conn
from shared_lib.monitoring.config import metrics_enabled
from shared_lib.monitoring.constants import (
    CELERY_TASK_COUNT_HASH,
    CELERY_TASK_DURATION_HASH,
    CELERY_TASK_FAILURE_HASH,
    CELERY_TASK_INFLIGHT_SET,
    CELERY_TASK_LAST_RUN_HASH,
    CELERY_TASK_START_HASH,
)

logger = logging.getLogger(__name__)


def _now() -> float:
    return time.time()


@signals.task_prerun.connect
def record_task_start(
    sender: Any = None,
    task_id: str | None = None,
    task: Any | None = None,
    **_: Any,
) -> None:
    if not metrics_enabled() or task_id is None:
        return

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
    if not metrics_enabled() or task_id is None or task is None:
        return

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
        pipe.execute()
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("Failed to store celery task completion metrics: %s", exc)
