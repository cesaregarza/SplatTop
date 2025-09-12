import React, { useEffect, useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import SUPPORTED_LANGUAGES from "../supported_languages";
import { FaGlobe } from "react-icons/fa";

const LanguageSelector = () => {
  const { i18n } = useTranslation();
  const [allLanguages, setAllLanguages] = useState({});
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    setAllLanguages(SUPPORTED_LANGUAGES);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleLanguageChange = (lng) => {
    i18n.changeLanguage(lng);
    setIsDropdownOpen(false);
  };

  const getLanguageTitle = (key) => {
    return allLanguages[i18n.language] ? allLanguages[i18n.language][key] : "Unknown";
  };

  return (
    <div className="relative language-selector" ref={dropdownRef}>
      <button
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        className="flex items-center bg-gray-900 text-white p-2 rounded-sm"
      >
        <FaGlobe className="mr-2" />
        {i18n.language.toUpperCase()}
      </button>
      {isDropdownOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-gray-900 text-white rounded-sm shadow-lg z-10">
          <ul className="py-1">
            {Object.keys(allLanguages).map((key) => (
              <li key={key}>
                <button
                  onClick={() => handleLanguageChange(key)}
                  className={`block px-4 py-2 text-sm hover:bg-gray-700 w-full text-left ${
                    i18n.language === key ? "bg-purple hover:bg-purplelight" : ""
                  }`}
                >
                  {getLanguageTitle(key)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default LanguageSelector;

