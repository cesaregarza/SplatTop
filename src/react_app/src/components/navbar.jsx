import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import SearchBar from "./misc_components/searchbar";
import LanguageSelector from "./misc_components/language_selector";

const Navbar = () => {
  const { t } = useTranslation("navigation");
  const [isActive, setIsActive] = useState(false);

  const toggleNavbar = () => {
    setIsActive(!isActive);
  };

  return (
    <header className="bg-gray-900 text-white shadow-md sticky top-0 z-50">
      <nav className="container mx-auto px-4 sm:px-6 py-2 flex justify-between items-center">
        <Link
          to="/"
          className="text-xl sm:text-2xl font-bold text-white hover:text-ab5ab7 transition duration-300"
        >
          splat.top <span className="text-purplelight">{t("top500")}</span>
        </Link>
        <button
          className="hamburger md:hidden focus:outline-none"
          onClick={toggleNavbar}
        >
          <div className="space-y-1.5">
            <div
              className={`h-0.5 w-8 bg-white rounded ${
                isActive ? "transform rotate-45 translate-y-1.5" : ""
              }`}
            ></div>
            <div
              className={`h-0.5 w-8 bg-white rounded ${
                isActive ? "opacity-0" : "opacity-100"
              }`}
            ></div>
            <div
              className={`h-0.5 w-8 bg-white rounded ${
                isActive ? "transform -rotate-45 -translate-y-1.5" : ""
              }`}
            ></div>
          </div>
        </button>
        <div
          className={`absolute top-full left-0 w-full bg-gray-900 md:bg-transparent md:static md:block ${
            isActive ? "block" : "hidden"
          } md:flex items-center md:w-auto transition-all duration-500 ease-in-out`}
        >
          <ul className="flex flex-col md:flex-row items-center md:space-x-6 py-4 md:py-0">
            <li>
              <Link
                to="/faq"
                className="block py-2 px-4 text-white hover:bg-ab5ab7 rounded-md transition duration-300"
              >
                {t("navbar.faq")}
              </Link>
            </li>
            <li>
              <Link
                to="/top_weapons"
                className="block py-2 px-4 text-white hover:bg-ab5ab7 rounded-md transition duration-300"
              >
                {t("navbar.top_weapons")}
              </Link>
            </li>
            <li>
              <Link
                to="/analytics"
                className="block py-2 px-4 text-white hover:bg-ab5ab7 rounded-md transition duration-300"
              >
                {t("navbar.analytics")}
              </Link>
            </li>
            <li>
              <SearchBar />
            </li>
            <li>
              <LanguageSelector />
            </li>
          </ul>
        </div>
      </nav>
    </header>
  );
};

export default Navbar;
