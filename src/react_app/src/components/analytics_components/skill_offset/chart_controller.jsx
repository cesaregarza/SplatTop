import React from "react";
import { useTranslation } from "react-i18next";
import { modes } from "../../constants";

const ALL_SLICE_KEY = "all";
const regions = ["Tentatek", "Takoroka"];

function SkillOffsetChartController({
  logarithmic,
  toggleLogarithmic,
  selectedMode,
  setSelectedMode,
  selectedRegion,
  setSelectedRegion,
}) {
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
          <div className="grid w-full max-w-3xl grid-cols-1 gap-4 px-4 pt-6 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-left text-sm font-medium">
              <span>{t("skill_offset.controller.mode_slice")}</span>
              <select
                className="rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white"
                value={selectedMode}
                onChange={(event) => setSelectedMode(event.target.value)}
              >
                <option value={ALL_SLICE_KEY}>
                  {t("skill_offset.controller.all_modes")}
                </option>
                {modes.map((mode) => (
                  <option key={mode} value={mode}>
                    {mode}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2 text-left text-sm font-medium">
              <span>{t("skill_offset.controller.region_slice")}</span>
              <select
                className="rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white"
                value={selectedRegion}
                onChange={(event) => setSelectedRegion(event.target.value)}
              >
                <option value={ALL_SLICE_KEY}>
                  {t("skill_offset.controller.all_regions")}
                </option>
                {regions.map((region) => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SkillOffsetChartController;
