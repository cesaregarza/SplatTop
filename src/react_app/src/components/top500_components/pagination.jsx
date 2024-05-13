import React from "react";

const Pagination = ({
  totalItems,
  itemsPerPage,
  currentPage,
  onPageChange,
  isTopOfPage,
}) => {
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  return (
    <div
      className={`flex justify-center ${
        isTopOfPage ? "mb-4" : "mt-4"
      } flex-wrap`}
    >
      {Array.from({ length: totalPages }, (_, i) => (
        <button
          key={i}
          onClick={() => onPageChange(i + 1)}
          className={`mx-1 px-4 py-2 rounded-md ${
            currentPage === i + 1
              ? "bg-purpledark text-white hover:bg-purple"
              : "bg-gray-700 hover:bg-purple"
          }`}
        >
          {i + 1}
        </button>
      ))}
    </div>
  );
};

export default Pagination;
