"""Configuration helpers for the monitoring/telemetry stack."""

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def metrics_enabled() -> bool:
    """Return whether Prometheus metrics should be exposed."""

    raw = os.getenv("ENABLE_METRICS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


@lru_cache(maxsize=1)
def metrics_namespace() -> str:
    """Return the Redis key namespace used for telemetry bookkeeping."""

    return os.getenv("METRICS_NAMESPACE", "metrics")


def metrics_key(*parts: str) -> str:
    """Build a Redis key for telemetry artifacts."""

    return ":".join((metrics_namespace(), *parts))
