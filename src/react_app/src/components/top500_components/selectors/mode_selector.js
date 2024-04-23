import React from "react";
import SplatZonesIcon from "../../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../../assets/icons/tower_control.png";
import RainmakerIcon from "../../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../../assets/icons/clam_blitz.png";

const modes = ["Splat Zones", "Tower Control", "Rainmaker", "Clam Blitz"];
const modeIcons = {
  "Splat Zones": SplatZonesIcon,
  "Tower Control": TowerControlIcon,
  Rainmaker: RainmakerIcon,
  "Clam Blitz": ClamBlitzIcon,
};
const modesSplit = [
  [modes[0], modes[1]],
  [modes[2], modes[3]],
];
const modeButtonSize = "px-4";

const ModeSelector = ({
  selectedMode,
  setSelectedMode,
  allowedModes = [true, true, true, true],
}) => {
  return (
    <div className="mb-4 w-full sm:w-auto">
      <h2 className="text-xl font-bold mb-2">Modes</h2>
      <div className="flex justify-center items-center">
        {modesSplit.map((modePair, pairIndex) => (
          <div
            key={pairIndex}
            className="grid grid-cols-2 justify-center items-center mb-2"
          >
            {modePair.map((mode, index) => (
              <div key={index} className="flex justify-center">
                <button
                  onClick={() =>
                    allowedModes[modes.indexOf(mode)]
                      ? setSelectedMode(mode)
                      : null
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
                    className="h-12 w-12 object-cover aspect-square"
                  />
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ModeSelector;
