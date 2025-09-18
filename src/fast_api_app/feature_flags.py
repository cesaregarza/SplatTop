from __future__ import annotations

import os
from importlib import import_module
from typing import Optional

from fast_api_app import connections
from shared_lib.constants import COMP_LEADERBOARD_FLAG_KEY

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return None


def _env_default() -> bool:
    parsed = _parse_bool(os.getenv("COMP_LEADERBOARD_ENABLED"))
    if parsed is None:
        return False
    return parsed


def _redis():
    try:
        app_module = import_module("fast_api_app.app")
        redis_override = getattr(app_module, "redis_conn", None)
        if redis_override is not None:
            return redis_override
    except Exception:
        pass
    return connections.redis_conn


def is_comp_leaderboard_enabled() -> bool:
    """Return whether the competition leaderboard is enabled."""
    override = _parse_bool(_redis().get(COMP_LEADERBOARD_FLAG_KEY))
    if override is not None:
        return override
    return _env_default()


def set_comp_leaderboard_flag(enabled: Optional[bool]) -> None:
    """Persist an override for the competition leaderboard flag.

    Passing ``None`` removes the override and falls back to the env default.
    """
    conn = _redis()
    if enabled is None:
        conn.delete(COMP_LEADERBOARD_FLAG_KEY)
        return
    conn.set(COMP_LEADERBOARD_FLAG_KEY, "1" if enabled else "0")
