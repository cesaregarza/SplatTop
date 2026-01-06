from typing import Any


def test_rate_limit_applies_to_cors_preflight(client_factory: Any) -> None:
    headers = {
        "Origin": "https://example.com",
        "Access-Control-Request-Method": "GET",
    }
    with client_factory(
        env={"API_RL_PER_SEC": "1", "API_RL_PER_MIN": "1"}
    ) as client:
        response = None
        for _ in range(3):
            response = client.options("/api/ripple", headers=headers)

        assert response is not None
        assert response.status_code == 429
