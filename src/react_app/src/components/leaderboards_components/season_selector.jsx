import React, { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { calculateSeasonNow, getSeasonName } from "../utils/season_utils";
import { FaTimes } from "react-icons/fa";

const SEASON_ACCENT_COLORS = ["#22c55e", "#facc15", "#fb923c", "#38bdf8"];

const SeasonValue = ({ accentColor, season, seasonName, selected, year }) => (
  <div className="flex min-w-0 items-center gap-3">
    <span
      className="h-3 w-3 shrink-0 rounded-full"
      style={{ backgroundColor: accentColor }}
      aria-hidden="true"
    />
    <div className="min-w-0">
      <div className="grid min-w-0 grid-cols-[3.75rem_minmax(0,1fr)] items-center gap-2">
        <span className="inline-flex min-w-[3.75rem] items-center justify-center rounded-full border border-amber-300/30 bg-amber-300/10 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-amber-200">
          {year}
        </span>
        <span
          className="inline-flex min-w-0 max-w-full items-center rounded-full border px-2 py-0.5 text-xs font-semibold text-white"
          style={{
            borderColor: accentColor,
            backgroundColor: `${accentColor}22`,
          }}
        >
          <span className="truncate">{seasonName}</span>
        </span>
      </div>
      <div
        className={`mt-1 text-xs ${selected ? "text-gray-200" : "text-gray-400"}`}
      >
        Season {season}
      </div>
    </div>
  </div>
);

const SeasonSelector = ({
  selectedSeason,
  setSelectedSeason,
  className = "w-full",
  availableSeasons = null,
  allowClear = true,
  disabled = false,
  emptyLabel = null,
}) => {
  const { t } = useTranslation("weapon_leaderboard");
  const { t: gameT } = useTranslation("game");
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const currentSeason = calculateSeasonNow();
  const seasons = useMemo(
    () =>
      availableSeasons && availableSeasons.length > 0
        ? [...availableSeasons]
        : Array.from({ length: currentSeason }, (_, i) => i + 1).sort(
            (a, b) => a - b
          ),
    [availableSeasons, currentSeason]
  );
  const isDisabled = disabled || seasons.length === 0;

  const getSeasonParts = (season) => {
    const seasonOffset = season + 2;
    const seasonIndex = seasonOffset % 4;
    const year = 2022 + Math.floor(seasonOffset / 4);
    const seasonNames = [
      gameT("spring"),
      gameT("summer"),
      gameT("autumn"),
      gameT("winter"),
    ];

    return {
      year,
      seasonIndex,
      seasonName: seasonNames[seasonIndex],
    };
  };

  const getAccentColor = (season) =>
    SEASON_ACCENT_COLORS[getSeasonParts(season).seasonIndex];

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
    if (!isDisabled) {
      setIsOpen(!isOpen);
    }
  };

  const selectionLabel =
    selectedSeason !== null
      ? `Season ${selectedSeason} ${getSeasonName(selectedSeason, gameT)}`
      : emptyLabel || t("all_seasons");
  const selectedSeasonParts =
    selectedSeason !== null ? getSeasonParts(selectedSeason) : null;
  const selectedAccentColor =
    selectedSeason !== null ? getAccentColor(selectedSeason) : null;

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        type="button"
        disabled={isDisabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={selectionLabel}
        className={`flex w-full items-center justify-between rounded-md border border-gray-700 bg-gray-800/90 px-3 py-2.5 leading-tight text-white transition ${
          isDisabled
            ? "cursor-not-allowed opacity-60"
            : "cursor-pointer hover:border-gray-600 hover:bg-gray-800"
        } ${selectedSeason !== null && allowClear ? "pr-12" : ""}`}
        onClick={toggleDropdown}
        onKeyDown={(event) => {
          if (isDisabled) {
            return;
          }
          if (event.key === "Escape") {
            setIsOpen(false);
          }
        }}
      >
        {selectedSeason !== null ? (
          <div className="flex min-w-0 grow items-center gap-3">
            <div className="min-w-0 grow">
              <SeasonValue
                accentColor={selectedAccentColor}
                season={selectedSeason}
                seasonName={selectedSeasonParts.seasonName}
                selected={true}
                year={selectedSeasonParts.year}
              />
            </div>
          </div>
        ) : (
          <div className="min-w-0">
            <span className="text-sm text-gray-200">{selectionLabel}</span>
          </div>
        )}
        <svg
          className={`ml-2 h-4 w-4 shrink-0 fill-current ${
            isOpen ? "transform rotate-180" : ""
          }`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
        </svg>
      </button>
      {selectedSeason !== null && allowClear ? (
        <button
          type="button"
          onClick={handleClearSeason}
          className="absolute right-9 top-1/2 -translate-y-1/2 rounded-md p-1 text-gray-300 transition hover:bg-gray-700 hover:text-white"
          aria-label="Clear season selection"
        >
          <FaTimes size={14} />
        </button>
      ) : null}
      {isOpen && !isDisabled && (
        <div
          className="absolute z-10 mt-2 max-h-72 w-full overflow-y-auto rounded-md border border-gray-700 bg-gray-900 shadow-lg"
          role="listbox"
          aria-label={selectionLabel}
        >
          {seasons.map((season) => {
            const seasonParts = getSeasonParts(season);
            const accentColor =
              SEASON_ACCENT_COLORS[seasonParts.seasonIndex];
            const isSelected = selectedSeason === season;

            return (
              <button
                key={season}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={`flex w-full items-center justify-between border-b border-gray-800 px-3 py-3 text-left transition last:border-b-0 ${
                  isSelected ? "bg-gray-800/90" : "hover:bg-gray-800/70"
                }`}
                style={
                  isSelected
                    ? {
                        boxShadow: `inset 0 0 0 1px ${accentColor}`,
                      }
                    : undefined
                }
                onClick={() => handleSeasonSelect(season)}
              >
                <SeasonValue
                  accentColor={accentColor}
                  season={season}
                  seasonName={seasonParts.seasonName}
                  selected={isSelected}
                  year={seasonParts.year}
                />
                {isSelected ? (
                  <span
                    className="ml-3 text-xs font-semibold uppercase tracking-[0.16em]"
                    style={{ color: accentColor }}
                  >
                    Selected
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default SeasonSelector;
