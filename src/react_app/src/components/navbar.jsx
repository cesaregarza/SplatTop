import React, { useState } from "react";
import { Link } from "react-router-dom";
import SearchBar from "./searchbar";

const Navbar = () => {
  const [isActive, setIsActive] = useState(false);

  const toggleNavbar = () => {
    setIsActive(!isActive);
  };

  return (
    <header className="bg-gray-900 text-white shadow-md sticky top-0 z-50">
      <nav className="container mx-auto px-6 py-4 flex flex-col md:flex-row justify-between items-center">
        <div className="flex items-center">
          <Link
            to="/"
            className="text-2xl font-bold text-white hover:text-ab5ab7 transition duration-300"
          >
            splat.top <span className="text-purplelight">Top 500</span>
          </Link>
        </div>
        <div className="flex items-center">
          <button
            className={`hamburger ${
              isActive ? "is-active" : ""
            } focus:outline-none`}
            onClick={toggleNavbar}
          >
            <span className="hamburger-box">
              <span className="hamburger-inner"></span>
            </span>
          </button>
        </div>
        <div
          className={`navbar-collapse ${
            isActive ? "block" : "hidden"
          } md:block`}
        >
          <ul className="navbar-nav ml-auto flex flex-col md:flex-row items-center space-y-4 md:space-y-0 md:space-x-8 mt-4 md:mt-0">
            <li>
              <Link
                to="/faq"
                className="py-2 px-4 text-white hover:bg-ab5ab7 rounded-md transition duration-300"
              >
                FAQ
              </Link>
            </li>
            <li className="w-full md:w-auto">
              <SearchBar />
            </li>
          </ul>
        </div>
      </nav>
    </header>
  );
};

export default Navbar;
