# Ghost Blog Integration for splat.top

This document describes the Ghost CMS integration for the splat.top blog.

## Quick Start

To deploy Ghost blog to your local development environment:

```bash
# Deploy Ghost CMS
make deploy-ghost

# View logs
make ghost-logs

# Remove Ghost (if needed)
make undeploy-ghost
```

After deployment:
- **Blog**: http://localhost:8080/blog
- **Admin**: http://localhost:8080/ghost

On first visit to `/ghost`, you'll create the admin account and complete the setup wizard.

## Overview

Ghost CMS has been integrated into the splat.top Kubernetes deployment to provide a professional blogging platform with a built-in admin interface, markdown editor, and member management.

## Architecture

- **CMS**: Ghost 5 (Alpine-based Docker image)
- **Database**: SQLite (embedded, stored in persistent volume)
- **Storage**: Kubernetes PersistentVolumeClaim (1Gi)
- **Port**: 2368 (internal), exposed via service on port 80
- **Routes**: `/blog` for public blog, `/ghost` for admin interface

## Deployment

### Local Development (Kind)

**Easy Method** (using Makefile):
```bash
make deploy-ghost
```

This will deploy all Ghost components and wait for the pod to be ready.

**Manual Method** (using kubectl directly):

1. **Apply the Ghost manifests**:
   ```bash
   kubectl apply -f k8s/ghost/ghost-pvc-dev.yaml -n splattop-dev
   kubectl apply -f k8s/ghost/ghost-deployment-dev.yaml -n splattop-dev
   kubectl apply -f k8s/ghost/ghost-service-dev.yaml -n splattop-dev
   ```

2. **Apply the updated ingress**:
   ```bash
   kubectl apply -f k8s/ingress-dev.yaml
   ```

3. **Wait for Ghost to be ready**:
   ```bash
   kubectl wait --for=condition=ready pod -l app=ghost-blog -n splattop-dev --timeout=300s
   ```

4. **Access Ghost**:
   - Blog: http://localhost:8080/blog
   - Admin: http://localhost:8080/ghost

### First-time Setup

1. Navigate to http://localhost/ghost
2. Create your admin account (first user becomes the owner)
3. Complete the setup wizard
4. Start creating blog posts!

## Configuration

### Environment Variables

The Ghost deployment uses the following key environment variables:

- `NODE_ENV`: Set to "development" for local, "production" for prod
- `url`: The base URL for the blog (http://localhost/blog for dev)
- `database__client`: Database type (sqlite3 for embedded)
- `database__connection__filename`: Path to SQLite database file

### Persistent Storage

Ghost content is stored in a PersistentVolumeClaim:
- **Claim Name**: ghost-pvc
- **Storage**: 1Gi
- **Access Mode**: ReadWriteOnce
- **StorageClass**: standard (Kind default)

The PVC stores:
- SQLite database
- Uploaded images
- Theme files
- Content files

### Resource Limits

The Ghost deployment has the following resource configuration:
- **Requests**: 256Mi memory, 100m CPU
- **Limits**: 512Mi memory, 500m CPU

Adjust these in `k8s/ghost/ghost-deployment-dev.yaml` if needed.

## Using Ghost

### Admin Interface

Access the admin interface at `/ghost`:
- Create and publish blog posts
- Manage pages and posts
- Upload images
- Configure site settings
- Manage members (if enabled)
- Customize themes

### Writing Posts

Ghost supports:
- **Markdown** editor with live preview
- **Rich media** embeds (YouTube, Twitter, etc.)
- **Image galleries**
- **Code blocks** with syntax highlighting
- **Custom HTML** cards
- **Bookmarks** and **buttons**

### Themes

Ghost comes with the Casper theme by default. To customize:
1. Download a theme from https://ghost.org/marketplace/
2. Upload via Settings → Design → Change theme
3. Or mount custom themes in the deployment

## Production Considerations

For production deployment, consider these improvements:

### 1. Use MySQL Instead of SQLite

Update the deployment to use MySQL for better performance and scalability:

```yaml
env:
  - name: database__client
    value: "mysql"
  - name: database__connection__host
    value: "mysql-service"
  - name: database__connection__user
    valueFrom:
      secretKeyRef:
        name: ghost-db-secrets
        key: MYSQL_USER
  - name: database__connection__password
    valueFrom:
      secretKeyRef:
        name: ghost-db-secrets
        key: MYSQL_PASSWORD
  - name: database__connection__database
    value: "ghost"
```

### 2. Configure Production URL

Update the `url` environment variable:

```yaml
- name: url
  value: "https://splat.top/blog"
```

### 3. Enable Email

Configure mail settings for newsletters and notifications:

```yaml
- name: mail__transport
  value: "SMTP"
- name: mail__options__service
  value: "Mailgun"  # or SendGrid, SES, etc.
- name: mail__options__auth__user
  valueFrom:
    secretKeyRef:
      name: ghost-secrets
      key: MAIL_USER
- name: mail__options__auth__pass
  valueFrom:
    secretKeyRef:
      name: ghost-secrets
      key: MAIL_PASSWORD
```

### 4. Increase Storage

For production with lots of images/content:

```yaml
resources:
  requests:
    storage: 10Gi  # or more
```

### 5. Add SSL/TLS

The ingress should use cert-manager for SSL:

```yaml
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - splat.top
      secretName: splat-top-tls
```

### 6. Configure Backups

Set up automated backups of:
- Ghost content (PVC)
- Database (if using MySQL)

### 7. Set Up CDN

For better performance, configure a CDN for images:
- Use Ghost's built-in storage adapters
- Or use external storage (S3, Google Cloud Storage)

## Troubleshooting

### Ghost pod not starting

Check the logs:
```bash
kubectl logs -l app=ghost-blog
```

Common issues:
- PVC not bound: Check PVC status with `kubectl get pvc ghost-pvc`
- Resource limits: Check if cluster has enough resources
- Configuration errors: Verify environment variables

### Database corruption

If using SQLite and the database becomes corrupted:
1. Backup the PVC
2. Delete the ghost.db file
3. Restart Ghost (it will create a new database)
4. Restore from backup if needed

### Images not loading

Check:
1. PVC is properly mounted
2. Volume permissions are correct
3. Image URLs in Ghost settings

### Can't access admin

1. Verify ingress is routing `/ghost` correctly:
   ```bash
   kubectl get ingress dev-ingress -o yaml
   ```

2. Check Ghost service:
   ```bash
   kubectl get svc ghost-blog-service
   ```

3. Port-forward directly to test:
   ```bash
   kubectl port-forward svc/ghost-blog-service 2368:80
   ```
   Then access http://localhost:2368/ghost

## Customization

### Custom Themes

1. Create a ConfigMap with your theme:
   ```bash
   kubectl create configmap ghost-theme --from-file=path/to/theme
   ```

2. Mount it in the deployment:
   ```yaml
   volumeMounts:
     - name: custom-theme
       mountPath: /var/lib/ghost/content/themes/custom
   volumes:
     - name: custom-theme
       configMap:
         name: ghost-theme
   ```

### Custom Routes

Ghost supports custom routing via routes.yaml. Mount it as a ConfigMap.

### Integrations

Ghost supports:
- **Webhooks** for external integrations
- **Custom integrations** via API keys
- **Zapier** and other automation tools
- **Analytics** (Google Analytics, etc.)

## API Access

Ghost provides a powerful Content API and Admin API:

- **Content API**: Public, read-only access to published content
- **Admin API**: Full CRUD operations (requires authentication)

Generate API keys in Ghost Admin → Integrations.

## Monitoring

Add monitoring for Ghost:

1. **Prometheus metrics**: Use a Ghost Prometheus exporter
2. **Loki logs**: Configure log shipping
3. **Uptime monitoring**: Monitor `/blog` availability
4. **Database size**: Track PVC usage

## Migration from Custom Implementation

The custom FastAPI blog implementation has been removed in favor of Ghost. If you had any data:

1. Export content from the old database
2. Format as Ghost-compatible JSON
3. Import via Ghost Admin or API

## Additional Resources

- [Ghost Documentation](https://ghost.org/docs/)
- [Ghost API Reference](https://ghost.org/docs/admin-api/)
- [Ghost Themes](https://ghost.org/marketplace/)
- [Ghost Docker Image](https://hub.docker.com/_/ghost/)

## Support

For Ghost-specific issues, consult:
- Ghost Forum: https://forum.ghost.org/
- Ghost GitHub: https://github.com/TryGhost/Ghost

For deployment issues specific to splat.top, check the Kubernetes logs and ensure all manifests are applied correctly.
