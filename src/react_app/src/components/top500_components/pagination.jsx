import React from "react";

const Pagination = ({
  totalItems,
  itemsPerPage,
  currentPage,
  onPageChange,
  isTopOfPage,
  compact = false,
  className = "",
  align = "center",
}) => {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const justifyClass = {
    center: "justify-center",
    left: "justify-start",
    right: "justify-end",
  }[align];

  if (totalPages <= 1) {
    return null;
  }

  return (
    <div
      className={`flex ${justifyClass} ${
        isTopOfPage ? "mb-4" : "mt-4"
      } flex-wrap gap-2 ${className}`}
    >
      {Array.from({ length: totalPages }, (_, i) => (
        <button
          key={i}
          onClick={() => onPageChange(i + 1)}
          className={`rounded-md border ${
            currentPage === i + 1
              ? "border-purple-500/60 bg-purple-950/40 text-white"
              : "border-gray-800 bg-gray-950/70 text-gray-200 hover:border-gray-700 hover:bg-gray-900"
          } ${compact ? "min-w-[2.25rem] px-2.5 py-1.5 text-sm" : "px-4 py-2"}`}
          aria-current={currentPage === i + 1 ? "page" : undefined}
        >
          {i + 1}
        </button>
      ))}
    </div>
  );
};

export default Pagination;
