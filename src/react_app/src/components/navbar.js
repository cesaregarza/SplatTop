import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  const [isActive, setIsActive] = useState(false);

  const toggleNavbar = () => {
    setIsActive(!isActive);
  };

  return (
    <header className="bg-gray-900 text-white shadow-md sticky top-0 z-50">
      <nav className="container mx-auto px-6 py-4 flex justify-between items-center">
        <div className="flex items-center">
          <Link to="/" className="text-2xl font-bold text-white hover:text-ab5ab7 transition duration-300">
            splat.top <span className="text-purplelight">Top 500</span>
          </Link>
        </div>
        <div className="flex items-center">
          <button
            className={`hamburger ${isActive ? 'is-active' : ''} focus:outline-none`}
            onClick={toggleNavbar}
          >
            <span className="hamburger-box">
              <span className="hamburger-inner"></span>
            </span>
          </button>
        </div>
        <div className={`navbar-collapse ${isActive ? 'block' : 'hidden'} md:block`}>
          <ul className="navbar-nav ml-auto flex flex-col md:flex-row items-center space-y-4 md:space-y-0 md:space-x-8 mt-4 md:mt-0">
            <li>
              <Link
                to="/faq"
                className="py-2 px-4 text-white hover:bg-ab5ab7 rounded-md transition duration-300"
              >
                FAQ
              </Link>
            </li>
            <li>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search..."
                  className="py-2 px-4 pr-10 bg-white text-gray-700 placeholder-gray-500 rounded-md focus:outline-none focus:ring-2 focus:ring-ab5ab7"
                />
                <span className="absolute inset-y-0 right-0 flex items-center pr-3">
                  <svg
                    className="h-5 w-5 text-gray-400"
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
                </span>
              </div>
            </li>
          </ul>
        </div>
      </nav>
    </header>
  );
};

export default Navbar;