import React from "react";
import { useTranslation } from "react-i18next";
import SplatZonesIcon from "../../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../../assets/icons/tower_control.png";
import RainmakerIcon from "../../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../../assets/icons/clam_blitz.png";
import AllModesIcon from "../../../assets/icons/all_modes.png";
import { modeKeyMap, modes } from "../../constants";

const modeIcons = {
  "Splat Zones": SplatZonesIcon,
  "Tower Control": TowerControlIcon,
  Rainmaker: RainmakerIcon,
  "Clam Blitz": ClamBlitzIcon,
  "All Modes": AllModesIcon,
};

const ModeSelector = ({
  selectedMode,
  setSelectedMode,
  allowedModes = [true, true, true, true],
  showTitle = true,
  modeButtonSize = "",
  buttonPadding = "px-4 py-2",
  imageWidth = "w-12",
  imageHeight = "h-12",
  baseClass = "mb-4 w-full sm:w-auto",
  includeAllModes = false,
  showLabels = false,
  buttonVariant = "default",
  equalWidthButtons = false,
}) => {
  const { t } = useTranslation();

  const getModeLabel = (mode) =>
    t(modeKeyMap[mode], { ns: "game", defaultValue: mode });

  const getButtonClasses = (mode) => {
    const isSelected = selectedMode === mode;
    const isAllowed = allowedModes[modes.indexOf(mode)];

    if (buttonVariant === "utility") {
      return `rounded-md border ${buttonPadding} ${modeButtonSize} ${
        isSelected
          ? "border-purple-500/60 bg-purple-950/40 text-white"
          : "border-gray-800 bg-gray-950/70 text-gray-200 hover:border-gray-700 hover:bg-gray-900"
      } flex justify-center items-center ${
        equalWidthButtons ? "w-full min-w-0" : ""
      } ${
        !isAllowed ? "cursor-not-allowed opacity-45 grayscale" : ""
      }`;
    }

    return `m-1 rounded-md ${buttonPadding} ${modeButtonSize} ${
      isSelected
        ? "bg-purpledark text-white hover:bg-purple"
        : "bg-gray-700 hover:bg-purple"
    } flex justify-center items-center ${
      !isAllowed ? "grayscale cursor-not-allowed" : ""
    }`;
  };

  return (
    <div className={baseClass}>
      {showTitle && <h2 className="text-xl font-bold mb-2">{t("modes")}</h2>}
      <div
        className={
          equalWidthButtons
            ? "grid grid-cols-2 gap-2"
            : "flex justify-center items-center flex-wrap"
        }
      >
        {modes.map((mode) => (
          <div
            key={mode}
            className={equalWidthButtons ? "min-w-0" : "flex justify-center"}
          >
            <button
              onClick={() =>
                allowedModes[modes.indexOf(mode)] ? setSelectedMode(mode) : null
              }
              className={getButtonClasses(mode)}
              disabled={!allowedModes[modes.indexOf(mode)]}
              title={
                !allowedModes[modes.indexOf(mode)]
                  ? "No data found for this mode"
                  : getModeLabel(mode)
              }
              aria-label={getModeLabel(mode)}
              aria-pressed={selectedMode === mode}
            >
              <img
                src={modeIcons[mode]}
                alt={mode}
                className={`${imageWidth} ${imageHeight} object-cover aspect-square`}
              />
              {showLabels ? (
                <span
                  className={`ml-2 text-sm font-medium ${
                    equalWidthButtons
                      ? "min-w-0 text-left leading-tight whitespace-normal"
                      : ""
                  }`}
                >
                  {getModeLabel(mode)}
                </span>
              ) : null}
            </button>
          </div>
        ))}
        {includeAllModes && (
          <div className={equalWidthButtons ? "min-w-0" : "flex justify-center"}>
            <button
              onClick={() => setSelectedMode("All Modes")}
              className={`rounded-md ${buttonPadding} ${modeButtonSize} ${
                selectedMode === "All Modes"
                  ? "bg-purpledark text-white hover:bg-purple"
                  : "bg-gray-700 hover:bg-purple"
              } flex justify-center items-center ${
                equalWidthButtons ? "w-full min-w-0" : ""
              }`}
              aria-label="All Modes"
              aria-pressed={selectedMode === "All Modes"}
            >
              <img
                src={AllModesIcon}
                alt="All Modes"
                className={`${imageWidth} ${imageHeight} object-cover aspect-square`}
              />
              {showLabels ? (
                <span
                  className={`ml-2 text-sm font-medium ${
                    equalWidthButtons
                      ? "min-w-0 text-left leading-tight whitespace-normal"
                      : ""
                  }`}
                >
                  All Modes
                </span>
              ) : null}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ModeSelector;
