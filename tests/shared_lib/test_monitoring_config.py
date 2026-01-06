import pytest

from shared_lib.monitoring import config


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    config.metrics_enabled.cache_clear()
    config.metrics_namespace.cache_clear()


def test_metrics_enabled_defaults_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENABLE_METRICS", raising=False)
    config.metrics_enabled.cache_clear()
    assert config.metrics_enabled() is True


def test_metrics_enabled_false_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_METRICS", "false")
    config.metrics_enabled.cache_clear()
    assert config.metrics_enabled() is False


def test_metrics_namespace_default_and_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("METRICS_NAMESPACE", raising=False)
    config.metrics_namespace.cache_clear()
    assert config.metrics_namespace() == "metrics"

    monkeypatch.setenv("METRICS_NAMESPACE", "custom")
    config.metrics_namespace.cache_clear()
    assert config.metrics_namespace() == "custom"


def test_metrics_key_uses_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_NAMESPACE", "telemetry")
    config.metrics_namespace.cache_clear()
    assert config.metrics_key("events", "count") == "telemetry:events:count"
