import React, { Suspense } from "react";
import { useTranslation } from "react-i18next";
import Loading from "../misc_components/loading";
import { useWeaponAndTranslation } from "../utils/weaponAndTranslation";
import { FaExchangeAlt } from "react-icons/fa";

const RegionSelector = React.lazy(() =>
  import("../top500_components/selectors/region_selector")
);
const ModeSelector = React.lazy(() =>
  import("../top500_components/selectors/mode_selector")
);
const WeaponSelector = React.lazy(() => import("./weapon_selector"));
const ThresholdSelector = React.lazy(() => import("./threshold_selector"));

const WeaponLeaderboardControls = ({
  selectedRegion,
  setSelectedRegion,
  selectedMode,
  setSelectedMode,
  weaponId,
  setWeaponId,
  additionalWeaponId,
  setAdditionalWeaponId,
  threshold,
  setThreshold,
  finalResults,
  toggleFinalResults,
  handleSwapWeapons,
}) => {
  const { t } = useTranslation("main_page");
  const { t: pl } = useTranslation("player");
  const {
    weaponTranslations,
    weaponReferenceData,
    isLoading: isWeaponDataLoading,
    error: weaponDataError,
  } = useWeaponAndTranslation();

  const weaponReferenceDataById = React.useMemo(() => {
    if (!weaponReferenceData) return {};
    return Object.entries(weaponReferenceData).reduce((acc, [key, value]) => {
      if (key === value.reference_id.toString()) {
        acc[key] = value;
      }
      return acc;
    }, {});
  }, [weaponReferenceData]);

  if (isWeaponDataLoading) {
    return <Loading text={t("loading")} />;
  }

  if (weaponDataError) {
    return <div className="text-red-500">{weaponDataError.message}</div>;
  }

  return (
    <Suspense fallback={<Loading text={t("loading")} />}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div className="flex flex-col items-center">
          <RegionSelector
            selectedRegion={selectedRegion}
            setSelectedRegion={setSelectedRegion}
          />
        </div>
        <div className="flex flex-col items-center">
          <ModeSelector
            selectedMode={selectedMode}
            setSelectedMode={setSelectedMode}
          />
        </div>
      </div>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-2 sm:mb-4">
        {weaponReferenceDataById && weaponTranslations && (
          <>
            <div className="flex flex-col items-center">
              <span className="mb-2 text-center text-lg font-semibold text-purple-400">
                {t("weapon_select_main")}
              </span>
              <WeaponSelector
                onWeaponSelect={setWeaponId}
                weaponReferenceData={weaponReferenceDataById}
                weaponTranslations={weaponTranslations[pl("data_lang_key")]}
                initialWeaponId={weaponId}
              />
            </div>
            <button
              onClick={handleSwapWeapons}
              className={`bg-purple-500 hover:bg-purple-700 text-white font-bold p-2 rounded my-2 sm:my-0 ${
                additionalWeaponId === null
                  ? "opacity-50 cursor-not-allowed"
                  : ""
              }`}
              aria-label="Swap weapons"
              disabled={additionalWeaponId === null}
            >
              <FaExchangeAlt />
            </button>
            <div className="flex flex-col items-center">
              <span className="mb-2 text-center text-lg font-semibold text-purple-400">
                {t("weapon_select_alt")}
              </span>
              <WeaponSelector
                onWeaponSelect={setAdditionalWeaponId}
                weaponReferenceData={weaponReferenceDataById}
                weaponTranslations={weaponTranslations[pl("data_lang_key")]}
                initialWeaponId={additionalWeaponId}
                allowNull={true}
              />
            </div>
          </>
        )}
      </div>
      <ThresholdSelector threshold={threshold} setThreshold={setThreshold} />
      <div className="flex flex-col justify-center items-center mb-4 sm:mb-6">
        <label
          htmlFor="toggleFinalResults"
          className="inline-flex items-center cursor-pointer flex-col"
        >
          <div className="flex items-center">
            <span
              className={`text-sm font-medium mr-2 ${
                !finalResults ? "highlighted-option" : ""
              }`}
            >
              {t("weapon_leaderboard.peak_x_power")}
            </span>
            <div className="relative" title="Change the scale type">
              <input
                type="checkbox"
                id="toggleFinalResults"
                className="sr-only peer"
                checked={finalResults}
                onChange={toggleFinalResults}
              />
              <div
                className={`w-11 h-6 rounded-full peer peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5 ${
                  finalResults ? "bg-purple" : "bg-gray-600"
                }`}
              ></div>
            </div>
            <span
              className={`text-sm font-medium ml-2 ${
                finalResults ? "highlighted-option" : ""
              }`}
            >
              {t("weapon_leaderboard.final_x_power")}
            </span>
          </div>
        </label>
      </div>
    </Suspense>
  );
};

export default WeaponLeaderboardControls;
