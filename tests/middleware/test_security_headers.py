from typing import Any


def test_x_frame_options_header_present(
    client: Any, test_token: str
) -> None:
    response = client.get(
        "/api/ping", headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_x_content_type_options_header_present(
    client: Any, test_token: str
) -> None:
    response = client.get(
        "/api/ping", headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_strict_transport_security_header_present(
    client: Any, test_token: str
) -> None:
    response = client.get(
        "/api/ping", headers={"Authorization": f"Bearer {test_token}"}
    )
    assert "Strict-Transport-Security" in response.headers


def test_content_security_policy_header_present(
    client: Any, test_token: str
) -> None:
    response = client.get(
        "/api/ping", headers={"Authorization": f"Bearer {test_token}"}
    )
    assert "Content-Security-Policy" in response.headers


def test_security_headers_on_error_responses(client: Any) -> None:
    response = client.get("/api/nonexistent")
    assert "X-Frame-Options" in response.headers


def test_security_headers_on_multiple_requests(
    client: Any, test_token: str
) -> None:
    """Verify headers persist across multiple requests."""
    for _ in range(3):
        response = client.get(
            "/api/ping", headers={"Authorization": f"Bearer {test_token}"}
        )
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
