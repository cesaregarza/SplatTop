# SplatTop

A platform showcasing the Top 500 players in Splatoon 3, with historical rankings, analytics, and machine learning inference. SplatTop consists of:
  - A React frontend served by Nginx
  - A FastAPI backend running under Uvicorn (via Gunicorn)
  - Redis for caching, message brokering, and PubSub
  - Celery workers for background processing
  - Celery Beat for scheduled tasks
  - A machine learning inference service (SplatGPT)
  - An Nginx Ingress controller
  - Cert-Manager for SSL/TLS certificates (production only)

Deployment is handled via Kubernetes (DigitalOcean Kubernetes Service in production), with continuous integration and deployment via GitHub Actions. Local development can be done using Docker & kind or by running components individually.

## Prerequisites

- Docker & kind (`kubectl`) for Kubernetes-based local development
- Python 3.10+ & Poetry for backend dependencies and scripts
- Node.js & npm for frontend development
- (Optional) Access to a `secrets.yaml` or a local `.env` file containing database credentials and ML storage settings

We welcome contributions for localizations! If you are interested in helping translate SplatTop into other languages, please refer to the [Contributing Localizations](LOCALIZING.md) section.

## Table of Contents

- [Installation](#installation)
  - [Local Development](#local-development)
  - [Secrets Configuration](#secrets-configuration)
- [Architecture](#architecture)
    - [Frontend Pod](#frontend-pod)
    - [Backend Pod](#backend-pod)
    - [Cache/Message Broker/PubSub Pod](#cachemessage-broker-pubsub-pod)
    - [Workers Pod](#workers-pod)
    - [Task Scheduler Pod](#task-scheduler-pod)
    - [Ingress Controller Pod](#ingress-controller-pod)
    - [Cert-Manager Pod (Production Only)](#cert-manager-pod-production-only)
- [Contributing](#contributing)
- [Contributing Localizations](LOCALIZING.md)
- [License](#license)
- [API Authentication & Tokens](#api-authentication--tokens)
  - [Admin Token Management Endpoints](#admin-token-management-endpoints)
  - [Using API Tokens](#using-api-tokens)
  - [Rate Limiting](#rate-limiting)
  - [Usage Logging & Flush](#usage-logging--flush)
  - [Proxy Headers & Client IP](#proxy-headers--client-ip)
  - [Deployment/Migration Notes](#deploymentmigration-notes)

## Installation

### Local Development (Manual)

You can run SplatTop locally without Kubernetes by starting each component manually:

1. **Clone the Repository**:
   ```sh
   git clone https://github.com/cesaregarza/SplatTop.git
   cd SplatTop
   ```

2. **Environment Variables**: Copy the example and set credentials:
   ```sh
   cp .env.example .env
   # Edit .env to set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DEV_MODE=1
   ```

3. **Install Dependencies**:
   ```sh
   poetry install    # Backend and scripts
   cd src/react_app && npm install   # Frontend dependencies
   ```

4. **Start Redis**:
   ```sh
   docker run -d --name redis -p 6379:6379 redis:6
   ```

5. **Start Celery Services**:
   ```sh
   # Worker
   poetry run celery -A src.celery_app.app:celery worker --loglevel=info
   # Scheduler (Beat)
   poetry run celery -A src.celery_app.beat:celery beat --loglevel=info
   ```

6. **Run Backend**:
   ```sh
   poetry run uvicorn fast_api_app.app:app --reload --host 0.0.0.0 --port 5000 --app-dir src
   ```

7. **Run Frontend**:
   ```sh
   cd src/react_app
   npm start    # Opens http://localhost:3000 with hot-reload
   ```

8. **(Optional) ML Inference Service**:
   If you have access to the SplatGPT Docker image (`splatnlp:latest`), run:
   ```sh
   docker run -d --name splatnlp \
     -e ENV=development \
     -e DO_SPACES_ML_ENDPOINT=... \
     -e DO_SPACES_ML_DIR=... \
     -p 9000:9000 splatnlp:latest
   ```

### Local Development with Kubernetes (kind)

Alternatively, you can use Kubernetes (kind) and Makefile targets for a K8s-based workflow:

```sh
# Create a local kind cluster
kind create cluster --config k8s/kind-config.yaml
# Build images and load into kind
make build
# Deploy all components for development
make deploy-dev
``` 
Frontend: http://localhost:3000 (hot-reload) or http://localhost:4000 (prod build)
Backend API: http://localhost:5000
Ingress (pre-prod): http://localhost:8080

> Helm preview: Set `USE_HELM=1` to have `make deploy-dev` install FastAPI, React, Redis, Celery worker/beat, and SplatGPT through the new chart (`helm/splattop`). You can inspect the rendered manifests with `make helm-template-dev` before enabling it.


### Secrets Configuration

### Secrets Configuration

Sensitive settings (database credentials, ML storage endpoints) should be provided via environment variables in `.env`, or via `secrets.yaml` when deploying on Kubernetes.

1. **Local `.env`**:
   - Copy `.env.example` to `.env` and fill in DB and other service credentials.

2. **Kubernetes `secrets.yaml`**:
   - For production or K8s deployments, create a `k8s/secrets.yaml` containing the same keys as your `.env` (DB_* vars and ML settings).
   - Apply with: `kubectl apply -f k8s/secrets.yaml`.

## Architecture

### Frontend Pod
The frontend pod hosts the React application on Nginx. It serves the user interface of SplatTop, enabling users to interact with the website and view the Top 500 players and their ranking history. This pod communicates exclusively with the backend pod to fetch data and update the UI based on user actions, and it cannot access the rest of the Kubernetes cluster. While currently written in JavaScript and JSX, a migration to TypeScript and TSX is planned for the near future.

### Backend Pod
The backend pod runs a FastAPI application hosted on Gunicorn with Uvicorn workers. It handles API requests from the frontend, processes data, communicates with Redis and the database, and exposes websocket endpoints for real-time updates.

### Database
Persistent player and leaderboard data is stored in PostgreSQL. Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME). For local caching and development, SQLite is used for read-only or non-critical data stores.

### Cache/Message Broker/PubSub Pod
The Redis pod functions as a cache, message broker, and PubSub system. Celery workers use Redis to queue tasks and store results. The backend caches frequently accessed leaderboard snapshots in Redis. Redis PubSub channels are used for real-time player detail updates.

### Workers Pod
The workers pod runs Celery workers that handle asynchronous tasks such as:
  - Pulling and updating leaderboard data
  - Fetching weapon info and aliases
  - Computing analytics (Lorenz curves, Gini coefficients, skill offsets)
  - Populating Redis caches and database tables

### Inference Service Pod
The machine learning inference service (SplatGPT) provides loadout recommendations via a REST API on port 9000. It can be run as a separate Docker image (`splatnlp:latest`) and communicates with the backend or external storage (e.g., DigitalOcean Spaces) to load models and data.

### Task Scheduler Pod
The task scheduler pod runs Celery Beat, which schedules periodic tasks (e.g., data pulls, analytics updates) for the Celery workers according to `src/celery_app/beat.py` schedules.

### Ingress Controller Pod
The ingress controller pod uses Nginx to manage incoming traffic to the Kubernetes cluster. It routes requests to the appropriate services based on predefined rules, ensuring that users can access the frontend and backend services. This is not used in the `-dev` environment, as the frontend and backend communicate directly with each other.

### Cert-Manager Pod (Production Only)
The cert-manager pod is responsible for managing SSL/TLS certificates using Let's Encrypt. This pod is only deployed in the production environment to ensure secure communication between users and the SplatTop website and is completely isolated from the rest of the system.

## Contributing

Contributions are welcome, but I maintain high standards for code quality and maintainability. A CONTRIBUTING.md file will be created in the future, but for now, please reach out via a GitHub Issue to discuss potential contributions. I am open to all ideas but am selective about what code is merged into the project. Feedback and suggestions are always welcome, so please do not hesitate to reach out.



## License

This project is licensed under GPL-3.0. Please refer to the [LICENSE](LICENSE) file for more information.

## API Authentication & Tokens

SplatTop uses high-entropy bearer tokens to protect selected API endpoints. Tokens are minted and managed via admin endpoints and validated against Redis-backed metadata. Token hashing uses SHA-256 with a server-side pepper for lookup/storage.

Environment variables
- `API_TOKEN_PEPPER`: Required for hashing API tokens.
- `ADMIN_TOKEN_PEPPER` (optional): Pepper for admin tokens (defaults to `API_TOKEN_PEPPER`).
- `ADMIN_API_TOKENS_HASHED`: Comma-separated or JSON array of SHA-256(`pepper` + `token`) hashes for admin access.
- `API_TOKEN_ALLOWED_SCOPES` (optional): Comma-separated allowlist of valid scopes.
- `ADMIN_MAX_API_TOKENS` (optional, default 1000): Cap on minted tokens.

### Admin Token Management Endpoints

Base path: `/api/admin/tokens` (requires an admin bearer token in headers; see below).

- Mint a token
  - POST `/api/admin/tokens`
  - Body:
    ```json
    { "name": "ServiceName", "note": "optional", "scopes": ["ripple.read"], "expires_at_ms": 0 }
    ```
  - Response includes the full bearer token in the `token` field: `rpl_<uuid>_<secret>`.

- List tokens
  - GET `/api/admin/tokens`

- Revoke a token
  - DELETE `/api/admin/tokens/{token_id}`

Headers for admin endpoints
- `Authorization: Bearer <ADMIN_TOKEN>` or `X-Admin-Token: <ADMIN_TOKEN>`
- The server hashes the presented admin token with the configured pepper and compares against `ADMIN_API_TOKENS_HASHED`.

CI note for admin tokens
- The workflow `.github/workflows/update_k8s_deployment.yaml` computes `ADMIN_API_TOKENS_HASHED` from `ADMIN_API_TOKENS` using Python. It accepts JSON arrays, newline-delimited, or comma-separated token lists and fails fast if the pepper is missing.

### Using API Tokens

Send your minted token with either header:
- `Authorization: Bearer rpl_<uuid>_<secret>`
- `X-API-Token: rpl_<uuid>_<secret>`

Example curl
```sh
curl -H "Authorization: Bearer rpl_..." \
     http://localhost:5000/api/ripple/leaderboard
```

Scopes
- Example required scope: `ripple.read` for ripple endpoints.
- If a token has empty scopes, it defaults to full access for backward compatibility. Define scopes to restrict access.

### Rate Limiting

Simple fixed-window limits are enforced per-token or per-IP for `/api/*` (excluding `/api/admin/*`).

Environment variables
- `API_RL_PER_SEC` (default 10)
- `API_RL_PER_MIN` (default 120)
- `API_RL_FAIL_OPEN` (default `false`): If `true`, requests pass when Redis is unavailable; otherwise responses are 429.

Response on limit: `429 { "detail": "Rate limit exceeded" }`

### Usage Logging & Flush

All non-admin `/api/*` requests are enqueued to Redis for usage analytics and periodically flushed to PostgreSQL by Celery.

Redis keys
- Queue: `api:usage:queue`
- Processing: `api:usage:queue:processing`
- Lock: `api:usage:flush:lock`

Environment variables
- `API_USAGE_FLUSH_BATCH` (default 1000): Max items to move per flush run.
- `API_USAGE_MAX_ATTEMPTS` (default 5): Max requeue attempts before DLQ.
- `API_USAGE_LOCK_TTL` (default 55): Lock TTL seconds to prevent overlap.
- `API_USAGE_RECOVER_LIMIT` (default 1000): Max orphaned items recovered per run.
- `API_USAGE_FLUSH_MINUTE` (default `*`): Minute field for Celery Beat cron.

### Proxy Headers & Client IP

Client IP resolution is conservative by default; proxy headers are ignored unless explicitly enabled.

Environment variable
- `TRUST_PROXY_HEADERS` (set to `true`/`1` to enable): Only enable when your deployment runs behind a trusted proxy that sets `X-Forwarded-For`/`X-Real-IP` correctly.

### Deployment/Migration Notes

1. Configure secrets:
   - Set `API_TOKEN_PEPPER` (high entropy).
   - Set `ADMIN_API_TOKENS` (plaintext) in CI; the workflow produces `ADMIN_API_TOKENS_HASHED` for the cluster from the pepper and tokens.
2. Ensure database schema exists (managed externally):
   - `auth.api_tokens` and `auth.api_token_usage` tables with appropriate indexes (e.g., `api_token_usage(token_id, ts)` for analytics).
3. Deploy Redis (broker + cache) and Celery Beat/Workers.
4. Tune rate-limits and flush cadence via env vars as above.
