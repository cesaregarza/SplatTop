-- Migration: Create blog_posts table
-- Schema: splatgpt
-- Description: This migration creates the blog_posts table for storing blog content

CREATE TABLE IF NOT EXISTS splatgpt.blog_posts (
    id BIGSERIAL PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    excerpt TEXT,
    content TEXT NOT NULL,
    author VARCHAR(255),
    featured_image_url VARCHAR(1000),
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_blog_posts_slug ON splatgpt.blog_posts(slug);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published_at ON splatgpt.blog_posts(published_at);
CREATE INDEX IF NOT EXISTS idx_blog_posts_is_published ON splatgpt.blog_posts(is_published);

-- Add a comment to the table
COMMENT ON TABLE splatgpt.blog_posts IS 'Stores blog posts for the splat.top blog section';

-- Example: Insert a sample blog post (optional, can be removed after testing)
-- INSERT INTO splatgpt.blog_posts (slug, title, excerpt, content, author, is_published, published_at)
-- VALUES (
--     'welcome-to-splat-top-blog',
--     'Welcome to the splat.top Blog',
--     'We''re excited to announce the launch of our new blog where we''ll share insights, updates, and analysis about Splatoon 3 competitive play.',
--     '<h2>Welcome to splat.top Blog!</h2><p>We''re thrilled to introduce our new blog section where we''ll be sharing:</p><ul><li>Meta analysis and trends</li><li>Player spotlights and interviews</li><li>Tournament coverage and results</li><li>Data insights and statistics</li><li>Site updates and new features</li></ul><p>Stay tuned for our upcoming posts!</p>',
--     'The splat.top Team',
--     TRUE,
--     CURRENT_TIMESTAMP
-- );
