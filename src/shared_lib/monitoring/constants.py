"""Redis key constants used by telemetry instrumentation."""

from shared_lib.monitoring.config import metrics_key

CELERY_TASK_START_HASH = metrics_key("celery", "start")
CELERY_TASK_COUNT_HASH = metrics_key("celery", "count")
CELERY_TASK_DURATION_HASH = metrics_key("celery", "duration_sum")
CELERY_TASK_FAILURE_HASH = metrics_key("celery", "failures")
CELERY_TASK_LAST_RUN_HASH = metrics_key("celery", "last_run_ts")
CELERY_TASK_INFLIGHT_SET = metrics_key("celery", "inflight")
