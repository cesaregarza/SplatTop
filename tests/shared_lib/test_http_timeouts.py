import pytest
import requests

import shared_lib.utils as utils


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    utils.weapon_cache.clear()
    utils.badge_cache.clear()
    utils.banner_cache.clear()


def test_weapon_xref_request_has_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_get(*args, **kwargs):
        assert "timeout" in kwargs, "Request missing timeout parameter"
        raise requests.Timeout("Simulated timeout")

    monkeypatch.setattr(requests, "get", slow_get)

    with pytest.raises(requests.Timeout):
        utils.get_weapon_xref()


def test_badge_xref_request_has_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_get(*args, **kwargs):
        assert "timeout" in kwargs, "Request missing timeout parameter"
        raise requests.Timeout("Simulated timeout")

    monkeypatch.setattr(requests, "get", slow_get)

    with pytest.raises(requests.Timeout):
        utils.get_badge_xref()


def test_banner_xref_request_has_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_get(*args, **kwargs):
        assert "timeout" in kwargs, "Request missing timeout parameter"
        raise requests.Timeout("Simulated timeout")

    monkeypatch.setattr(requests, "get", slow_get)

    with pytest.raises(requests.Timeout):
        utils.get_banner_xref()
