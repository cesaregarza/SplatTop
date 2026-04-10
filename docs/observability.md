# Observability

This repo owns the metrics emitted by FastAPI and Celery. Grafana dashboards and
Prometheus alert rules live in the sibling config repo, `../SplatTopConfig`.

## Ownership Split

- App repo (`SplatTop`)
  - metric definitions: `src/shared_lib/monitoring/prometheus.py`
  - FastAPI request middleware: `src/fast_api_app/metrics.py`
  - route/task instrumentation on hot paths
- Config repo (`SplatTopConfig`)
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
- If you add a metric here, add or update the matching Grafana/Prometheus wiring in `SplatTopConfig` in the same PR set.
