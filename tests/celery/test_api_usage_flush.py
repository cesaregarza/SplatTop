import json
from contextlib import contextmanager

from shared_lib.constants import API_USAGE_PROCESSING_KEY, API_USAGE_QUEUE_KEY


def test_flush_api_usage_defers_ack_until_commit(monkeypatch, fake_redis):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "db")
    monkeypatch.setenv("RANKINGS_DB_NAME", "db")

    import celery_app.tasks.api_tokens as tasks_mod

    # Use the fake redis connection for the task module
    monkeypatch.setattr(tasks_mod, "redis_conn", fake_redis, raising=False)

    event = {
        "token_id": "tok-1",
        "ts_ms": 1700000000000,
        "ip": "127.0.0.1",
        "path": "/api/ping",
        "status": 200,
        "method": "GET",
        "ua": "pytest",
        "latency_ms": 12,
    }
    fake_redis.rpush(API_USAGE_QUEUE_KEY, json.dumps(event))

    sessions = []

    class DummySession:
        def __init__(self, commit_error: bool = False):
            self.commit_error = commit_error
            self.rollback_called = False

        def execute(self, *args, **kwargs):
            return None

        def flush(self):
            return None

        def commit(self):
            if self.commit_error:
                raise RuntimeError("boom")

        def rollback(self):
            self.rollback_called = True

    @contextmanager
    def failing_session():
        sess = DummySession(commit_error=True)
        sessions.append(sess)
        try:
            yield sess
        finally:
            pass

    monkeypatch.setattr(
        tasks_mod, "Session", lambda: failing_session(), raising=False
    )

    processed = tasks_mod.flush_api_usage(batch_size=5)
    assert processed == 0
    assert sessions[-1].rollback_called is True
    # Event should remain in processing since commit failed
    assert fake_redis.llen(API_USAGE_QUEUE_KEY) == 0
    assert fake_redis.llen(API_USAGE_PROCESSING_KEY) == 1

    # Allow the next flush to commit successfully
    @contextmanager
    def success_session():
        sess = DummySession(commit_error=False)
        sessions.append(sess)
        try:
            yield sess
        finally:
            pass

    monkeypatch.setattr(
        tasks_mod, "Session", lambda: success_session(), raising=False
    )

    processed_success = tasks_mod.flush_api_usage(batch_size=5)
    assert processed_success == 1
    assert fake_redis.llen(API_USAGE_QUEUE_KEY) == 0
    assert fake_redis.llen(API_USAGE_PROCESSING_KEY) == 0
    assert sessions[-1].rollback_called is False
