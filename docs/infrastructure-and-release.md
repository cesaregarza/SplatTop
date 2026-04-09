# Infrastructure and Release Guide

SplatTop production is split across two repositories:

- `SplatTop` (this repo): application code, Dockerfiles, tests, and GitHub Actions that build/publish images
- `SplatTopConfig`: Helm chart values, Argo CD Applications, encrypted secrets, and the desired production state

This document is the practical map of how those pieces fit together.

## Repo Responsibilities

### `SplatTop`

Owns:

- FastAPI, Celery, React, and shared Python/JS code
- Docker image build definitions in `dockerfiles/`
- CI/CD workflows in `.github/workflows/`
- local kind manifests under `k8s/`
- helper scripts for secret sync and release automation

Does **not** own the live production manifests. A merge to `main` here publishes images and proposes config updates, but production still reads desired state from `SplatTopConfig`.

### `SplatTopConfig`

Owns:

- Helm chart values for development and production
- Argo CD `Application` resources
- encrypted production secrets
- component tag metadata (`automation/component-tags.json`)
- the production image tags consumed by Argo/Helm

Production tracks `SplatTopConfig/main`, not `SplatTop/main`.

## Production Topology

Production runs on DigitalOcean Kubernetes and is managed through Argo CD.

Core workloads:

- `splattop-prod-fastapi`
- `splattop-prod-react`
- `splattop-prod-celery-worker`
- `splattop-prod-celery-beat`
- `splattop-prod-redis`
- `splattop-prod-splatnlp`

Important namespace notes:

- the Argo `Application` lives in namespace `argocd`
- the actual SplatTop production workloads currently run in namespace `default`

The Argo app name is:

- `splattop-prod`

## Release Flow

### Normal application release

1. Merge app changes to `SplatTop/main`.
2. `.github/workflows/update_k8s_deployment.yaml` detects changed components.
3. GitHub Actions builds only the changed images and publishes:
   - `registry.digitalocean.com/sendouq/fast-api:vX.Y.Z`
   - `registry.digitalocean.com/sendouq/celery:vX.Y.Z`
   - `registry.digitalocean.com/sendouq/react:vX.Y.Z`
4. The workflow creates or updates the GitHub release tag and emits `component-tags.json`.
5. The workflow opens a PR against `SplatTopConfig` to bump the affected Helm image tags and refresh `automation/component-tags.json`.
6. After `SplatTopConfig/main` is updated, Argo can sync `splattop-prod` to roll the new version.

### Secret sync flow

Competition auth secrets follow a different path:

1. Update `secrets/competition-admins/comp-auth-secrets.enc.yaml` in `SplatTop`.
2. `.github/workflows/sync_competition_admins_to_config.yml` copies that state into `SplatTopConfig`.
3. The workflow opens a PR in `SplatTopConfig`.
4. After that PR merges, Argo sync applies the new secret wiring.

## What Changed In The Lookup Snapshot Refactor

Historically, FastAPI owned the local SQLite lookup refreshers for:

- aliases
- weapon leaderboard peak data
- season results

That was simple, but it meant request-serving FastAPI pods also performed heavyweight rebuild work. Under load, that created avoidable latency spikes.

The current production path is:

1. Celery tasks build a combined lookup SQLite snapshot.
2. The snapshot is compressed and published to Redis.
3. FastAPI reads the published snapshot into a local file-backed read-only SQLite database.
4. Search and weapon leaderboard endpoints query that local snapshot.

Relevant code:

- snapshot build task: `src/celery_app/tasks/sqlite_lookup_snapshot.py`
- schedule registration: `src/celery_app/beat.py`
- FastAPI snapshot loader: `src/fast_api_app/sqlite_lookup_store.py`
- consumers:
  - `src/fast_api_app/routes/search.py`
  - `src/fast_api_app/routes/weapon_leaderboard.py`

Operational consequence:

- FastAPI should be treated as read-only for those lookup datasets in production.
- If the lookup snapshot is missing after a rollout, trigger `tasks.refresh_lookup_sqlite_snapshot` once from Celery and confirm `lookup_sqlite:meta` exists in Redis.

## Operational Checklist

### Before syncing production

- confirm the app workflow on `SplatTop` finished successfully
- confirm the expected release tag exists on GitHub
- confirm `SplatTopConfig/main` points the correct components at that tag

### After syncing production

- check Argo:
  - `kubectl --context do-nyc3-k8s-nyc3-splattop -n argocd get application splattop-prod`
- check rollout status:
  - `kubectl --context do-nyc3-k8s-nyc3-splattop -n default rollout status deployment/splattop-prod-fastapi`
  - `kubectl --context do-nyc3-k8s-nyc3-splattop -n default rollout status deployment/splattop-prod-celery-worker`
  - `kubectl --context do-nyc3-k8s-nyc3-splattop -n default rollout status deployment/splattop-prod-celery-beat`
- confirm deployed images:
  - `kubectl --context do-nyc3-k8s-nyc3-splattop -n default get deploy splattop-prod-fastapi splattop-prod-celery-worker splattop-prod-celery-beat -o jsonpath='{range .items[*]}{.metadata.name}{\" => \"}{range .spec.template.spec.containers[*]}{.image}{\" \"}{end}{\"\\n\"}{end}'`

### Lookup snapshot sanity checks

- confirm Redis metadata:
  - `kubectl --context do-nyc3-k8s-nyc3-splattop -n default exec deploy/splattop-prod-redis -- redis-cli GET lookup_sqlite:meta`
- if needed, warm the snapshot explicitly:
  - `kubectl --context do-nyc3-k8s-nyc3-splattop -n default exec deploy/splattop-prod-celery-worker -- celery -A celery_app.app call tasks.refresh_lookup_sqlite_snapshot`

## Local Development Notes

The local kind path still lives in this repo under `k8s/`, but production Helm/Argo manifests are in `SplatTopConfig`.

For local work:

- use `.env` for manual service startup
- use `k8s/secrets.dev.enc.yaml` for kind/Helm-based local development
- keep a local clone of `../SplatTopConfig` available if you need to diff or test production Helm values

## When To Update This Doc

Update this file when any of these change:

- the app/config repo boundary
- the production release workflow
- Argo application names or namespaces
- the ownership of background refresh work between FastAPI and Celery
- the manual post-deploy checks required for production safety
