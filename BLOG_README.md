# Blog Feature Documentation

## Overview

The blog feature has been added to splat.top, providing a custom CMS integrated with the existing PostgreSQL database and React/FastAPI stack.

## Architecture

- **Backend**: FastAPI endpoints for blog CRUD operations
- **Frontend**: React components with Tailwind CSS styling
- **Database**: PostgreSQL table in the `splatgpt` schema
- **Styling**: Custom CSS matching the existing site's purple theme

## Database Setup

### Run the Migration

To create the `blog_posts` table, run the SQL migration script:

```bash
psql -h <host> -U <user> -d <database> -f migrations/001_create_blog_posts.sql
```

Or execute the SQL directly in your PostgreSQL client.

### Table Schema

The `blog_posts` table includes:
- `id`: Primary key (BIGSERIAL)
- `slug`: URL-friendly unique identifier (VARCHAR 255)
- `title`: Post title (VARCHAR 500)
- `excerpt`: Short summary (TEXT)
- `content`: Full post content in HTML (TEXT)
- `author`: Author name (VARCHAR 255)
- `featured_image_url`: Optional featured image URL (VARCHAR 1000)
- `is_published`: Publication status (BOOLEAN)
- `published_at`: Publication timestamp (TIMESTAMP WITH TIME ZONE)
- `created_at`: Creation timestamp (TIMESTAMP WITH TIME ZONE)
- `updated_at`: Last update timestamp (TIMESTAMP WITH TIME ZONE)

## API Endpoints

### Get Blog Posts (List)
```
GET /api/blog
Query Parameters:
  - page: Page number (default: 1)
  - limit: Posts per page (default: 10, max: 50)
  - published_only: Show only published posts (default: true)
```

### Get Single Blog Post
```
GET /api/blog/{slug}
Returns a single blog post by slug
```

## Creating Blog Posts

Currently, blog posts need to be created directly in the database. You can insert posts using SQL:

```sql
INSERT INTO splatgpt.blog_posts (
    slug,
    title,
    excerpt,
    content,
    author,
    is_published,
    published_at
) VALUES (
    'my-first-post',
    'My First Blog Post',
    'This is a short excerpt of my post.',
    '<h2>Hello World</h2><p>This is the full content of my blog post.</p>',
    'Author Name',
    TRUE,
    CURRENT_TIMESTAMP
);
```

### Content Format

Blog post content supports HTML and will be styled according to the site's theme:
- Headings (`<h1>` - `<h6>`): Purple colored
- Links (`<a>`): Purple with hover effect
- Code blocks (`<code>`, `<pre>`): Dark background
- Lists (`<ul>`, `<ol>`): Styled bullets/numbers
- Images (`<img>`): Responsive with rounded corners
- Tables: Striped rows with purple headers
- Blockquotes: Purple left border

## Frontend Components

### BlogList Component
- Located at: `src/react_app/src/components/blog/blog_list.jsx`
- Route: `/blog`
- Features:
  - Paginated list of blog posts
  - Featured image display
  - Excerpt preview
  - Author and date information
  - Previous/Next navigation

### BlogPost Component
- Located at: `src/react_app/src/components/blog/blog_post.jsx`
- Route: `/blog/:slug`
- Features:
  - Full post content display
  - Featured image
  - Author and publication date
  - Back to blog link
  - Custom styled HTML content

## Styling

All blog components use:
- Tailwind CSS for layout and components
- Custom `.blog-content` CSS class for content styling
- Purple theme colors matching the site (`--color-purple`, `--color-purplelight`, `--color-purpledark`)
- Dark mode design (gray-800, gray-900 backgrounds)

## Future Enhancements

Consider adding:
1. **Admin Panel**: Web interface for creating/editing posts
2. **Markdown Support**: Add a markdown library (like `react-markdown`) for easier content creation
3. **Categories/Tags**: Organize posts by topic
4. **Comments**: User comments on posts
5. **Search**: Full-text search for blog posts
6. **RSS Feed**: RSS/Atom feed for blog subscribers
7. **Related Posts**: Show related posts at the end of each post
8. **Draft System**: Save drafts before publishing

## Navigation

The blog is accessible from the main navigation bar with a "Blog" link between "Analytics" and the search bar.

## SEO Considerations

- Each blog post sets the document title dynamically
- Slugs are URL-friendly
- Consider adding meta tags for better SEO (description, og:tags, etc.)

## Support for CMS Tools

If you want to add a headless CMS in the future, consider:
- **Strapi**: Self-hosted, works well with PostgreSQL
- **Ghost**: Focused on blogging
- **Contentful**: Cloud-based headless CMS
- **Sanity**: Real-time collaboration features

The current implementation provides a solid foundation that can be extended with any of these tools.
