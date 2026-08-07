from shared_lib.constants import _redis_port_from_env


def test_redis_port_uses_kubernetes_service_port(monkeypatch):
    monkeypatch.delenv("SPLATTOP_REDIS_PORT", raising=False)
    monkeypatch.setenv("REDIS_SERVICE_PORT", "6379")
    monkeypatch.setenv("REDIS_PORT", "tcp://10.245.248.113:6379")

    assert _redis_port_from_env() == 6379


def test_redis_port_accepts_kubernetes_service_url_fallback(monkeypatch):
    monkeypatch.delenv("SPLATTOP_REDIS_PORT", raising=False)
    monkeypatch.delenv("REDIS_SERVICE_PORT", raising=False)
    monkeypatch.setenv("REDIS_PORT", "tcp://10.245.248.113:6380")

    assert _redis_port_from_env() == 6380


def test_numeric_legacy_port_overrides_kubernetes_service_port(monkeypatch):
    monkeypatch.delenv("SPLATTOP_REDIS_PORT", raising=False)
    monkeypatch.setenv("REDIS_SERVICE_PORT", "6379")
    monkeypatch.setenv("REDIS_PORT", "6380")

    assert _redis_port_from_env() == 6380
