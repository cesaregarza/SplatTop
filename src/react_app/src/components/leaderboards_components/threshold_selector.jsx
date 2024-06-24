import React from "react";
import { useTranslation } from "react-i18next";

const ThresholdSelector = ({ threshold, setThreshold }) => {
  const { t } = useTranslation();

  const handleChange = (e) => {
    const value = parseInt(e.target.value, 10);
    setThreshold(value);
  };

  return (
    <div className="w-full max-w-3xl mx-auto my-6">
      <label
        htmlFor="threshold"
        className="block text-lg font-semibold text-gray-300 mb-2"
      >
        {t("threshold_select")}
      </label>
      <div className="relative">
        <input
          id="threshold"
          type="range"
          min="0"
          max="1000"
          value={threshold}
          onChange={handleChange}
          className="w-full h-2 bg-gray-700 rounded-full appearance-none cursor-pointer"
          style={{
            background: `linear-gradient(to right, #ab5ab7 0%, #ab5ab7 ${
              threshold / 10
            }%, #374151 ${threshold / 10}%, #374151 100%)`,
          }}
        />
        <div
          className="absolute top-1/2 transform -translate-y-1/2 w-5 h-5 bg-ab5ab7 rounded-full shadow-lg"
          style={{
            left: `calc(${threshold / 10}% - 10px)`,
            boxShadow: "0 0 5px #ab5ab7",
            backgroundColor: "#ab5ab7",
          }}
        />
      </div>
      <div className="text-right mt-1">
        <span className="text-lg font-bold text-ab5ab7">
          {(threshold / 10).toFixed(1)}%
        </span>
      </div>
    </div>
  );
};

export default ThresholdSelector;
