import time

from shared_lib.monitoring.constants import (
    CELERY_TASK_COUNT_HASH,
    CELERY_TASK_DURATION_HASH,
    CELERY_TASK_FAILURE_HASH,
    CELERY_TASK_INFLIGHT_SET,
    CELERY_TASK_LAST_RUN_HASH,
)


def test_metrics_endpoint_tracks_http_requests(client, test_token):
    headers = {"Authorization": f"Bearer {test_token}"}

    resp = client.get("/api/ping", headers=headers)
    assert resp.status_code == 200

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    body = metrics_resp.text

    assert (
        'fastapi_requests_total{method="GET",path="/api/ping",status="200"}'
        in body
    )
    assert "fastapi_request_duration_seconds_bucket" in body


def test_metrics_endpoint_includes_celery_state(client, fake_redis):
    task_name = "tasks.example"
    fake_redis.hincrby(CELERY_TASK_COUNT_HASH, task_name, 3)
    fake_redis.hincrbyfloat(CELERY_TASK_DURATION_HASH, task_name, 12.5)
    fake_redis.hincrby(CELERY_TASK_FAILURE_HASH, task_name, 1)
    fake_redis.hset(CELERY_TASK_LAST_RUN_HASH, task_name, str(time.time()))
    fake_redis.sadd(CELERY_TASK_INFLIGHT_SET, "foo-id")

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    body = metrics_resp.text

    assert f'celery_task_executions_total{{task="{task_name}"}} 3.0' in body
    assert f'celery_task_failures_total{{task="{task_name}"}} 1.0' in body
    assert "celery_tasks_in_progress" in body
