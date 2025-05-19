import React from "react";
import { useTranslation } from "react-i18next";
import SplatZonesIcon from "../../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../../assets/icons/tower_control.png";
import RainmakerIcon from "../../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../../assets/icons/clam_blitz.png";
import AllModesIcon from "../../../assets/icons/all_modes.png";
import { modes } from "../../constants";

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
  modeButtonSize = "px-4",
  imageWidth = "w-12",
  imageHeight = "h-12",
  baseClass = "mb-4 w-full sm:w-auto",
  includeAllModes = false,
}) => {
  const { t } = useTranslation();
  return (
    <div className={baseClass}>
      {showTitle && <h2 className="text-xl font-bold mb-2">{t("modes")}</h2>}
      <div className="flex justify-center items-center flex-wrap">
        {modes.map((mode, index) => (
          <div key={index} className="flex justify-center">
            <button
              onClick={() =>
                allowedModes[modes.indexOf(mode)] ? setSelectedMode(mode) : null
              }
              className={`m-1 px-4 py-2 rounded-md ${modeButtonSize} ${
                selectedMode === mode
                  ? "bg-purpledark text-white hover:bg-purple"
                  : "bg-gray-700 hover:bg-purple"
              } flex justify-center items-center ${
                !allowedModes[modes.indexOf(mode)]
                  ? "grayscale cursor-not-allowed"
                  : ""
              }`}
              disabled={!allowedModes[modes.indexOf(mode)]}
              title={
                !allowedModes[modes.indexOf(mode)]
                  ? "No data found for this mode"
                  : ""
              }
            >
              <img
                src={modeIcons[mode]}
                alt={mode}
                className={`${imageWidth} ${imageHeight} object-cover aspect-square`}
              />
            </button>
          </div>
        ))}
        {includeAllModes && (
          <div className="flex justify-center">
            <button
              onClick={() => setSelectedMode("All Modes")}
              className={`m-1 px-4 py-2 rounded-md ${modeButtonSize} ${
                selectedMode === "All Modes"
                  ? "bg-purpledark text-white hover:bg-purple"
                  : "bg-gray-700 hover:bg-purple"
              } flex justify-center items-center`}
            >
              <img
                src={AllModesIcon}
                alt="All Modes"
                className={`${imageWidth} ${imageHeight} object-cover aspect-square`}
              />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default React.memo(ModeSelector);
