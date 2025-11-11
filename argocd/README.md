# SplatTop ArgoCD Configuration

This directory contains ArgoCD manifests for deploying SplatTop using GitOps continuous delivery.

## Overview

SplatTop uses ArgoCD for automated, declarative deployment management across multiple environments. This configuration supports:

- **Multi-environment deployment** (dev, staging, prod)
- **Automated sync** with self-healing for non-production
- **Manual sync** for production deployments (safety gate)
- **RBAC** for developer and admin roles
- **Helm-based** deployment using the charts in `/helm/splattop`

## Directory Structure

```
argocd/
├── applications/
│   ├── splattop-dev.yaml           # Development application
│   ├── splattop-prod.yaml          # Production application
│   └── splattop-applicationset.yaml # Multi-environment ApplicationSet
├── projects/
│   └── splattop-project.yaml       # ArgoCD project definition
└── README.md                        # This file
```

## Prerequisites

1. **ArgoCD installed** in your Kubernetes cluster:
   ```bash
   kubectl create namespace argocd
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
   ```

2. **ArgoCD CLI** (optional, for command-line operations):
   ```bash
   # macOS
   brew install argocd

   # Linux
   curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
   sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
   ```

3. **Required Secrets** in target namespaces (see `/helm/splattop/README.md` for details):
   - `db-secrets` - Database credentials
   - `regcred` - Container registry credentials
   - `grafana-admin-credentials` - Grafana admin credentials (if monitoring enabled)
   - `alertmanager-config` - AlertManager configuration (if monitoring enabled)
   - Ensure these exist in **every** namespace the application targets (`default`, `splattop-dev`, `splattop-staging`, `monitoring`). Helm expects them to be present already, so ArgoCD will fail to sync until they are created (use the `make create-secrets-*` helpers or manual `kubectl apply`).

## Deployment Options

You can deploy SplatTop using ArgoCD in three ways:

### Option 1: Individual Applications (Recommended for Getting Started)

Deploy specific environments individually:

**Development:**
```bash
kubectl apply -f argocd/projects/splattop-project.yaml
kubectl apply -f argocd/applications/splattop-dev.yaml
```

**Production:**
```bash
kubectl apply -f argocd/projects/splattop-project.yaml
kubectl apply -f argocd/applications/splattop-prod.yaml
```

### Option 2: ApplicationSet (Dev/Staging)

Deploy the non-production environments together:

```bash
kubectl apply -f argocd/projects/splattop-project.yaml
kubectl apply -f argocd/applications/splattop-applicationset.yaml
```

This creates Applications for:
- `splattop-dev` (auto-sync enabled)
- `splattop-staging` (auto-sync enabled)

> **Production is managed separately** through `argocd/applications/splattop-prod.yaml` (auto-sync enabled) so you can roll prod independently of the dev/staging ApplicationSet.

### Option 3: ArgoCD UI

1. Access ArgoCD UI:
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```

2. Login (get initial password):
   ```bash
   argocd admin initial-password -n argocd
   ```

3. Create the SplatTop project manually or via:
   ```bash
   kubectl apply -f argocd/projects/splattop-project.yaml
   ```

4. Create new application via UI:
   - Project: `splattop`
   - Repository: `https://github.com/cesaregarza/SplatTop`
   - Path: `helm/splattop`
   - Cluster: `in-cluster`
   - Namespace: `splattop-<env>` (use `default` for production in the current cluster)
   - Helm values: Select `values-prod.yaml` for production

## Configuration Details

### Application Sync Policies

#### Development (`splattop-dev.yaml`)
- **Auto-sync**: Enabled
- **Self-heal**: Enabled
- **Prune**: Enabled
- **Namespace**: `splattop-dev`
- **Values**: `values.yaml` (default development config)

#### Production (`splattop-prod.yaml`)
- **Auto-sync**: Enabled (prune + self-heal)
- **Self-heal**: Enabled
- **Prune**: Enabled
- **Namespace**: `default` (existing production workloads live in `default`; adjust if/when a dedicated namespace is created)
- **Values**: `values-prod.yaml` (production overrides)

#### ApplicationSet
- Manages the dev and staging environments only (both auto-sync with prune + self-heal)
- Apply `argocd/applications/splattop-prod.yaml` separately for production control (also auto-sync)

### Project RBAC

The `splattop` project defines two roles:

**Developer Role:**
- View all applications
- Sync dev and staging environments
- Cannot sync production
- Groups: `splattop-developers`

**Admin Role:**
- Full control over all applications
- Can sync production
- Groups: `splattop-admins`

To assign users to groups, configure ArgoCD RBAC:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.csv: |
    g, alice@example.com, splattop-developers
    g, bob@example.com, splattop-admins
```

## Managing Deployments

### Sync Application

**Via CLI:**
```bash
# Sync development
argocd app sync splattop-dev

# Sync production
argocd app sync splattop-prod

# Sync with pruning
argocd app sync splattop-prod --prune
```

**Via kubectl:**
```bash
kubectl patch app splattop-dev -n argocd --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'
```

### View Application Status

```bash
# List all applications
argocd app list

# Get detailed status
argocd app get splattop-prod

# Watch sync status
argocd app wait splattop-prod
```

### Rollback

```bash
# View history
argocd app history splattop-prod

# Rollback to specific revision
argocd app rollback splattop-prod <revision-id>
```

### Delete Application

```bash
# Delete via ArgoCD (also deletes resources)
argocd app delete splattop-dev

# Delete via kubectl
kubectl delete app splattop-dev -n argocd
```

## Health Checks

ArgoCD automatically monitors the health of all deployed resources:

- **Deployments**: Checks replica status
- **StatefulSets**: Checks ready replicas
- **Services**: Always healthy
- **Ingress**: Checks annotation status
- **Pods**: Checks Running state

Custom health checks can be added to `.argocd/` directory if needed.

## Troubleshooting

### Application OutOfSync

Check the differences:
```bash
argocd app diff splattop-prod
```

Force sync:
```bash
argocd app sync splattop-prod --force
```

### Sync Failures

View sync operation details:
```bash
argocd app get splattop-prod --show-operation
```

View application events:
```bash
kubectl describe app splattop-prod -n argocd
```

### Resource Pruning Issues

Some resources are configured to be ignored (e.g., manually created secrets). Check:
```bash
argocd app get splattop-prod --show-params
```

### Manual Intervention Required

If manual changes were made to the cluster:
```bash
# Hard refresh
argocd app get splattop-prod --hard-refresh

# Sync with replace strategy
argocd app sync splattop-prod --replace
```

## Environment-Specific Configurations

### Development
- Single replica for most services
- Monitoring stack disabled
- No ingress/TLS by default
- Auto-sync enabled

### Staging
- Same as development
- Can be used for integration testing
- Auto-sync enabled

### Production
- Multiple replicas (2x for FastAPI/React)
- Monitoring stack enabled (Prometheus, Grafana, AlertManager)
- Ingress enabled with TLS
- Manual sync recommended for safety

## Continuous Delivery Workflow

1. **Developers** push code changes to GitHub
2. **CI/CD** builds and pushes new container images with tags
3. **Update** image tags in `values-prod.yaml` or via Helm parameters
4. **ArgoCD** detects changes in the Git repository
5. **Dev/Staging** environments auto-sync immediately
6. **Production** requires manual approval and sync
7. **ArgoCD** monitors health and performs rollbacks if needed

## Best Practices

1. **Use Git branches** for environment promotion:
   - `main` → production
   - `develop` → staging
   - Feature branches → dev

2. **Pin image tags** in production (avoid `latest`)

3. **Test in staging** before promoting to production

4. **Monitor prod auto-syncs** via the Argo UI and pause automation only if you need a temporary freeze

5. **Monitor ArgoCD notifications** (configure Slack/email)

6. **Regular cleanup** of old ApplicationSet-generated apps

7. **Use sync waves** for ordered deployments (add to annotations):
   ```yaml
   metadata:
     annotations:
       argocd.argoproj.io/sync-wave: "1"
   ```

## Integration with CI/CD

The repository already contains two GitHub workflows that pair with ArgoCD:

1. **Build and Update Kubernetes Deployment** (`.github/workflows/update_k8s_deployment.yaml`)
   - Runs on every `main` push.
   - Builds and publishes the FastAPI, Celery, and React images as needed.
   - Runs `helm lint` and a full `helm upgrade --dry-run` against the prod cluster to catch template errors early.
   - Stops before applying live changes; ArgoCD remains the source of truth for production.

2. **Manual Helm Deployment** (`.github/workflows/manual_helm_deploy.yaml`)
   - `workflow_dispatch` trigger only.
   - Rebuilds images (optional) and performs the secret bootstrapping + real `helm upgrade`.
   - Use this strictly as a break-glass option if ArgoCD cannot sync.

The day-to-day flow is therefore:
1. Merge to `main` → CI publishes images and validates the chart (no live apply).
2. ArgoCD notices the Git change and auto-syncs dev/staging plus prod (prune + self-heal).
3. Keep an eye on the Argo UI to confirm the sync succeeded; if it fails, address the diff or re-run the sync.
4. If ArgoCD is unavailable, run the manual workflow to perform a one-off Helm deployment.

## Additional Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [Helm Chart README](../helm/splattop/README.md)
- [SplatTop Repository](https://github.com/cesaregarza/SplatTop)

## Support

For issues or questions:
- GitHub Issues: https://github.com/cesaregarza/SplatTop/issues
- Website: https://splat.top
