# Observability

This repo owns the metrics emitted by FastAPI and Celery. Grafana dashboards and
Prometheus alert rules live in the sibling config repo, `../GarzAICluster`.

## Ownership Split

- App repo (`SplatTop`)
  - metric definitions: `src/shared_lib/monitoring/prometheus.py`
  - FastAPI request middleware: `src/fast_api_app/metrics.py`
  - route/task instrumentation on hot paths
- Config repo (`GarzAICluster`)
  - dashboards: `helm/splattop/files/grafana/dashboards/`
  - alert rules: `helm/splattop/templates/monitoring-prometheus-rules-configmap.yaml`
  - production dashboard mounting: `helm/splattop/values-prod.yaml`

## Hot Signals

These are the first metrics to check when the site feels slow.

- Lookup snapshots
  - `lookup_sqlite_snapshot_last_success_timestamp_seconds`
  - `lookup_sqlite_snapshot_events_total`
  - `lookup_sqlite_snapshot_bytes`
- Main `splat.top/player/{id}`
  - `player_detail_pipeline_duration_seconds`
  - `player_detail_rows`
  - `player_detail_payload_bytes`
- Competition `comp.splat.top/u/{id}`
  - route latency via `fastapi_request_duration_seconds{path=...}`
  - `ripple_player_section_cache_requests_total`
  - `ripple_player_section_resolve_seconds`
  - `ripple_player_section_payload_bytes`
- Search
  - `fastapi_request_duration_seconds{path="/api/search/{query}"}`
  - `fastapi_search_duration_seconds`
  - `fastapi_search_requests_total`
- Celery worker memory
  - `celery_task_rss_before_bytes{task=...}`
  - `celery_task_rss_after_bytes{task=...}`
  - `celery_task_rss_delta_bytes{task=...}`
  - `celery_task_process_rss_high_water_bytes{task=...}`

Celery memory samples are the latest completed sample for each task name. RSS is
the worker process's resident set size read immediately before and after the
task, so the delta may be negative and is not unique allocation. The high-water
metric is the worker process lifetime `VmHWM` observed at completion; it is not
the task's peak RSS. Values are best effort: missing or malformed `/proc` and
Redis data are omitted, and task IDs are never exported as labels.

To compare the latest completed tasks in Prometheus, use
`sort_desc(celery_task_rss_after_bytes / 1024 / 1024)` for process RSS in MiB,
and `sort_desc(celery_task_rss_delta_bytes / 1024 / 1024)` for the change across
each task. Check `time() - celery_task_last_finished_timestamp_seconds` for
sample age. These are individual completion samples, not averages or total
worker memory: successive samples can come from different child processes.

## Dashboard Intent

`Hot Paths & Snapshots` is meant to answer four questions quickly:

1. Is the lookup snapshot fresh enough for search and lookup-backed endpoints?
2. Is the main player page slow because of DB rows, payload size, or pipeline time?
3. Is the public competition player path slow because of summary/history/results latency?
4. Are competition player section caches hitting their dedicated keys or falling back?

## Alert Intent

- `LookupSQLiteSnapshotStale`
  - warns when the lookup snapshot has not published a successful build for 45 minutes
- `CompetitionPlayerSummaryLatencyHigh`
  - warns when the public competition summary path stays above 750ms P95 for 15 minutes

## Guardrails

- Do not add high-cardinality labels like `player_id`, Discord ID, raw search query, or tournament ID.
- Prefer route templates, section names, outcomes, and cache statuses as labels.
- If you add a metric here, add or update the matching Grafana/Prometheus wiring in `GarzAICluster` in the same PR set.

For memory pressure, use the before/after delta to identify tasks associated
with growth and use the process high-water metric as historical context for
worker lifetime pressure. Prefer conservative child recycling when current
post-task RSS remains elevated across tasks; HWM remains elevated after a peak
and should not by itself trigger recycling. Tune recycling in the
deployment/config repository after observing sustained behavior rather than
changing live worker thresholds from this instrumentation change.
