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
- **Ingress**: (Optional) Route external traffic to services

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- A Kubernetes secret named `db-secrets` containing database credentials (or customize via `global.databaseSecretName`)
- Image pull secrets configured as `regcred` (or customize via `global.imagePullSecrets`)
- (Optional) Nginx Ingress Controller for ingress support
- (Optional) cert-manager for TLS certificate management

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
| `fastapi.env.COMP_LEADERBOARD_ENABLED` | Enable competition leaderboard | `false` (dev), `true` (prod) |

### React Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `react.enabled` | Enable React deployment | `true` |
| `react.replicas` | Number of replicas | `1` (dev), `2` (prod) |
| `react.image.repository` | Image repository | `registry.digitalocean.com/sendouq/react` |
| `react.image.tag` | Image tag | `latest` |
| `react.service.port` | Service port | `80` |

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

## Support

For issues and questions:
- GitHub: https://github.com/cesaregarza/SplatTop
- Website: https://splat.top
