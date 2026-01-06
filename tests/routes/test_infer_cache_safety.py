import builtins
import importlib
from types import ModuleType
from typing import Any

import pytest


def _abilities_hash(abilities: dict[str, int], weapon_id: int) -> int:
    abilities_str = sorted(
        [f"{ability}:{value}" for ability, value in abilities.items() if value > 0]
    )
    abilities_str.append(f"weapon_id:{weapon_id}")
    abilities_str = ",".join(abilities_str)
    return hash(abilities_str)


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")


def _load_infer() -> ModuleType:
    return importlib.import_module("fast_api_app.routes.infer")


def test_cache_deserialization_rejects_code_injection(
    client: Any, fake_redis: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    infer_mod = _load_infer()
    abilities = {"swim_speed_up": 3}
    weapon_id = 1
    abilities_hash = _abilities_hash(abilities, weapon_id)
    fake_redis.hset(
        "splatgpt",
        field=abilities_hash,
        value="[(__import__('os').system('whoami'), 0.5)]",
    )

    monkeypatch.setattr(infer_mod, "redis_conn", fake_redis, raising=False)

    eval_called = {"called": False}

    def fake_eval(payload):
        eval_called["called"] = True
        return []

    monkeypatch.setattr(builtins, "eval", fake_eval)

    async def fake_add_to_queue(request):
        return {
            "predictions": [("main", 0.5)],
            "splatgpt_info": {"version": "test"},
            "api_version": "0.1.0",
            "inference_time": 0.1,
        }

    monkeypatch.setattr(
        infer_mod.model_queue, "add_to_queue", fake_add_to_queue, raising=False
    )

    resp = client.post(
        "/api/infer",
        json={"abilities": abilities, "weapon_id": weapon_id},
        headers={"User-Agent": "TestAgent"},
    )

    assert resp.status_code == 200
    assert eval_called["called"] is False


def test_cache_deserialization_handles_valid_data(
    client: Any, fake_redis: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    infer_mod = _load_infer()
    abilities = {"swim_speed_up": 3}
    weapon_id = 1
    abilities_hash = _abilities_hash(abilities, weapon_id)
    fake_redis.hset(
        "splatgpt",
        field=abilities_hash,
        value='[["main", 0.95]]',
    )

    monkeypatch.setattr(infer_mod, "redis_conn", fake_redis, raising=False)

    async def fail_add_to_queue(request):
        raise AssertionError("cache miss should not call model queue")

    monkeypatch.setattr(
        infer_mod.model_queue, "add_to_queue", fail_add_to_queue, raising=False
    )

    resp = client.post(
        "/api/infer",
        json={"abilities": abilities, "weapon_id": weapon_id},
        headers={"User-Agent": "TestAgent"},
    )

    assert resp.status_code == 200
    assert resp.json()["metadata"]["cache_status"] == "hit"


def test_cache_deserialization_handles_malformed_json(
    client: Any, fake_redis: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    infer_mod = _load_infer()
    abilities = {"swim_speed_up": 3}
    weapon_id = 1
    abilities_hash = _abilities_hash(abilities, weapon_id)
    fake_redis.hset(
        "splatgpt",
        field=abilities_hash,
        value="not valid {json or python",
    )

    monkeypatch.setattr(infer_mod, "redis_conn", fake_redis, raising=False)

    async def fake_add_to_queue(request):
        return {
            "predictions": [("main", 0.5)],
            "splatgpt_info": {"version": "test"},
            "api_version": "0.1.0",
            "inference_time": 0.1,
        }

    monkeypatch.setattr(
        infer_mod.model_queue, "add_to_queue", fake_add_to_queue, raising=False
    )

    resp = client.post(
        "/api/infer",
        json={"abilities": abilities, "weapon_id": weapon_id},
        headers={"User-Agent": "TestAgent"},
    )

    assert resp.status_code == 200
    assert resp.json()["metadata"]["cache_status"] == "miss"


def test_cache_deserialization_handles_none(
    client: Any, fake_redis: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    infer_mod = _load_infer()
    abilities = {"swim_speed_up": 3}
    weapon_id = 1

    monkeypatch.setattr(infer_mod, "redis_conn", fake_redis, raising=False)

    add_calls = {"count": 0}

    async def fake_add_to_queue(request):
        add_calls["count"] += 1
        return {
            "predictions": [("main", 0.5)],
            "splatgpt_info": {"version": "test"},
            "api_version": "0.1.0",
            "inference_time": 0.1,
        }

    monkeypatch.setattr(
        infer_mod.model_queue, "add_to_queue", fake_add_to_queue, raising=False
    )

    resp = client.post(
        "/api/infer",
        json={"abilities": abilities, "weapon_id": weapon_id},
        headers={"User-Agent": "TestAgent"},
    )

    assert resp.status_code == 200
    assert resp.json()["metadata"]["cache_status"] == "miss"
    assert add_calls["count"] == 1
