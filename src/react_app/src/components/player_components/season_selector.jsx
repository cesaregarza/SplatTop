import React, { useEffect, useRef, useState } from "react";
import { calculateSeasonNow, getSeasonName } from "../utils/season_utils";
import { useTranslation } from "react-i18next";

function SeasonSelector({ data, mode, onSeasonChange, compact = false }) {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const [selectedSeasons, setSelectedSeasons] = useState([]);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const currentSeason = calculateSeasonNow();
  const seasonNumbers = Array.from({ length: currentSeason }, (_, i) => i + 1);

  const isSeasonAvailable = (season) =>
    data.weapon_counts.some(
      (entry) => entry.season_number === season && entry.mode === mode
    );

  const availableSeasons = seasonNumbers.filter((season) =>
    isSeasonAvailable(season)
  );

  const updateSelectedSeasons = (seasons) => {
    setSelectedSeasons(seasons);
    onSeasonChange(seasons);
  };

  useEffect(() => {
    updateSelectedSeasons(availableSeasons);
  }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const handleSeasonChange = (season) => {
    const newSelectedSeasons = selectedSeasons.includes(season)
      ? selectedSeasons.filter((entry) => entry !== season)
      : [...selectedSeasons, season];
    updateSelectedSeasons(newSelectedSeasons);
  };

  const handleSelectAll = () => {
    updateSelectedSeasons(availableSeasons);
  };

  const handleClearAll = () => {
    updateSelectedSeasons([]);
  };

  const selectionLabel = (() => {
    if (availableSeasons.length === 0) {
      return t("controller.no_seasons_available");
    }

    if (selectedSeasons.length === 0) {
      return t("controller.all_seasons_shown");
    }

    if (selectedSeasons.length === availableSeasons.length) {
      return t("controller.all_available_seasons");
    }

    if (selectedSeasons.length === 1) {
      return t("controller.one_season_selected");
    }

    return t("controller.many_seasons_selected").replace(
      "%COUNT%",
      selectedSeasons.length
    );
  })();

  return (
    <div className={compact ? "w-full min-w-0" : "w-full"}>
      <div className="relative inline-block w-full text-left" ref={menuRef}>
        <button
          type="button"
          className={`flex w-full items-center justify-between border border-gray-800 bg-black/20 text-left text-white transition hover:border-gray-700 hover:bg-gray-900 focus:outline-hidden focus:ring-2 focus:ring-purple-500 ${
            compact
              ? "rounded-md px-3 py-2 text-sm"
              : "rounded-lg px-4 py-3"
          }`}
          id="options-menu"
          aria-haspopup="true"
          aria-expanded={isMenuOpen}
          aria-label={`${t("controller.select_season")}: ${selectionLabel}`}
          onClick={() => setIsMenuOpen(!isMenuOpen)}
        >
          {compact ? (
            <span className="min-w-0 text-sm leading-tight text-gray-200">
              {selectionLabel}
            </span>
          ) : (
            <span className="flex flex-col">
              <span className="text-sm font-semibold">
                {t("controller.select_season")}
              </span>
              <span className="text-xs text-gray-400">{selectionLabel}</span>
            </span>
          )}
          <svg
            className={`ml-3 h-5 w-5 shrink-0 transition ${
              isMenuOpen ? "rotate-180" : ""
            }`}
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
        {isMenuOpen && (
          <div
            className={`absolute z-20 mt-2 max-h-96 overflow-auto rounded-lg border border-gray-800 bg-gray-950 shadow-lg ${
              compact ? "right-0" : "left-1/2"
            }`}
            style={
              compact
                ? { width: "min(calc(100vw - 2rem), 24rem)" }
                : {
                    transform: "translateX(-50%)",
                    left: "50%",
                    width: "min(calc(100vw - 2rem), 28rem)",
                  }
            }
          >
            <div className="sticky top-0 z-10 flex items-center justify-between gap-2 border-b border-gray-800 bg-gray-900 px-4 py-3">
              <span className="text-xs font-medium uppercase tracking-[0.16em] text-gray-400">
                {t("controller.weapon_seasons")}
              </span>
              <div className="flex gap-2 text-xs">
                <button
                  type="button"
                  className="rounded-full border border-gray-700 px-3 py-1 text-gray-200 transition hover:border-purple-500 hover:text-white"
                  onClick={handleSelectAll}
                >
                  {t("controller.select_all")}
                </button>
                <button
                  type="button"
                  className="rounded-full border border-gray-700 px-3 py-1 text-gray-200 transition hover:border-purple-500 hover:text-white"
                  onClick={handleClearAll}
                >
                  {t("controller.clear_all")}
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3">
              {seasonNumbers.map((season) => (
                <label
                  key={season}
                  className={`flex items-center rounded-lg px-3 py-2 text-sm transition duration-200 ease-in-out ${
                    isSeasonAvailable(season)
                      ? "cursor-pointer text-white hover:bg-gray-800 hover:text-purple-400"
                      : "cursor-not-allowed text-gray-500"
                  } ${
                    selectedSeasons.includes(season)
                      ? "bg-purple-900/60 text-purple-200 ring-1 ring-purple-500/60"
                      : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedSeasons.includes(season)}
                    disabled={!isSeasonAvailable(season)}
                    onChange={() => handleSeasonChange(season)}
                    className="mr-2"
                  />
                  <span>{getSeasonName(season, g)}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SeasonSelector;
