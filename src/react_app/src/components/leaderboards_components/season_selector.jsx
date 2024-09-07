import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { calculateSeasonNow, getSeasonName } from "../utils/season_utils";
import { FaTimes } from "react-icons/fa";

const SeasonSelector = ({ selectedSeason, setSelectedSeason }) => {
  const { t } = useTranslation("weapon_leaderboard");
  const { t: gameT } = useTranslation("game");
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const currentSeason = calculateSeasonNow();
  const seasons = Array.from({ length: currentSeason }, (_, i) => i + 1).sort(
    (a, b) => a - b
  );

  const handleSeasonSelect = (season) => {
    setSelectedSeason(season);
    setIsOpen(false);
  };

  const handleClearSeason = (e) => {
    e.stopPropagation();
    setSelectedSeason(null);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="relative inline-block w-64" ref={dropdownRef}>
      <div
        className="flex items-center justify-between w-full bg-gray-800 border border-gray-700 text-white py-2 px-3 rounded leading-tight cursor-pointer"
        onClick={toggleDropdown}
      >
        {selectedSeason !== null ? (
          <div className="flex items-center flex-grow">
            <span>{`${selectedSeason} ${getSeasonName(
              selectedSeason,
              gameT
            )}`}</span>
            <button
              onClick={handleClearSeason}
              className="ml-auto p-1 hover:bg-gray-700 rounded"
              aria-label="Clear season selection"
            >
              <FaTimes size={14} />
            </button>
          </div>
        ) : (
          <span>{t("all_seasons")}</span>
        )}
        <svg
          className={`fill-current h-4 w-4 ml-2 ${
            isOpen ? "transform rotate-180" : ""
          }`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
        >
          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
        </svg>
      </div>
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg max-h-60 overflow-y-auto">
          {seasons.map((season) => (
            <div
              key={season}
              className="flex items-center px-3 py-2 cursor-pointer hover:bg-gray-700"
              onClick={() => handleSeasonSelect(season)}
            >
              <span>{`${season} ${getSeasonName(season, gameT)}`}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SeasonSelector;
