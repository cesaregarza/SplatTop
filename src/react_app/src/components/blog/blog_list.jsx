import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const BlogList = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  document.title = "splat.top - Blog";

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        setLoading(true);
        const response = await axios.get("/api/blog", {
          params: { page, limit: 10 },
        });

        if (response.data.length < 10) {
          setHasMore(false);
        }

        setPosts(response.data);
        setLoading(false);
      } catch (err) {
        setError("Failed to load blog posts. Please try again later.");
        setLoading(false);
      }
    };

    fetchPosts();
  }, [page]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center min-h-[400px]">
          <div className="text-purplelight text-xl">Loading...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-900 border border-red-700 text-white px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-8 text-center text-purplelight">
        Blog
      </h1>

      {posts.length === 0 ? (
        <div className="bg-gray-800 shadow-lg rounded-lg p-6 text-center">
          <p className="text-white">No blog posts yet. Check back soon!</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {posts.map((post) => (
            <div
              key={post.id}
              className="bg-gray-800 shadow-lg rounded-lg overflow-hidden hover:shadow-xl transition-shadow duration-300"
            >
              {post.featured_image_url && (
                <div className="w-full h-64 overflow-hidden">
                  <img
                    src={post.featured_image_url}
                    alt={post.title}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="p-6">
                <Link to={`/blog/${post.slug}`}>
                  <h2 className="text-3xl font-semibold mb-3 text-purplelight hover:text-purpledark transition-colors">
                    {post.title}
                  </h2>
                </Link>

                <div className="flex items-center gap-4 mb-4 text-gray-400 text-sm">
                  {post.author && <span>By {post.author}</span>}
                  {post.published_at && (
                    <span>{formatDate(post.published_at)}</span>
                  )}
                </div>

                {post.excerpt && (
                  <p className="text-white mb-4 line-clamp-3">{post.excerpt}</p>
                )}

                <Link
                  to={`/blog/${post.slug}`}
                  className="inline-block bg-purple hover:bg-purpledark text-white font-semibold py-2 px-4 rounded transition-colors"
                >
                  Read More
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {posts.length > 0 && (
        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="bg-purple hover:bg-purpledark text-white font-semibold py-2 px-6 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="flex items-center text-white">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasMore}
            className="bg-purple hover:bg-purpledark text-white font-semibold py-2 px-6 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default BlogList;
