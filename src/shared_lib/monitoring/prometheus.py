"""Prometheus metric primitives and custom collectors."""

from __future__ import annotations

import logging
from typing import Iterable, Iterator

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
)
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from shared_lib.monitoring.config import metrics_enabled
from shared_lib.monitoring.constants import (
    CELERY_TASK_COUNT_HASH,
    CELERY_TASK_DURATION_HASH,
    CELERY_TASK_FAILURE_HASH,
    CELERY_TASK_INFLIGHT_SET,
    CELERY_TASK_LAST_RUN_HASH,
)

logger = logging.getLogger(__name__)

REQUEST_LATENCY = Histogram(
    "fastapi_request_duration_seconds",
    "Duration of HTTP requests in seconds grouped by method and route.",
    labelnames=["method", "path"],
)
REQUEST_COUNTER = Counter(
    "fastapi_requests_total",
    "Total count of HTTP requests grouped by method, route, and status code.",
    labelnames=["method", "path", "status"],
)
INFLIGHT_REQUESTS = Gauge(
    "fastapi_requests_in_progress",
    "Number of active HTTP requests currently being served.",
    labelnames=["method", "path"],
)

SPLATGPT_CACHE_REQUESTS = Counter(
    "splatgpt_cache_requests_total",
    "Count of inference cache lookups grouped by outcome.",
    labelnames=["status"],
)
SPLATGPT_INFERENCE_DURATION = Histogram(
    "splatgpt_inference_duration_seconds",
    "Duration of inference request handling grouped by source.",
    labelnames=["source"],
)
SPLATGPT_QUEUE_SIZE = Gauge(
    "splatgpt_queue_size",
    "Current backlog of pending inference requests.",
)
SPLATGPT_INFLIGHT = Gauge(
    "splatgpt_requests_in_progress",
    "Number of inference requests currently executing against the model server.",
)
SPLATGPT_ERRORS = Counter(
    "splatgpt_request_errors_total",
    "Count of inference processing errors grouped by stage.",
    labelnames=["stage"],
)

WEBSOCKET_CONNECTIONS = Gauge(
    "fastapi_websocket_connections",
    "Active websocket connections grouped by player id.",
    labelnames=["player_id"],
)
WEBSOCKET_EVENTS = Counter(
    "fastapi_websocket_events_total",
    "Websocket lifecycle events.",
    labelnames=["event"],
)
WEBSOCKET_BROADCAST_DURATION = Histogram(
    "fastapi_websocket_broadcast_duration_seconds",
    "Duration of websocket broadcast operations.",
    labelnames=["player_id"],
)
WEBSOCKET_BYTES_SENT = Counter(
    "fastapi_websocket_bytes_total",
    "Total bytes of websocket payloads sent.",
    labelnames=["player_id"],
)

TABLE_REFRESH_DURATION = Histogram(
    "fastapi_table_refresh_duration_seconds",
    "Duration of SQLite materialization runs grouped by table name.",
    labelnames=["table"],
)
TABLE_REFRESH_TOTAL = Counter(
    "fastapi_table_refresh_total",
    "Count of table refresh outcomes.",
    labelnames=["table", "outcome"],
)
TABLE_REFRESH_SLEEP_SECONDS = Gauge(
    "fastapi_table_refresh_sleep_seconds",
    "Sleep interval scheduled before the next refresh.",
    labelnames=["table"],
)

PUBSUB_EVENTS = Counter(
    "fastapi_pubsub_messages_total",
    "PubSub listener events grouped by outcome.",
    labelnames=["event"],
)
PUBSUB_RESTARTS = Counter(
    "fastapi_pubsub_listener_restarts_total",
    "Number of times the pubsub listener restarted.",
)
PUBSUB_ACTIVE = Gauge(
    "fastapi_pubsub_listener_active",
    "Flag indicating if the pubsub listener loop is running.",
)
PUBSUB_BYTES_BROADCAST = Counter(
    "fastapi_pubsub_bytes_total",
    "Bytes broadcast to websocket subscribers via pubsub.",
    labelnames=["player_id"],
)

RATE_LIMIT_EVENTS = Counter(
    "fastapi_rate_limit_events_total",
    "Outcomes of rate limit evaluations.",
    labelnames=["outcome"],
)

AUTH_FAILURES = Counter(
    "fastapi_auth_failures_total",
    "Authentication failures grouped by reason.",
    labelnames=["reason"],
)

SEARCH_LATENCY = Histogram(
    "fastapi_search_duration_seconds",
    "Duration of search lookups in seconds grouped by outcome.",
    labelnames=["outcome"],
)
SEARCH_RESULTS = Counter(
    "fastapi_search_requests_total",
    "Search endpoint requests grouped by outcome.",
    labelnames=["outcome"],
)

RIPPLE_CACHE_REQUESTS = Counter(
    "ripple_cache_requests_total",
    "Ripple API cache lookups grouped by kind and status.",
    labelnames=["kind", "status"],
)
RIPPLE_QUERY_DURATION = Histogram(
    "ripple_query_duration_seconds",
    "Duration of ripple query calls grouped by kind.",
    labelnames=["kind"],
)
RIPPLE_CACHE_PAYLOAD_BYTES = Gauge(
    "ripple_cache_payload_bytes",
    "Payload size stored in ripple cache per kind.",
    labelnames=["kind"],
)

API_USAGE_EVENTS = Counter(
    "api_usage_events_total",
    "Outcome of API usage flush processing steps.",
    labelnames=["result"],
)
API_USAGE_BATCH_DURATION = Histogram(
    "api_usage_flush_duration_seconds",
    "Duration of API usage flush batches.",
)
API_USAGE_RECOVERED = Counter(
    "api_usage_recovered_total",
    "Recovered usage events moved back to the primary queue.",
)

DATA_PULL_DURATION = Histogram(
    "celery_data_pull_duration_seconds",
    "Duration of data pull tasks grouped by task name.",
    labelnames=["task"],
)
DATA_PULL_ROWS = Gauge(
    "celery_data_pull_rows",
    "Row count snapshots for data pull tasks.",
    labelnames=["task"],
)

METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST


def render_latest() -> bytes:
    """Render all registered Prometheus metrics."""

    ensure_collectors_registered()
    return generate_latest(REGISTRY)


class _CeleryMetricsCollector:
    """Custom collector that surfaces Celery task telemetry stored in Redis."""

    def collect(self) -> Iterator[GaugeMetricFamily | CounterMetricFamily]:
        if not metrics_enabled():
            return

        try:
            from fast_api_app.connections import redis_conn as fastapi_redis
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.debug("Celery metrics collector missing redis_conn: %s", exc)
            return

        redis_conn = fastapi_redis
        try:
            counts = redis_conn.hgetall(CELERY_TASK_COUNT_HASH) or {}
            durations = redis_conn.hgetall(CELERY_TASK_DURATION_HASH) or {}
            failures = redis_conn.hgetall(CELERY_TASK_FAILURE_HASH) or {}
            last_run = redis_conn.hgetall(CELERY_TASK_LAST_RUN_HASH) or {}
            inflight = redis_conn.scard(CELERY_TASK_INFLIGHT_SET) or 0
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.debug("Failed to read celery metrics from Redis: %s", exc)
            return

        task_names = _merge_keys(
            counts.keys(), durations.keys(), failures.keys(), last_run.keys()
        )

        total_metric = CounterMetricFamily(
            "celery_task_executions_total",
            "Total number of Celery task executions grouped by task name.",
            labels=["task"],
        )
        failure_metric = CounterMetricFamily(
            "celery_task_failures_total",
            "Total number of Celery task failures grouped by task name.",
            labels=["task"],
        )
        runtime_sum_metric = GaugeMetricFamily(
            "celery_task_runtime_seconds_sum",
            "Aggregate runtime in seconds for completed Celery tasks.",
            labels=["task"],
        )
        runtime_avg_metric = GaugeMetricFamily(
            "celery_task_runtime_seconds_avg",
            "Average runtime in seconds for completed Celery tasks.",
            labels=["task"],
        )
        last_run_metric = GaugeMetricFamily(
            "celery_task_last_finished_timestamp_seconds",
            "Unix timestamp of the most recent task completion.",
            labels=["task"],
        )

        for name in task_names:
            count = _to_float(counts.get(name))
            duration = _to_float(durations.get(name))
            failure = _to_float(failures.get(name))
            last_ts = _to_float(last_run.get(name))

            total_metric.add_metric([name], count)
            failure_metric.add_metric([name], failure)
            runtime_sum_metric.add_metric([name], max(duration, 0.0))
            avg = duration / count if count > 0 else 0.0
            runtime_avg_metric.add_metric([name], max(avg, 0.0))
            last_run_metric.add_metric([name], last_ts)

        inflight_metric = GaugeMetricFamily(
            "celery_tasks_in_progress",
            "Number of Celery tasks currently executing.",
        )
        inflight_metric.add_metric([], float(max(inflight, 0)))

        try:
            from shared_lib.constants import API_USAGE_QUEUE_KEY
        except Exception:  # pragma: no cover - defensive fallback
            api_usage_len = None
        else:
            try:
                api_usage_len = redis_conn.llen(API_USAGE_QUEUE_KEY)
            except Exception:  # pragma: no cover - best effort only
                api_usage_len = None

        if api_usage_len is not None:
            usage_metric = GaugeMetricFamily(
                "api_usage_queue_length",
                "Number of pending API usage events waiting to be flushed.",
            )
            usage_metric.add_metric([], float(max(api_usage_len, 0)))
        else:
            usage_metric = None

        yield total_metric
        yield failure_metric
        yield runtime_sum_metric
        yield runtime_avg_metric
        yield last_run_metric
        yield inflight_metric
        if usage_metric is not None:
            yield usage_metric


def _merge_keys(*iterables: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for iterable in iterables:
        out.update(iterable)
    return out


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return default


_collector_registered = False


def ensure_collectors_registered() -> None:
    """Register custom collectors if metrics are enabled."""

    global _collector_registered
    if _collector_registered or not metrics_enabled():
        return

    try:
        REGISTRY.register(_CeleryMetricsCollector())
    except ValueError:
        # Already registered by another worker/process.
        pass
    else:
        _collector_registered = True
