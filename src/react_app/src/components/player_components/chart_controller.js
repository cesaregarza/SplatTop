import React, { useState, useEffect } from "react";
import ModeSelector from "../top500_components/selectors/mode_selector";
import XChart from "./xchart";

function ChartController({ data, modes }) {
  const [mode, setMode] = useState(modes[0]);
  const [colorMode, setColorMode] = useState("Seasonal");

  useEffect(() => {
    // This could be used to fetch additional data or perform setup operations
  }, []);

  const handleModeChange = (newMode) => {
    setMode(newMode);
  };

  const toggleColorMode = () => {
    setColorMode((prevColorMode) =>
      prevColorMode === "Seasonal" ? "Accessible" : "Seasonal"
    );
  };

  return (
    <div>
      <XChart data={data} mode={mode} colorMode={colorMode} />
      <div className="relative controls-box border-2 border-gray-200 rounded-lg py-4 px-1 mt-5">
        <div className="absolute bg-gray-900">
          <h2 className="text-lg font-semibold rounded-sm">Controls</h2>
        </div>
        <div className="flex flex-col justify-center items-center">
          <div className="w-full flex justify-center items-center">
            <label
              htmlFor="toggleColorMode"
              className="inline-flex items-center cursor-pointer"
            >
              <span
                className={`text-sm font-medium mr-2 ${
                  colorMode === "Seasonal" ? "highlighted-option" : ""
                }`}
              >
                Seasonal
              </span>
              <div className="relative" title="Change the color scheme">
                <input
                  type="checkbox"
                  id="toggleColorMode"
                  className="sr-only peer"
                  checked={colorMode === "Accessible"}
                  onChange={toggleColorMode}
                />
                <div
                  className={`w-11 h-6 rounded-full peer peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5 ${
                    colorMode === "Accessible" ? "accessible-bg" : "seasonal-bg"
                  }`}
                ></div>
              </div>
              <span
                className={`text-sm font-medium ml-2 ${
                  colorMode === "Accessible" ? "highlighted-option" : ""
                }`}
              >
                Accessible
              </span>
            </label>
          </div>
          <ModeSelector
            selectedMode={mode}
            setSelectedMode={handleModeChange}
            allowedModes={modes.map((mode) =>
              data.some((d) => d.mode === mode)
            )}
            showTitle={false}
            modeButtonSize="mt-3"
            baseClass="w-full sm:w-auto"
          />
        </div>
      </div>
    </div>
  );
}

export default ChartController;
