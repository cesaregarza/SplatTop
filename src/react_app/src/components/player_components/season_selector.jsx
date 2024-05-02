import React, { useState, useEffect, useRef } from "react";
import { calculateSeasonNow, getSeasonName } from "./xchart_helper_functions";

function SeasonSelector({ data, mode, onSeasonChange }) {
  const [selectedSeasons, setSelectedSeasons] = useState([]);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const currentSeason = calculateSeasonNow();
  const seasonNumbers = Array.from({ length: currentSeason }, (_, i) => i + 1);

  const handleSeasonChange = (season) => {
    const newSelectedSeasons = selectedSeasons.includes(season)
      ? selectedSeasons.filter((s) => s !== season)
      : [...selectedSeasons, season];
    setSelectedSeasons(newSelectedSeasons);
    onSeasonChange(newSelectedSeasons);
  };

  const isSeasonAvailable = (season) =>
    data.weapon_counts.some(
      (d) => d.season_number === season && d.mode === mode
    );

  useEffect(() => {
    // Set the initial selected seasons based on the available seasons for the current mode
    const availableSeasons = seasonNumbers.filter((season) =>
      isSeasonAvailable(season)
    );
    setSelectedSeasons(availableSeasons);
    onSeasonChange(availableSeasons);
  }, [mode]); // Only run this effect when the mode changes

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  const handleSeasonToggle = (season) => {
    if (isSeasonAvailable(season)) {
      handleSeasonChange(season);
    }
  };

  const columnCount = 3; // Number of columns to display
  const columnSize = Math.ceil(seasonNumbers.length / columnCount);

  return (
    <div className="relative inline-block text-left" ref={menuRef}>
      <div>
        <button
          type="button"
          className="inline-flex justify-center w-full rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-gray-800 text-sm font-medium text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
          id="options-menu"
          aria-haspopup="true"
          aria-expanded={isMenuOpen}
          onClick={() => setIsMenuOpen(!isMenuOpen)}
        >
          Select Weapon Seasons
          <svg
            className="-mr-1 ml-2 h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {isMenuOpen && (
        <div className="origin-top-right absolute right-0 mt-2 w-80 rounded-md shadow-lg bg-gray-900 ring-1 ring-black ring-opacity-5">
          <div
            className="py-1 grid grid-cols-3 gap-2"
            role="menu"
            aria-orientation="vertical"
            aria-labelledby="options-menu"
          >
            {Array.from({ length: columnCount }, (_, columnIndex) => (
              <div key={columnIndex} className="px-2">
                {seasonNumbers
                  .slice(
                    columnIndex * columnSize,
                    (columnIndex + 1) * columnSize
                  )
                  .map((season) => (
                    <label
                      key={season}
                      className={`block py-2 px-4 text-sm ${
                        isSeasonAvailable(season)
                          ? "text-white hover:bg-gray-800 hover:text-purple-400"
                          : "text-gray-500"
                      } ${
                        selectedSeasons.includes(season)
                          ? "bg-purple-900 text-purple-400"
                          : ""
                      } rounded-md cursor-pointer transition duration-200 ease-in-out`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedSeasons.includes(season)}
                        onChange={() => handleSeasonToggle(season)}
                        className="mr-2"
                      />
                      {getSeasonName(season)}
                    </label>
                  ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SeasonSelector;
