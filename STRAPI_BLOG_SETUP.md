# Strapi CMS Blog Integration for splat.top

This document describes the Strapi headless CMS integration for the splat.top blog.

## Quick Start

To deploy Strapi CMS to your local development environment:

```bash
# Deploy Strapi CMS
make deploy-strapi

# View logs
make strapi-logs

# Remove Strapi (if needed)
make undeploy-strapi
```

After deployment:
- **Strapi Admin**: http://localhost:8080/strapi/admin
- **Strapi API**: http://localhost:8080/strapi/api
- **Blog Frontend**: http://localhost:8080/blog

## Overview

Strapi is a headless CMS that provides a powerful admin panel and RESTful/GraphQL API. It integrates seamlessly with your existing React frontend and PostgreSQL database.

## Architecture

- **CMS**: Strapi 4.25.11 (Node.js-based)
- **Database**: PostgreSQL (your existing database)
- **Storage**: Uses PostgreSQL for all content
- **Port**: 1337 (internal), exposed via service on port 80
- **Routes**:
  - `/strapi/admin` - Admin interface
  - `/strapi/api/*` - REST API endpoints
  - `/blog` - React frontend consuming Strapi API

## Initial Setup

### 1. Deploy Strapi

```bash
make deploy-strapi
```

### 2. Create Admin Account

1. Navigate to http://localhost:8080/strapi/admin
2. Create your admin account (first user becomes the super admin)
3. You'll be redirected to the admin dashboard

### 3. Create Blog Content Type

Since this is a fresh Strapi installation, you need to create the "Blog Post" content type:

1. In the Strapi admin, go to **Content-Type Builder** (left sidebar)
2. Click **"Create new collection type"**
3. Enter name: `blog-post` (Display name will be "Blog Post")
4. Click **Continue**

5. Add the following fields:

   **Text Fields:**
   - `title` (Short text, required)
   - `slug` (UID, attached to title, required)
   - `excerpt` (Long text)
   - `author` (Short text)

   **Rich Text Field:**
   - `content` (Rich text - Markdown, required)

   **Date Field:**
   - `publishedAt` (datetime, enable timestamps)

   **Media Field:**
   - `featuredImage` (Single media)

6. Click **Save** and wait for Strapi to restart

### 4. Create Your First Blog Post

1. Go to **Content Manager** → **Blog Post**
2. Click **"Create new entry"**
3. Fill in the fields:
   - **Title**: Your post title
   - **Slug**: Will auto-generate from title
   - **Content**: Write in Markdown
   - **Excerpt**: Short summary
   - **Author**: Your name
   - **Featured Image**: Upload an image (optional)
4. Click **Save**
5. Click **Publish** to make it live

### 5. Configure API Permissions

By default, Strapi's API is protected. To make blog posts publicly readable:

1. Go to **Settings** → **Users & Permissions Plugin** → **Roles**
2. Click on **Public** role
3. Under **Permissions**, expand **Blog-post**
4. Check the box for **find** and **findOne**
5. Click **Save**

Now your React frontend can fetch blog posts!

## Frontend Integration

The React app automatically fetches blog posts from Strapi:

- **Blog List**: `/blog` - Displays paginated list of posts
- **Blog Post**: `/blog/:slug` - Displays individual post by slug

Blog posts are fetched from `/strapi/api/blog-posts` and rendered with:
- Featured images
- Markdown content (rendered with react-markdown)
- Author and publication date
- Pagination

## Content Creation Workflow

1. Log into Strapi admin: http://localhost:8080/strapi/admin
2. Create/edit blog posts in the Content Manager
3. Write content in Markdown format
4. Upload featured images
5. Save and Publish
6. Content immediately appears on http://localhost:8080/blog

## Strapi Features

### Content Management
- Rich text editor with Markdown support
- Media library for images
- Draft/Published workflow
- Version history
- Bulk operations

### API Features
- RESTful API out of the box
- GraphQL plugin available
- Built-in authentication
- Role-based access control
- API tokens for programmatic access

### Customization
- Custom fields and content types
- Plugins and extensions
- Webhooks for integrations
- Internationalization (i18n)
- Media providers (S3, Cloudinary, etc.)

## Configuration

### Environment Variables

Strapi is configured via environment variables in the deployment manifest:

```yaml
- name: DATABASE_CLIENT
  value: "postgres"
- name: DATABASE_HOST
  valueFrom:
    secretKeyRef:
      name: db-secrets
      key: DB_HOST
# ... other database vars
```

### Security Tokens

The deployment includes placeholder tokens that should be changed for production:

- `APP_KEYS`: Used to encrypt sessions
- `API_TOKEN_SALT`: Used for API token generation
- `ADMIN_JWT_SECRET`: JWT secret for admin authentication
- `JWT_SECRET`: JWT secret for user authentication
- `TRANSFER_TOKEN_SALT`: Used for data transfer tokens

**For production**, generate random secrets:

```bash
# Generate random secrets
openssl rand -base64 32
```

Update the deployment manifest or use Kubernetes secrets.

## Production Considerations

### 1. Use Kubernetes Secrets for Sensitive Data

Instead of hardcoded values, create a secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: strapi-secrets
type: Opaque
stringData:
  APP_KEYS: "your-secret-key-1,your-secret-key-2"
  API_TOKEN_SALT: "your-api-token-salt"
  ADMIN_JWT_SECRET: "your-admin-jwt-secret"
  JWT_SECRET: "your-jwt-secret"
  TRANSFER_TOKEN_SALT: "your-transfer-token-salt"
```

Then reference in deployment:

```yaml
- name: APP_KEYS
  valueFrom:
    secretKeyRef:
      name: strapi-secrets
      key: APP_KEYS
```

### 2. Set NODE_ENV to Production

```yaml
- name: NODE_ENV
  value: "production"
```

### 3. Configure S3/CDN for Media

For production, use external storage for uploaded images:

```yaml
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: aws-secrets
      key: AWS_ACCESS_KEY_ID
- name: AWS_ACCESS_SECRET
  valueFrom:
    secretKeyRef:
      name: aws-secrets
      key: AWS_ACCESS_SECRET
- name: AWS_REGION
  value: "us-east-1"
- name: AWS_BUCKET
  value: "splattop-strapi-media"
```

Then install the AWS S3 plugin in Strapi.

### 4. Enable SSL/TLS

Update ingress with cert-manager:

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

### 5. Increase Resources

For production with more content:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### 6. Set Up Backups

Strapi uses PostgreSQL, so backup your database regularly:

```bash
# Example backup
pg_dump -h <host> -U <user> -d <database> > strapi_backup.sql
```

### 7. Configure Production URL

Set the correct public URL:

```yaml
- name: URL
  value: "https://splat.top"
```

## Advanced Features

### Webhooks

Strapi supports webhooks to trigger actions when content changes:

1. Go to **Settings** → **Webhooks**
2. Create webhook for `blog-post.create`, `blog-post.update`, etc.
3. Integrate with Discord, Slack, or custom services

### API Tokens

Generate API tokens for programmatic access:

1. Go to **Settings** → **API Tokens**
2. Create token with specific permissions
3. Use token in your apps for authenticated API access

### Plugins

Extend Strapi with plugins:

- **GraphQL**: Enable GraphQL API
- **Documentation**: Auto-generated API docs
- **SEO**: SEO metadata fields
- **Sitemap**: Generate XML sitemaps
- **Comments**: User comments on posts

Install plugins via npm:

```bash
npm install @strapi/plugin-graphql
```

### Internationalization

Enable i18n for multi-language content:

1. Install i18n plugin
2. Enable it for blog-post content type
3. Create content in multiple locales

## Troubleshooting

### Strapi pod not starting

Check the logs:
```bash
make strapi-logs
```

Common issues:
- Database connection failed: Check database credentials in secrets
- Port conflicts: Ensure port 1337 isn't already in use
- Memory limits: Increase resource limits if OOM

### Can't access admin panel

1. Verify ingress is routing `/strapi` correctly:
   ```bash
   kubectl get ingress dev-ingress -o yaml
   ```

2. Check Strapi service:
   ```bash
   kubectl get svc strapi-cms-service -n splattop-dev
   ```

3. Port-forward directly to test:
   ```bash
   kubectl port-forward svc/strapi-cms-service 1337:80 -n splattop-dev
   ```
   Then access http://localhost:1337/admin

### Blog posts not showing in frontend

1. Check API permissions (Settings → Roles → Public)
2. Ensure posts are Published (not Draft)
3. Check browser console for API errors
4. Verify ingress is routing `/strapi/api` correctly

### Database migrations failing

If content types change and Strapi can't migrate:

1. Check Strapi logs for migration errors
2. Manually fix schema conflicts in PostgreSQL
3. Or reset Strapi tables (dev only):
   ```sql
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   ```

## API Reference

### List Blog Posts

```http
GET /strapi/api/blog-posts?pagination[page]=1&pagination[pageSize]=10
```

Response:
```json
{
  "data": [
    {
      "id": 1,
      "attributes": {
        "title": "Post Title",
        "slug": "post-title",
        "content": "Post content in Markdown...",
        "excerpt": "Short summary",
        "author": "Author Name",
        "publishedAt": "2024-01-01T00:00:00.000Z",
        "featuredImage": {
          "data": {
            "attributes": {
              "url": "/uploads/image.jpg"
            }
          }
        }
      }
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "pageSize": 10,
      "pageCount": 5,
      "total": 42
    }
  }
}
```

### Get Single Blog Post

```http
GET /strapi/api/blog-posts?filters[slug][$eq]=post-slug
```

### With Population

To include related data (like featuredImage):

```http
GET /strapi/api/blog-posts?populate=featuredImage
```

## Backup and Migration

### Export Content

```bash
# Use Strapi's data transfer feature
npx strapi transfer --from http://source.example.com/admin --to http://destination.example.com/admin
```

### Backup Database

Since Strapi uses PostgreSQL, back up the database:

```bash
kubectl exec -it postgres-pod -- pg_dump -U postgres > strapi_backup.sql
```

## Additional Resources

- [Strapi Documentation](https://docs.strapi.io/)
- [Strapi REST API](https://docs.strapi.io/dev-docs/api/rest)
- [Strapi Content API](https://docs.strapi.io/dev-docs/api/content-api)
- [Strapi Plugins Market](https://market.strapi.io/)
- [Strapi Cloud](https://strapi.io/cloud) - Managed hosting option

## Support

For Strapi-specific issues:
- [Strapi Forum](https://forum.strapi.io/)
- [Strapi Discord](https://discord.strapi.io/)
- [Strapi GitHub](https://github.com/strapi/strapi)

For deployment issues specific to splat.top, check the Kubernetes logs and ensure all manifests are applied correctly.
