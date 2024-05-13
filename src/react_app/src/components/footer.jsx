import React from "react";
import { Link } from "react-router-dom";

const Footer = () => {
  return (
    <footer className="bg-gray-900 text-white py-8">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <Link
              to="/"
              className="text-2xl font-bold text-white hover:text-ab5ab7 transition duration-300"
            >
              splat.top <span className="text-purplelight">Top 500</span>
            </Link>
          </div>
          <div>
            <ul className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-8">
              <li>
                <Link
                  to="/about"
                  className="text-white hover:text-ab5ab7 transition duration-300"
                >
                  About
                </Link>
              </li>
              <li>
                <Link
                  to="/contact"
                  className="text-white hover:text-ab5ab7 transition duration-300"
                >
                  Contact
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <hr className="my-6 border-gray-700" />
        <div className="text-center">
          <p className="text-sm">
            &copy; {new Date().getFullYear()} splat.top. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
