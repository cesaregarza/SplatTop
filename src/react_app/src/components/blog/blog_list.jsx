import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const BlogList = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const pageSize = 10;

  document.title = "splat.top - Blog";

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        setLoading(true);
        const response = await axios.get("/strapi/api/blog-posts", {
          params: {
            pagination: {
              page: page,
              pageSize: pageSize,
            },
            sort: ["publishedAt:desc"],
            populate: ["featuredImage"],
          },
        });

        setPosts(response.data.data || []);
        setPageCount(response.data.meta?.pagination?.pageCount || 1);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching blog posts:", err);
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
          {posts.map((post) => {
            const attrs = post.attributes || {};
            const featuredImage = attrs.featuredImage?.data?.attributes?.url;

            return (
              <div
                key={post.id}
                className="bg-gray-800 shadow-lg rounded-lg overflow-hidden hover:shadow-xl transition-shadow duration-300"
              >
                {featuredImage && (
                  <div className="w-full h-64 overflow-hidden">
                    <img
                      src={`/strapi${featuredImage}`}
                      alt={attrs.title || ""}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <div className="p-6">
                  <Link to={`/blog/${attrs.slug || post.id}`}>
                    <h2 className="text-3xl font-semibold mb-3 text-purplelight hover:text-purpledark transition-colors">
                      {attrs.title || "Untitled"}
                    </h2>
                  </Link>

                  <div className="flex items-center gap-4 mb-4 text-gray-400 text-sm">
                    {attrs.author && <span>By {attrs.author}</span>}
                    {attrs.publishedAt && (
                      <span>{formatDate(attrs.publishedAt)}</span>
                    )}
                  </div>

                  {attrs.excerpt && (
                    <p className="text-white mb-4 line-clamp-3">
                      {attrs.excerpt}
                    </p>
                  )}

                  <Link
                    to={`/blog/${attrs.slug || post.id}`}
                    className="inline-block bg-purple hover:bg-purpledark text-white font-semibold py-2 px-4 rounded transition-colors"
                  >
                    Read More
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {posts.length > 0 && pageCount > 1 && (
        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="bg-purple hover:bg-purpledark text-white font-semibold py-2 px-6 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="flex items-center text-white">
            Page {page} of {pageCount}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={page === pageCount}
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
