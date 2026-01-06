import importlib
from typing import Any

import pytest

from shared_lib.constants import COMP_LEADERBOARD_FLAG_KEY


@pytest.fixture()
def feature_flags_module(
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    module = importlib.import_module("fast_api_app.feature_flags")
    return importlib.reload(module)


def test_is_comp_leaderboard_enabled_uses_env_default(
    feature_flags_module: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMP_LEADERBOARD_ENABLED", "false")
    monkeypatch.setattr(feature_flags_module, "_redis", lambda: fake_redis)

    assert feature_flags_module.is_comp_leaderboard_enabled() is False


def test_is_comp_leaderboard_enabled_respects_redis_override(
    feature_flags_module: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMP_LEADERBOARD_ENABLED", "false")
    monkeypatch.setattr(feature_flags_module, "_redis", lambda: fake_redis)

    feature_flags_module.set_comp_leaderboard_flag(True)
    assert feature_flags_module.is_comp_leaderboard_enabled() is True

    feature_flags_module.set_comp_leaderboard_flag(False)
    assert feature_flags_module.is_comp_leaderboard_enabled() is False


def test_set_comp_leaderboard_flag_clears_override(
    feature_flags_module: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(feature_flags_module, "_redis", lambda: fake_redis)

    feature_flags_module.set_comp_leaderboard_flag(True)
    assert fake_redis.get(COMP_LEADERBOARD_FLAG_KEY) == "1"

    feature_flags_module.set_comp_leaderboard_flag(None)
    assert fake_redis.get(COMP_LEADERBOARD_FLAG_KEY) is None


def test_invalid_redis_value_falls_back_to_env(
    feature_flags_module: Any,
    fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMP_LEADERBOARD_ENABLED", "true")
    monkeypatch.setattr(feature_flags_module, "_redis", lambda: fake_redis)
    fake_redis.set(COMP_LEADERBOARD_FLAG_KEY, "maybe")

    assert feature_flags_module.is_comp_leaderboard_enabled() is True
