import threading
from typing import Any

import fast_api_app.routes.admin_tokens as admin_mod
import pytest


def test_concurrent_token_minting_respects_limit(
    client: Any,
    override_admin: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_MAX_API_TOKENS", "5")

    barrier = threading.Barrier(10)

    def race_scard(key: str) -> int:
        barrier.wait()
        return 0

    monkeypatch.setattr(admin_mod, "_safe_scard", race_scard)

    results = []

    def mint(index: int) -> None:
        response = client.post(
            "/api/admin/tokens", json={"name": f"token-{index}"}
        )
        results.append(response.status_code)

    threads = [threading.Thread(target=mint, args=(i,)) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(200) <= 5
