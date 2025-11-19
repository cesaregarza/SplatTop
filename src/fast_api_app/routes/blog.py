from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select

from fast_api_app.connections import async_session_factory
from shared_lib.models import BlogPost

router = APIRouter()


class BlogPostResponse(BaseModel):
    id: int
    slug: str
    title: str
    excerpt: Optional[str]
    content: str
    author: Optional[str]
    featured_image_url: Optional[str]
    is_published: bool
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BlogPostListItem(BaseModel):
    id: int
    slug: str
    title: str
    excerpt: Optional[str]
    author: Optional[str]
    featured_image_url: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/api/blog", response_model=List[BlogPostListItem])
async def get_blog_posts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Posts per page"),
    published_only: bool = Query(True, description="Show only published posts"),
):
    """Get a paginated list of blog posts"""
    async with async_session_factory() as db:
        query = select(BlogPost).order_by(desc(BlogPost.published_at))

        if published_only:
            query = query.where(BlogPost.is_published == True)

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        posts = result.scalars().all()

        return [
            BlogPostListItem(
                id=post.id,
                slug=post.slug,
                title=post.title,
                excerpt=post.excerpt,
                author=post.author,
                featured_image_url=post.featured_image_url,
                published_at=post.published_at,
                created_at=post.created_at,
            )
            for post in posts
        ]


@router.get("/api/blog/{slug}", response_model=BlogPostResponse)
async def get_blog_post(slug: str):
    """Get a single blog post by slug"""
    async with async_session_factory() as db:
        query = select(BlogPost).where(BlogPost.slug == slug)
        result = await db.execute(query)
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")

        if not post.is_published:
            raise HTTPException(
                status_code=404, detail="Blog post not published"
            )

        return BlogPostResponse(
            id=post.id,
            slug=post.slug,
            title=post.title,
            excerpt=post.excerpt,
            content=post.content,
            author=post.author,
            featured_image_url=post.featured_image_url,
            is_published=post.is_published,
            published_at=post.published_at,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
