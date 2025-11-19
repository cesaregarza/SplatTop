import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import ReactMarkdown from "react-markdown";

const BlogPost = () => {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPost = async () => {
      try {
        setLoading(true);
        // Fetch by slug
        const response = await axios.get("/strapi/api/blog-posts", {
          params: {
            filters: {
              slug: {
                $eq: slug,
              },
            },
            populate: ["featuredImage"],
          },
        });

        if (response.data.data && response.data.data.length > 0) {
          const postData = response.data.data[0];
          setPost(postData);
          document.title = `${postData.attributes.title} - splat.top Blog`;
        } else {
          setError("Blog post not found.");
        }
        setLoading(false);
      } catch (err) {
        console.error("Error fetching blog post:", err);
        setError("Failed to load blog post. Please try again later.");
        setLoading(false);
      }
    };

    fetchPost();
  }, [slug]);

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

  if (error || !post) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-900 border border-red-700 text-white px-4 py-3 rounded-lg mb-4">
          {error || "Post not found"}
        </div>
        <Link
          to="/blog"
          className="inline-block bg-purple hover:bg-purpledark text-white font-semibold py-2 px-4 rounded transition-colors"
        >
          Back to Blog
        </Link>
      </div>
    );
  }

  const attrs = post.attributes || {};
  const featuredImage = attrs.featuredImage?.data?.attributes?.url;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <Link
          to="/blog"
          className="text-purplelight hover:text-purpledark transition-colors"
        >
          ← Back to Blog
        </Link>
      </div>

      <article className="bg-gray-800 shadow-lg rounded-lg overflow-hidden">
        {featuredImage && (
          <div className="w-full h-96 overflow-hidden">
            <img
              src={`/strapi${featuredImage}`}
              alt={attrs.title || ""}
              className="w-full h-full object-cover"
            />
          </div>
        )}

        <div className="p-8">
          <h1 className="text-4xl font-bold mb-4 text-purplelight">
            {attrs.title || "Untitled"}
          </h1>

          <div className="flex items-center gap-4 mb-6 text-gray-400 border-b border-gray-700 pb-4">
            {attrs.author && (
              <span className="text-white">By {attrs.author}</span>
            )}
            {attrs.publishedAt && <span>{formatDate(attrs.publishedAt)}</span>}
          </div>

          <div className="prose prose-invert prose-lg max-w-none blog-content">
            <ReactMarkdown>{attrs.content || ""}</ReactMarkdown>
          </div>
        </div>
      </article>
    </div>
  );
};

export default BlogPost;
