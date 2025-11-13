# SplatTop Helm Chart

This Helm chart deploys the SplatTop application - a Splatoon 3 competitive tracking platform.

## Components

This chart deploys the following components:

- **FastAPI Backend**: REST API and WebSocket server
- **React Frontend**: Web UI served by Nginx
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled task scheduler
- **Redis**: Cache and message broker
- **SplatNLP**: ML inference service
- **Ingress Controller**: (Optional) Bundled NGINX controller for local/dev clusters
- **Ingress**: (Optional) Route external traffic to services
- **Prometheus**: (Optional) Metrics collection and monitoring
- **Grafana**: (Optional) Metrics visualization and dashboards
- **AlertManager**: (Optional) Alert routing and management

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+ (or ArgoCD for GitOps deployment)
- A Kubernetes secret named `db-secrets` containing database credentials (or customize via `global.databaseSecretName`)
- Image pull secrets configured as `regcred` (or customize via `global.imagePullSecrets`)
- (Optional) Nginx Ingress Controller for ingress support (now bundled for dev via `ingressController.enabled`)
- (Optional) cert-manager for TLS certificate management
- (Optional) ArgoCD for GitOps continuous delivery (see `/argocd/README.md`)

## Deployment Methods

SplatTop can be deployed using two methods:

1. **Direct Helm Installation** (below) - Manual deployment using Helm CLI
2. **ArgoCD GitOps** - Automated deployment via ArgoCD (recommended for production)
   - See [ArgoCD documentation](/argocd/README.md) for GitOps setup
   - Supports multi-environment deployments
   - Automated sync with self-healing

## Installing the Chart

### Development Installation

Install with default development values:

```bash
helm install splattop ./helm/splattop
```

Or with a custom release name:

```bash
helm install my-splattop ./helm/splattop
```

For local kind clusters, use the provided overrides that point the workloads at
locally built images (after `make build` loads them into kind):

```bash
helm upgrade --install splattop-dev ./helm/splattop \
  -n splattop-dev \
  -f ./helm/splattop/values-local.yaml
```

The local overrides disable SplatNLP (to avoid large model downloads), switch all
images to the locally built tags, enable the bundled `ingress-nginx` controller,
and recreate the legacy `fast-api-app-service` and `redis` service names so the
containers can reach each other without changing their baked-in configuration.

### Production Installation

Install with production overrides:

```bash
helm install splattop ./helm/splattop -f ./helm/splattop/values-prod.yaml
```

### Custom Namespace

Install in a specific namespace:

```bash
kubectl create namespace splattop
helm install splattop ./helm/splattop -n splattop
```

## Upgrading the Chart

```bash
helm upgrade splattop ./helm/splattop -f ./helm/splattop/values-prod.yaml
```

## Uninstalling the Chart

```bash
helm uninstall splattop
```

## Configuration

The following table lists the configurable parameters and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Environment name (development/production) | `development` |
| `global.imagePullSecrets` | List of image pull secret names | `[regcred]` |
| `global.databaseSecretName` | Name of Kubernetes secret containing database credentials | `db-secrets` |

### FastAPI Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `fastapi.enabled` | Enable FastAPI deployment | `true` |
| `fastapi.replicas` | Number of replicas | `1` (dev), `2` (prod) |
| `fastapi.image.repository` | Image repository | `registry.digitalocean.com/sendouq/fast-api` |
| `fastapi.image.tag` | Image tag | `latest` |
| `fastapi.service.port` | HTTP service port | `8000` |
| `fastapi.service.websocketPort` | WebSocket service port | `8001` |
| `fastapi.service.extraServices` | Additional Service objects for compatibility (name/type/ports) | `[]` |
| `fastapi.env.COMP_LEADERBOARD_ENABLED` | Enable competition leaderboard | `false` (dev), `true` (prod) |

### React Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `react.enabled` | Enable React deployment | `true` |
| `react.replicas` | Number of replicas | `1` (dev), `2` (prod) |
| `react.image.repository` | Image repository | `registry.digitalocean.com/sendouq/react` |
| `react.image.tag` | Image tag | `latest` |
| `react.service.port` | Service port | `80` |
| `react.service.extraServices` | Additional Service objects for compatibility | `[]` |

### Celery Worker Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `celeryWorker.enabled` | Enable Celery worker deployment | `true` |
| `celeryWorker.replicas` | Number of replicas | `1` |
| `celeryWorker.image.repository` | Image repository | `registry.digitalocean.com/sendouq/celery` |

### Celery Beat Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `celeryBeat.enabled` | Enable Celery beat deployment | `true` |
| `celeryBeat.replicas` | Number of replicas | `1` |
| `celeryBeat.resources.requests.memory` | Memory request | `32Mi` |
| `celeryBeat.resources.limits.memory` | Memory limit | `64Mi` |

### Redis Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis deployment | `true` |
| `redis.replicas` | Number of replicas | `1` |
| `redis.image.repository` | Image repository | `redis` |
| `redis.service.port` | Service port | `6379` |
| `redis.service.extraServices` | Additional Service objects for compatibility | `[]` |

### SplatNLP Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `splatnlp.enabled` | Enable SplatNLP deployment | `true` |
| `splatnlp.replicas` | Number of replicas | `1` |
| `splatnlp.service.port` | Service port | `9000` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` (dev), `true` (prod) |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.tls.enabled` | Enable TLS | `false` (dev), `true` (prod) |
| `ingress.tls.secretName` | TLS secret name | `tls-secret` |

### Ingress Controller Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingressController.enabled` | Deploy the bundled `ingress-nginx` controller manifest | `false` (dev), `true` in `values-local.yaml` |
| `ingressController.manifestPath` | Path (under `helm/splattop/files/`) to render for the controller | `ingress-nginx/controller-v1.0.0.yaml` |

### Monitoring Configuration

#### Prometheus

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.prometheus.enabled` | Enable Prometheus | `false` (dev), `true` (prod) |
| `monitoring.prometheus.replicas` | Number of replicas | `1` |
| `monitoring.prometheus.image.tag` | Image tag | `v2.52.0` |
| `monitoring.prometheus.service.port` | Service port | `9090` |
| `monitoring.prometheus.configMapName` | ConfigMap containing `prometheus.yml` | `prometheus-config` |
| `monitoring.prometheus.retention` | Data retention period | `15d` |
| `monitoring.prometheus.persistence.enabled` | Enable persistent storage | `true` |
| `monitoring.prometheus.persistence.size` | Storage size | `20Gi` |
| `monitoring.prometheus.rules.enabled` | Mount alerting rules ConfigMap | `false` |
| `monitoring.prometheus.rules.configMapName` | ConfigMap containing alerting rules | `prometheus-rules` |
| `monitoring.prometheus.resources.requests.cpu` | CPU request | `250m` |
| `monitoring.prometheus.resources.requests.memory` | Memory request | `512Mi` |
| `monitoring.prometheus.resources.limits.cpu` | CPU limit | `1` |
| `monitoring.prometheus.resources.limits.memory` | Memory limit | `2Gi` |

#### Grafana

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.grafana.enabled` | Enable Grafana | `false` (dev), `true` (prod) |
| `monitoring.grafana.replicas` | Number of replicas | `1` |
| `monitoring.grafana.image.tag` | Image tag | `10.4.3` |
| `monitoring.grafana.service.port` | Service port | `80` |
| `monitoring.grafana.serverDomain` | Server domain | `""` (dev), `grafana.splat.top` (prod) |
| `monitoring.grafana.adminCredentialsSecret` | Admin credentials secret | `grafana-admin-credentials` |
| `monitoring.grafana.datasourcesConfigMapName` | ConfigMap for datasource provisioning | `grafana-datasources` |
| `monitoring.grafana.dashboardProvidersConfigMapName` | ConfigMap for dashboard providers | `grafana-dashboard-providers` |
| `monitoring.grafana.persistence.enabled` | Enable persistent storage | `true` |
| `monitoring.grafana.persistence.size` | Storage size | `5Gi` |
| `monitoring.grafana.dashboards` | List of dashboards to mount (`name`, optional `configMapName`) | `[]` (dev), see values-prod.yaml |

#### AlertManager

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.alertmanager.enabled` | Enable AlertManager | `false` (dev), `true` (prod) |
| `monitoring.alertmanager.replicas` | Number of replicas | `1` |
| `monitoring.alertmanager.image.tag` | Image tag | `v0.27.0` |
| `monitoring.alertmanager.service.port` | Service port | `9093` |
| `monitoring.alertmanager.configSecret` | Config secret name | `alertmanager-config` |

## Required Secrets

Before deploying, create a Kubernetes secret with database credentials:

```bash
kubectl create secret generic db-secrets \
  --from-literal=DB_HOST=your-db-host \
  --from-literal=DB_USER=your-db-user \
  --from-literal=DB_PASSWORD=your-db-password \
  --from-literal=DB_NAME=your-db-name \
  --from-literal=DB_PORT=5432 \
  --from-literal=RANKINGS_DB_NAME=your-rankings-db \
  --from-literal=RANKINGS_DB_SCHEMA=your-schema \
  --from-literal=API_TOKEN_PEPPER=your-api-pepper \
  --from-literal=ADMIN_TOKEN_PEPPER=your-admin-pepper \
  --from-literal=ADMIN_API_TOKENS_HASHED=your-hashed-tokens \
  --from-literal=DO_SPACES_ML_ENDPOINT=your-spaces-endpoint \
  --from-literal=DO_SPACES_ML_DIR=your-spaces-dir
```

You can also use the template from `/k8s/secrets.template` as a reference.

### Monitoring Secrets (if monitoring is enabled)

If you enable the monitoring stack, you'll need to create additional secrets:

**Grafana Admin Credentials:**
```bash
kubectl create secret generic grafana-admin-credentials \
  --from-literal=admin-user=admin \
  --from-literal=admin-password=your-secure-password
```

**AlertManager Configuration:**
```bash
kubectl create secret generic alertmanager-config \
  --from-file=alertmanager.yaml=/path/to/alertmanager-config.yaml
```

**Prometheus Configuration (if not using default):**

You'll need to create ConfigMaps for:
- `prometheus-config` - Main Prometheus configuration
- `prometheus-rules` - Prometheus alerting rules (optional)
- `grafana-datasources` - Grafana datasource configuration
- `grafana-dashboard-providers` - Grafana dashboard provider configuration
- Dashboard ConfigMaps (e.g., `grafana-dashboard-core`, `grafana-dashboard-splatgpt`, etc.)

If you already maintain these under different names, point the chart at them via
`monitoring.prometheus.configMapName`, `monitoring.prometheus.rules.configMapName`,
`monitoring.grafana.datasourcesConfigMapName`, and `monitoring.grafana.dashboardProvidersConfigMapName`
(each dashboard entry also accepts an optional `configMapName` override).

See the existing configurations in `/k8s/monitoring/` for reference templates.

## Examples

### Custom Values File

Create a `custom-values.yaml`:

```yaml
global:
  environment: staging

fastapi:
  replicas: 2
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"

ingress:
  enabled: true
  hosts:
    - host: staging.splat.top
      paths:
        - path: /api
          pathType: Prefix
          serviceName: fastapi
          servicePort: 8000
        - path: /
          pathType: Prefix
          serviceName: react
          servicePort: 80
```

Install with custom values:

```bash
helm install splattop ./helm/splattop -f custom-values.yaml
```

### Disable Components

To disable specific components:

```bash
helm install splattop ./helm/splattop \
  --set splatnlp.enabled=false \
  --set celeryBeat.enabled=false
```

## Validation

### Dry Run

Test the installation without actually deploying:

```bash
helm install splattop ./helm/splattop --dry-run --debug
```

### Template Rendering

View the rendered templates:

```bash
helm template splattop ./helm/splattop -f ./helm/splattop/values-prod.yaml
```

### Lint Chart

Validate the chart for issues:

```bash
helm lint ./helm/splattop
```

## Troubleshooting

### Check Deployment Status

```bash
helm status splattop
kubectl get pods
kubectl get services
```

### View Logs

```bash
# FastAPI logs
kubectl logs -l app.kubernetes.io/component=fastapi

# React logs
kubectl logs -l app.kubernetes.io/component=react

# Celery worker logs
kubectl logs -l app.kubernetes.io/component=celery-worker
```

### Common Issues

1. **Image Pull Errors**: Ensure `regcred` secret exists with correct registry credentials
2. **Database Connection Errors**: Verify `db-secrets` contains correct database credentials
3. **Ingress Not Working**: Ensure nginx-ingress-controller is installed and running

## Development

### Project Structure

```
helm/splattop/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values (development)
├── values-prod.yaml        # Production overrides
├── templates/              # Kubernetes manifests
│   ├── _helpers.tpl        # Template helpers
│   ├── fastapi-deployment.yaml
│   ├── fastapi-service.yaml
│   ├── react-deployment.yaml
│   ├── react-service.yaml
│   ├── celery-worker-deployment.yaml
│   ├── celery-worker-service.yaml
│   ├── celery-beat-deployment.yaml
│   ├── redis-deployment.yaml
│   ├── redis-service.yaml
│   ├── splatnlp-deployment.yaml
│   ├── splatnlp-service.yaml
│   ├── ingress.yaml
│   └── certificate.yaml
└── README.md               # This file
```

## GitOps Deployment with ArgoCD

For production environments, we recommend using ArgoCD for GitOps-based deployment:

### Why ArgoCD?

- **Declarative GitOps**: Git as the single source of truth
- **Automated Sync**: Automatic deployment of changes from Git
- **Self-Healing**: Automatically corrects drift from desired state
- **Multi-Environment**: Manage dev, staging, and production from one place
- **Rollback**: Easy rollback to previous versions
- **RBAC**: Fine-grained access control per environment

### Quick Start

1. **Install ArgoCD** (if not already installed):
   ```bash
   kubectl create namespace argocd
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
   ```

2. **Deploy SplatTop Project**:
   ```bash
   kubectl apply -f argocd/projects/splattop-project.yaml
   ```

3. **Deploy Application** (choose one):
   ```bash
   # Single environment
   kubectl apply -f argocd/applications/splattop-prod.yaml

   # Or use ApplicationSet for all environments
   kubectl apply -f argocd/applications/splattop-applicationset.yaml
   ```

4. **Access ArgoCD UI**:
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   # Get password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

For complete ArgoCD setup and usage, see [ArgoCD Documentation](/argocd/README.md).

## Support

For issues and questions:
- GitHub: https://github.com/cesaregarza/SplatTop
- Website: https://splat.top
