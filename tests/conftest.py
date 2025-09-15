import os
import sys
import types
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

# Ensure src/ is importable even if pytest.ini isn't picked up
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


class _FakePipeline:
    def __init__(self, store):
        self._store = store
        self._ops = []

    def incr(self, key):
        self._ops.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self._ops.append(("expire", key, ttl))
        return self

    # Minimal set used by admin routes (kept for future tests)
    def set(self, key, val):
        self._ops.append(("set", key, val))
        return self

    def hset(self, key, mapping=None, **kwargs):
        if mapping is None:
            mapping = kwargs
        self._ops.append(("hset", key, mapping))
        return self

    def sadd(self, key, member):
        self._ops.append(("sadd", key, member))
        return self

    def srem(self, key, member):
        self._ops.append(("srem", key, member))
        return self

    def delete(self, key):
        self._ops.append(("delete", key))
        return self

    def hgetall(self, key):
        self._ops.append(("hgetall", key))
        return self

    def execute(self):
        out = []
        for op in self._ops:
            name = op[0]
            if name == "incr":
                key = op[1]
                self._store._counters[key] = (
                    self._store._counters.get(key, 0) + 1
                )
                out.append(self._store._counters[key])
            elif name == "expire":
                out.append(True)
            elif name == "set":
                _, key, val = op
                self._store._kv[key] = val
                out.append(True)
            elif name == "hset":
                _, key, mapping = op
                self._store._hashes.setdefault(key, {})
                for k, v in mapping.items():
                    self._store._hashes[key][k] = v
                out.append(True)
            elif name == "sadd":
                _, key, member = op
                self._store._sets.setdefault(key, set()).add(member)
                out.append(True)
            elif name == "srem":
                _, key, member = op
                if (
                    key in self._store._sets
                    and member in self._store._sets[key]
                ):
                    self._store._sets[key].remove(member)
                out.append(True)
            elif name == "delete":
                _, key = op
                self._store._kv.pop(key, None)
                self._store._hashes.pop(key, None)
                out.append(True)
            elif name == "hgetall":
                _, key = op
                out.append(self._store._hashes.get(key, {}).copy())
            else:
                out.append(None)
        self._ops.clear()
        return out


class FakeRedis:
    def __init__(self):
        self._sets = {}
        self._kv = {}
        self._hashes = {}
        self._lists = {}
        self._counters = {}

    # Set ops
    def sismember(self, key, member):
        return member in self._sets.get(key, set())

    def sadd(self, key, member):
        self._sets.setdefault(key, set()).add(member)

    def smembers(self, key):
        return set(self._sets.get(key, set()))

    def scard(self, key):
        return len(self._sets.get(key, set()))

    # KV ops
    def get(self, key):
        return self._kv.get(key)

    def set(self, key, val):
        self._kv[key] = val

    def delete(self, key):
        self._kv.pop(key, None)
        self._hashes.pop(key, None)
        self._lists.pop(key, None)

    # Hash ops
    def hgetall(self, key):
        return self._hashes.get(key, {}).copy()

    def hset(self, key, mapping=None, **kwargs):
        if mapping is None:
            mapping = kwargs
        self._hashes.setdefault(key, {})
        self._hashes[key].update(mapping)

    # List ops used by usage middleware
    def rpush(self, key, value):
        self._lists.setdefault(key, [])
        self._lists[key].append(value)

    # Pipeline for rate limiter and admin ops
    def pipeline(self):
        return _FakePipeline(self)


@pytest.fixture()
def fake_redis():
    return FakeRedis()


@pytest.fixture()
def test_token(fake_redis, monkeypatch):
    """Provision a valid token and set env pepper; returns full token string."""
    # Late import to avoid side effects before patching
    from shared_lib.constants import (
        API_TOKEN_HASH_MAP_PREFIX,
        API_TOKEN_META_PREFIX,
        API_TOKEN_PREFIX,
        API_TOKENS_ACTIVE_SET,
    )

    # Configure peppers for hashing
    monkeypatch.setenv("API_TOKEN_PEPPER", "testpepper")

    token_id = "00000000-0000-4000-8000-000000000001"
    secret = "s3cr3t"
    token = f"{API_TOKEN_PREFIX}_{token_id}_{secret}"

    # Compute hash via the same function to avoid drift
    from fast_api_app.auth import hash_secret

    token_hash = hash_secret(secret, pepper="testpepper")

    # Activate token in fake redis
    fake_redis.sadd(API_TOKENS_ACTIVE_SET, token_hash)
    fake_redis.set(f"{API_TOKEN_HASH_MAP_PREFIX}{token_hash}", token_id)
    fake_redis.hset(
        f"{API_TOKEN_META_PREFIX}{token_id}",
        mapping={
            "id": token_id,
            "name": "Test Token",
            "scopes": '["ripple.read"]',
            "created_at_ms": 0,
            "expires_at_ms": 0,
            "revoked": 0,
            "hash": token_hash,
        },
    )

    return token


@pytest.fixture()
def app(fake_redis, monkeypatch):
    """FastAPI app with patched Redis and disabled background startup side effects."""
    # Ensure token hashing pepper configured for tests
    monkeypatch.setenv("API_TOKEN_PEPPER", "testpepper")
    # Provide dummy DB env to avoid create_engine URL parsing errors on import
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    # Import modules
    import fast_api_app.app as app_mod
    import fast_api_app.auth as auth_mod
    import fast_api_app.middleware as mw_mod
    import fast_api_app.routes.admin_tokens as admin_mod

    # Patch Redis in all modules that captured it at import time
    monkeypatch.setattr(app_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(auth_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(mw_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(admin_mod, "redis_conn", fake_redis, raising=False)

    # Disable side effects in lifespan
    class _DummyCelery:
        def send_task(self, *args, **kwargs):
            return None

    monkeypatch.setattr(app_mod, "celery", _DummyCelery(), raising=False)
    monkeypatch.setattr(admin_mod, "celery", _DummyCelery(), raising=False)
    monkeypatch.setattr(
        app_mod, "start_pubsub_listener", lambda: None, raising=False
    )

    async def _noop():
        return None

    # background_runner.run is awaited as a task; provide a coroutine
    br = getattr(app_mod, "background_runner", None)
    if br is not None:
        monkeypatch.setattr(br, "run", _noop, raising=False)

    # Avoid real DB session creation in ripple routes by patching context manager
    import fast_api_app.routes.ripple as ripple_mod

    @asynccontextmanager
    async def _dummy_session():
        class _S:  # bare dummy session
            pass

        yield _S()

    monkeypatch.setattr(
        ripple_mod, "rankings_async_session", _dummy_session, raising=False
    )

    return app_mod.app


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c
