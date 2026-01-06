from typing import Iterable

import pytest
from starlette.requests import Request

from fast_api_app.utils import get_client_ip


def _make_request(
    headers: Iterable[tuple[bytes, bytes]],
    client_host: str = "3.3.3.3",
) -> Request:
    scope = {
        "type": "http",
        "headers": headers,
        "client": (client_host, 1234),
        "method": "GET",
        "path": "/",
    }
    return Request(scope)


def test_get_client_ip_does_not_trust_headers_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    request = _make_request([(b"x-forwarded-for", b"1.1.1.1, 2.2.2.2")])

    assert get_client_ip(request) == "3.3.3.3"


def test_get_client_ip_trusts_forwarded_for_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    request = _make_request([(b"x-forwarded-for", b"1.1.1.1, 2.2.2.2")])

    assert get_client_ip(request) == "1.1.1.1"


def test_get_client_ip_uses_real_ip_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    request = _make_request([(b"x-real-ip", b"4.4.4.4")])

    assert get_client_ip(request) == "4.4.4.4"
