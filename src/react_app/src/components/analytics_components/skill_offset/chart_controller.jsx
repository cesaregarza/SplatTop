import React from "react";
import { useTranslation } from "react-i18next";

function SkillOffsetChartController({ logarithmic, toggleLogarithmic }) {
  const { t } = useTranslation("analytics");

  return (
    <div className="pb-24">
      <div className="relative controls-box border-2 border-gray-200 rounded-lg py-4 px-1 mt-5">
        <div className="absolute bg-gray-900">
          <h2 className="text-lg font-semibold rounded-xs">
            {t("skill_offset.controller.title")}
          </h2>
        </div>
        <div className="flex flex-col justify-center items-center">
          <label
            htmlFor="toggleLogarithmic"
            className="inline-flex items-center cursor-pointer flex-col"
          >
            <span className="text-sm font-medium mb-2">
              {t("skill_offset.controller.linlog.label")}
            </span>
            <div className="flex items-center">
              <span
                className={`text-sm font-medium mr-2 ${
                  !logarithmic ? "highlighted-option" : ""
                }`}
              >
                {t("skill_offset.controller.linear")}
              </span>
              <div className="relative" title="Change the scale type">
                <input
                  type="checkbox"
                  id="toggleLogarithmic"
                  className="sr-only peer"
                  checked={logarithmic}
                  onChange={toggleLogarithmic}
                />
                <div
                  className={`w-11 h-6 rounded-full peer peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5 ${
                    logarithmic ? "bg-purple" : "bg-gray-600"
                  }`}
                ></div>
              </div>
              <span
                className={`text-sm font-medium ml-2 ${
                  logarithmic ? "highlighted-option" : ""
                }`}
              >
                {t("skill_offset.controller.logarithmic")}
              </span>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}

export default SkillOffsetChartController;
