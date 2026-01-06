import importlib
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

    def hset(self, key, field=None, value=None, mapping=None, **kwargs):
        if mapping is not None and not isinstance(mapping, dict):
            raise TypeError("mapping must be a dict if provided")
        if kwargs:
            mapping = {**(mapping or {}), **kwargs}
        self._ops.append(("hset", key, field, value, mapping))
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
                _, key, field, value, mapping = op
                self._store._hashes.setdefault(key, {})
                if mapping:
                    for k, v in mapping.items():
                        self._store._hashes[key][k] = v
                if field is not None:
                    self._store._hashes[key][field] = value
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
            elif name == "hdel":
                _, key, fields = op
                out.append(self._store.hdel(key, *fields))
            elif name == "hincrby":
                _, key, field, amount = op
                out.append(self._store.hincrby(key, field, amount))
            elif name == "hincrbyfloat":
                _, key, field, amount = op
                out.append(self._store.hincrbyfloat(key, field, amount))
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

    def set(self, key, val, nx=False, ex=None, px=None):
        if nx and key in self._kv:
            return False
        self._kv[key] = val
        return True

    def setex(self, key, ttl, value):
        self._kv[key] = value
        return True

    def delete(self, key):
        self._kv.pop(key, None)
        self._hashes.pop(key, None)
        self._lists.pop(key, None)
        self._sets.pop(key, None)

    # Hash ops
    def hgetall(self, key):
        return self._hashes.get(key, {}).copy()

    def hset(self, key, field=None, value=None, mapping=None, **kwargs):
        self._hashes.setdefault(key, {})
        if mapping is not None:
            if not isinstance(mapping, dict):
                raise TypeError("mapping must be a dict if provided")
            self._hashes[key].update(mapping)
        if kwargs:
            self._hashes[key].update(kwargs)
        if field is not None:
            self._hashes[key][field] = value
        return 1

    def hget(self, key, field):
        return self._hashes.get(key, {}).get(field)

    def hdel(self, key, *fields):
        if not fields:
            return 0
        removed = 0
        if key in self._hashes:
            store = self._hashes[key]
            for field in fields:
                if field in store:
                    del store[field]
                    removed += 1
            if not store:
                del self._hashes[key]
        return removed

    def hincrby(self, key, field, amount=1):
        self._hashes.setdefault(key, {})
        current = int(self._hashes[key].get(field, 0))
        current += int(amount)
        self._hashes[key][field] = str(current)
        return current

    def hincrbyfloat(self, key, field, amount=1.0):
        self._hashes.setdefault(key, {})
        current = float(self._hashes[key].get(field, 0))
        current += float(amount)
        self._hashes[key][field] = str(current)
        return current

    # List ops used by usage middleware
    def rpush(self, key, value):
        self._lists.setdefault(key, [])
        self._lists[key].append(value)

    def lpush(self, key, value):
        self._lists.setdefault(key, [])
        self._lists[key].insert(0, value)

    def rpop(self, key):
        lst = self._lists.get(key, [])
        if not lst:
            return None
        return lst.pop()

    def rpoplpush(self, src, dest):
        item = self.rpop(src)
        if item is None:
            return None
        self.lpush(dest, item)
        return item

    def lrem(self, key, count, value):
        lst = list(self._lists.get(key, []))
        removed = 0
        if count == 0:
            new_list = [item for item in lst if item != value]
            removed = len(lst) - len(new_list)
            self._lists[key] = new_list
            return removed
        if count > 0:
            new_list = []
            for item in lst:
                if item == value and removed < count:
                    removed += 1
                    continue
                new_list.append(item)
            self._lists[key] = new_list
            return removed
        # count < 0 -> remove from tail
        target = -count
        new_list = []
        for item in reversed(lst):
            if item == value and removed < target:
                removed += 1
                continue
            new_list.append(item)
        new_list.reverse()
        self._lists[key] = new_list
        return removed

    def llen(self, key):
        return len(self._lists.get(key, []))

    def lindex(self, key, index):
        lst = self._lists.get(key, [])
        try:
            return lst[index]
        except IndexError:
            return None

    # Counter helpers
    def incr(self, key):
        self._counters[key] = self._counters.get(key, 0) + 1
        self._kv[key] = self._counters[key]
        return self._counters[key]

    # Pipeline for rate limiter and admin ops
    def pipeline(self, transaction: bool = True):
        return _FakePipeline(self)


@pytest.fixture()
def fake_redis():
    return FakeRedis()


# Convenience: import auth module with required DB env present
@pytest.fixture()
def auth_module(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")
    return importlib.import_module("fast_api_app.auth")


@pytest.fixture()
def token_builder(fake_redis, monkeypatch):
    """Factory to create API tokens in FakeRedis with desired scopes/expiry.

    Returns a callable: build(scopes=None, expires_at_ms=None, token_id=None, secret=None)
    -> (token, token_id, token_hash)
    """

    from shared_lib.constants import (
        API_TOKEN_HASH_MAP_PREFIX,
        API_TOKEN_META_PREFIX,
        API_TOKEN_PREFIX,
        API_TOKENS_ACTIVE_SET,
    )

    # Ensure hashing pepper
    monkeypatch.setenv("API_TOKEN_PEPPER", "testpepper")

    def _build(scopes=None, expires_at_ms=None, token_id=None, secret=None):
        from fast_api_app.auth import hash_secret

        tid = token_id or "00000000-0000-4000-8000-" + os.urandom(4).hex()
        sec = secret or "s3cr3t"
        token = f"{API_TOKEN_PREFIX}_{tid}_{sec}"
        h = hash_secret(sec, pepper="testpepper")
        fake_redis.sadd(API_TOKENS_ACTIVE_SET, h)
        fake_redis.set(f"{API_TOKEN_HASH_MAP_PREFIX}{h}", tid)
        fake_redis.hset(
            f"{API_TOKEN_META_PREFIX}{tid}",
            mapping={
                "id": tid,
                "name": "Test Token",
                "scopes": orjson.dumps(scopes or ["ripple.read"]).decode(),
                "created_at_ms": 0,
                "expires_at_ms": int(expires_at_ms or 0),
                "revoked": 0,
                "hash": h,
            },
        )
        return token, tid, h

    import orjson

    return _build


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
    import fast_api_app.connections as conn_mod
    import fast_api_app.middleware as mw_mod
    import fast_api_app.routes.admin_tokens as admin_mod
    import fast_api_app.routes.ripple_public as ripple_public_mod

    # Patch Redis in all modules that captured it at import time
    monkeypatch.setattr(app_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(auth_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(mw_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(admin_mod, "redis_conn", fake_redis, raising=False)
    monkeypatch.setattr(
        ripple_public_mod, "redis_conn", fake_redis, raising=False
    )
    monkeypatch.setattr(conn_mod, "redis_conn", fake_redis, raising=False)

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


@pytest.fixture()
def client_factory(fake_redis, monkeypatch):
    """Factory to build a fresh TestClient with env overrides to exercise middleware config.

    Usage:
        with client_factory(env={"API_RL_PER_SEC": "0", "API_RL_PER_MIN": "5"}) as c:
            c.get("/api/ping", headers=...)
    """

    class _Factory:
        def __call__(
            self, env: dict | None = None, redis: FakeRedis | None = None
        ):
            # Apply env overrides
            if env:
                for k, v in env.items():
                    if v is None:
                        monkeypatch.delenv(k, raising=False)
                    else:
                        monkeypatch.setenv(k, str(v))

            # Ensure DB env present
            monkeypatch.setenv("DB_HOST", "localhost")
            monkeypatch.setenv("DB_PORT", "5432")
            monkeypatch.setenv("DB_USER", "user")
            monkeypatch.setenv("DB_PASSWORD", "pass")
            monkeypatch.setenv("DB_NAME", "db")
            monkeypatch.setenv("RANKINGS_DB_NAME", "db")

            # Reload app-related modules to pick up new env
            for mod in [
                "fast_api_app.middleware",
                "fast_api_app.auth",
                "fast_api_app.routes.ripple",
                "fast_api_app.routes.ripple_public",
                "fast_api_app.routes.admin_tokens",
                "fast_api_app.app",
            ]:
                if mod in sys.modules:
                    importlib.reload(sys.modules[mod])
                else:
                    importlib.import_module(mod)

            app_mod = sys.modules["fast_api_app.app"]
            auth_mod = sys.modules["fast_api_app.auth"]
            mw_mod = sys.modules["fast_api_app.middleware"]
            admin_mod = sys.modules["fast_api_app.routes.admin_tokens"]
            ripple_mod = sys.modules["fast_api_app.routes.ripple"]
            ripple_public_mod = sys.modules["fast_api_app.routes.ripple_public"]

            r = redis or fake_redis
            # Patch Redis connections in reloaded modules
            monkeypatch.setattr(app_mod, "redis_conn", r, raising=False)
            monkeypatch.setattr(auth_mod, "redis_conn", r, raising=False)
            monkeypatch.setattr(mw_mod, "redis_conn", r, raising=False)
            monkeypatch.setattr(admin_mod, "redis_conn", r, raising=False)
            monkeypatch.setattr(ripple_mod, "redis_conn", r, raising=False)
            monkeypatch.setattr(
                ripple_public_mod, "redis_conn", r, raising=False
            )

            # Disable side effects
            class _DummyCelery:
                def send_task(self, *args, **kwargs):
                    return None

            monkeypatch.setattr(
                app_mod, "celery", _DummyCelery(), raising=False
            )
            monkeypatch.setattr(
                admin_mod, "celery", _DummyCelery(), raising=False
            )
            monkeypatch.setattr(
                app_mod, "start_pubsub_listener", lambda: None, raising=False
            )

            async def _noop():
                return None

            br = getattr(app_mod, "background_runner", None)
            if br is not None:
                monkeypatch.setattr(br, "run", _noop, raising=False)

            # Patch ripple DB session
            @asynccontextmanager
            async def _dummy_session():
                class _S:
                    pass

                yield _S()

            monkeypatch.setattr(
                ripple_mod,
                "rankings_async_session",
                _dummy_session,
                raising=False,
            )

            # Build a fresh client over the (reloaded) app
            return TestClient(app_mod.app)

    return _Factory()


@pytest.fixture()
def override_admin(client):
    """Override admin auth dependency for the duration of a test."""
    import fast_api_app.routes.admin_tokens as admin_mod

    client.app.dependency_overrides[
        admin_mod.require_admin_token
    ] = lambda: True
    try:
        yield
    finally:
        client.app.dependency_overrides.clear()


@pytest.fixture()
def celery_spy(monkeypatch):
    """Patch Celery send_task to a spy that records calls across app and admin modules."""

    class _Spy:
        def __init__(self):
            self.calls = []  # list of (name, args, kwargs)

        def send_task(self, name, args=None, kwargs=None):
            self.calls.append((name, list(args or []), dict(kwargs or {})))
            return None

    spy = _Spy()
    import fast_api_app.app as app_mod
    import fast_api_app.routes.admin_tokens as admin_mod

    monkeypatch.setattr(app_mod, "celery", spy, raising=False)
    monkeypatch.setattr(admin_mod, "celery", spy, raising=False)
    return spy
