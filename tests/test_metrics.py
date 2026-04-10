import re
import time

import orjson

from shared_lib.constants import (
    LOOKUP_SQLITE_SNAPSHOT_META_KEY,
    RIPPLE_PLAYER_INDEX_META_KEY,
    RIPPLE_PLAYER_INDEX_PLAYER_SUMMARY_PREFIX,
)
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


def test_metrics_endpoint_includes_search_and_comp_section_metrics(
    client_factory, fake_redis
):
    generated_at_ms = int(time.time() * 1000)
    fake_redis.set(
        RIPPLE_PLAYER_INDEX_META_KEY,
        orjson.dumps(
            {
                "generated_at_ms": generated_at_ms,
                "calculated_at_ms": generated_at_ms,
                "build_version": "test-v1",
            }
        ),
    )
    fake_redis.set(
        f"{RIPPLE_PLAYER_INDEX_PLAYER_SUMMARY_PREFIX}p1",
        orjson.dumps(
            {
                "player_id": "p1",
                "display_name": "Alpha",
                "generated_at_ms": generated_at_ms,
                "history_record_count": 2,
                "history_max_records": 25,
                "viewer_can_view_results": False,
            }
        ),
    )

    with client_factory(
        env={"COMP_LEADERBOARD_ENABLED": "true"},
        redis=fake_redis,
    ) as client:
        player_resp = client.get("/api/ripple/public/player/p1/summary")
        assert player_resp.status_code == 200

        fake_redis.delete(LOOKUP_SQLITE_SNAPSHOT_META_KEY)
        search_resp = client.get("/api/search/Alpha")
        assert search_resp.status_code == 503

        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200
        body = metrics_resp.text

    assert (
        'ripple_player_section_cache_requests_total{section="summary",status="section_hit"}'
        in body
    )
    assert (
        re.search(
            r'ripple_player_section_payload_bytes_bucket\{[^}]*section="summary"[^}]*\}',
            body,
        )
        is not None
    )
    assert 'fastapi_search_requests_total{outcome="unavailable"}' in body
