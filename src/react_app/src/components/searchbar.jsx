import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { getBaseApiUrl } from "./utils";
import { useTranslation } from "react-i18next";

const apiUrl = getBaseApiUrl();
const endpoint = `${apiUrl}/api/search`;

const SearchBar = () => {
  const { t } = useTranslation("main_page");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [isSearching, setIsSearching] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [isShortQuery, setIsShortQuery] = useState(false);
  const resultRefs = useRef([]);

  useEffect(() => {
    const handleSearch = async () => {
      if (searchQuery.trim() !== "" && searchQuery.length > 2) {
        setIsSearching(true);
        setIsShortQuery(false);
        const encodedQuery = encodeURIComponent(searchQuery);
        try {
          const response = await axios.get(`${endpoint}/${encodedQuery}`);
          setSearchResults(response.data);
        } catch (error) {
          console.error("Error searching:", error);
        }
        setIsSearching(false);
      } else if (searchQuery.trim() !== "" && searchQuery.length <= 2) {
        setIsShortQuery(true);
        setSearchResults([]);
        setIsSearching(false);
      } else {
        setIsShortQuery(false);
        setSearchResults([]);
        setIsSearching(false);
      }
    };

    handleSearch();
  }, [searchQuery]);

  const handleKeyDown = (e) => {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prevIndex) =>
        prevIndex <= 0 ? searchResults.length - 1 : prevIndex - 1
      );
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prevIndex) =>
        prevIndex === searchResults.length - 1 ? 0 : prevIndex + 1
      );
    } else if (e.key === "Enter") {
      if (selectedIndex !== -1) {
        const playerId = searchResults[selectedIndex][1];
        window.location.href = `/player/${playerId}`;
      }
    }
  };

  useEffect(() => {
    if (selectedIndex !== -1) {
      resultRefs.current[selectedIndex].scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [selectedIndex]);

  return (
    <div className="relative">
      <div className="flex items-center bg-white rounded-md shadow-md">
        <input
          type="text"
          placeholder={t("search_placeholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          className="w-full py-2 px-4 text-gray-700 placeholder-gray-400 rounded-md focus:outline-none"
        />
        <button
          className="text-gray-500 hover:text-gray-700 px-3 py-2 rounded-md focus:outline-none"
          onClick={() => setSearchQuery("")}
        >
          {searchQuery || isFocused ? (
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          ) : (
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              ></path>
            </svg>
          )}
        </button>
      </div>
      {searchQuery.length >= 3 && searchResults.length > 0 ? (
        <div className="absolute z-10 mt-2 w-full bg-gray-800 rounded-md shadow-lg max-h-60 overflow-y-auto">
          <ul>
            {searchResults.slice(0, 10).map((result, index) => {
              const keyText = result[0];
              const playerId = result[1];
              const highlightedText = keyText.replace(
                new RegExp(searchQuery, "gi"),
                (match) =>
                  `<span class="font-bold text-purplelight">${match}</span>`
              );
              return (
                <li
                  key={index}
                  ref={(ref) => (resultRefs.current[index] = ref)}
                  className={`px-4 py-2 text-white cursor-pointer ${
                    selectedIndex === index
                      ? "bg-gray-700"
                      : "hover:bg-gray-700"
                  }`}
                  dangerouslySetInnerHTML={{ __html: highlightedText }}
                  onClick={() => (window.location.href = `/player/${playerId}`)}
                ></li>
              );
            })}
          </ul>
        </div>
      ) : isSearching ? null : (
        <>
          {isShortQuery ? (
            <div className="absolute z-10 mt-2 w-full bg-gray-800 rounded-md shadow-lg max-h-60 overflow-y-auto text-center text-white py-2">
              {t("search_needs_3_chars")}
            </div>
          ) : (
            searchQuery.length >= 3 && (
              <div className="absolute z-10 mt-2 w-full bg-gray-800 rounded-md shadow-lg max-h-60 overflow-y-auto text-center text-white py-2">
                {t("no_results")}
              </div>
            )
          )}
        </>
      )}
    </div>
  );
};

export default SearchBar;
