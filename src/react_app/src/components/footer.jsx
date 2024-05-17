import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

const Footer = () => {
  const { t } = useTranslation("navigation");
  const dateString = new Date().getFullYear();
  const rightsString = t("footer.rights").replace("%DATE%", dateString);
  return (
    <footer className="bg-gray-900 text-white py-8">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <Link
              to="/"
              className="text-2xl font-bold text-white hover:text-ab5ab7 transition duration-300"
            >
              splat.top{" "}
              <span className="text-purplelight">{t("top500")}</span>
            </Link>
          </div>
          <div>
            <ul className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-8">
              <li>
                <Link
                  to="/about"
                  className="text-white hover:text-ab5ab7 transition duration-300"
                >
                  {t("footer.about")}
                </Link>
              </li>
              <li>
                <Link
                  to="/contact"
                  className="text-white hover:text-ab5ab7 transition duration-300"
                >
                  {t("footer.contact")}
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <hr className="my-6 border-gray-700" />
        <div className="text-center">
          <p className="text-sm">&copy; {rightsString}</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
