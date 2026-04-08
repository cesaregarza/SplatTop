import React, { Suspense } from "react";
import { useTranslation } from "react-i18next";
import Loading from "../misc_components/loading";

const RegionSelector = React.lazy(() =>
  import("../top500_components/selectors/region_selector")
);
const ModeSelector = React.lazy(() =>
  import("../top500_components/selectors/mode_selector")
);
const WeaponSelector = React.lazy(() => import("./weapon_selector"));
const ThresholdSelector = React.lazy(() => import("./threshold_selector"));
const SeasonSelector = React.lazy(() => import("./season_selector"));

const controlLabelClass =
  "mb-2 block text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-gray-400";

const segmentedButtonClass = (isSelected) =>
  `rounded-md border px-3 py-2 text-sm font-medium transition ${
    isSelected
      ? "border-purple-500/60 bg-purple-950/40 text-white"
      : "border-gray-800 bg-gray-950/70 text-gray-200 hover:border-gray-700 hover:bg-gray-900"
  }`;

const ControlSection = ({ label, children, className = "" }) => (
  <div className={className}>
    <p className={controlLabelClass}>{label}</p>
    {children}
  </div>
);

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
  dedupePlayers,
  toggleDedupePlayers,
  selectedSeason,
  setSelectedSeason,
  compareEnabled,
  toggleCompare,
  localizedWeaponTranslations,
  weaponReferenceData,
}) => {
  const { t } = useTranslation("weapon_leaderboard");
  const weaponReferenceDataById = React.useMemo(() => {
    if (!weaponReferenceData) {
      return {};
    }

    return Object.entries(weaponReferenceData).reduce((acc, [key, value]) => {
      if (key === value.reference_id.toString()) {
        acc[key] = value;
      }
      return acc;
    }, {});
  }, [weaponReferenceData]);

  if (
    !weaponReferenceDataById ||
    Object.keys(weaponReferenceDataById).length === 0 ||
    !localizedWeaponTranslations
  ) {
    return <Loading text={t("loading")} />;
  }

  return (
    <Suspense fallback={<Loading text={t("loading")} />}>
      <section className="rounded-lg border border-gray-800 bg-gray-950/70 p-3 sm:p-4">
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1.7fr)_minmax(0,1.35fr)_minmax(0,1.35fr)]">
          <ControlSection label={t("controls.region")}>
            <RegionSelector
              selectedRegion={selectedRegion}
              setSelectedRegion={setSelectedRegion}
              showTitle={false}
              showLabels={true}
              buttonVariant="utility"
              buttonPadding="px-3 py-2"
              imageWidth="w-7"
              imageHeight="h-7"
              baseClass="w-full"
            />
          </ControlSection>

          <ControlSection label={t("controls.mode")}>
            <ModeSelector
              selectedMode={selectedMode}
              setSelectedMode={setSelectedMode}
              showTitle={false}
              showLabels={true}
              buttonVariant="utility"
              buttonPadding="px-3 py-2"
              imageWidth="w-7"
              imageHeight="h-7"
              baseClass="w-full"
              equalWidthButtons={true}
              autoFitEqualWidth={true}
            />
          </ControlSection>

          <ControlSection label={t("controls.weapon")}>
            <WeaponSelector
              onWeaponSelect={setWeaponId}
              weaponReferenceData={weaponReferenceDataById}
              weaponTranslations={localizedWeaponTranslations}
              initialWeaponId={weaponId}
              className="w-full"
            />
          </ControlSection>

          <ControlSection label={t("controls.compare")}>
            {compareEnabled ? (
              <div className="space-y-2">
                <WeaponSelector
                  onWeaponSelect={setAdditionalWeaponId}
                  weaponReferenceData={weaponReferenceDataById}
                  weaponTranslations={localizedWeaponTranslations}
                  initialWeaponId={additionalWeaponId}
                  allowNull={true}
                  className="w-full"
                />
                <button
                  onClick={toggleCompare}
                  className="w-full rounded-md border border-gray-800 bg-gray-950/70 px-3 py-2 text-sm text-gray-300 hover:border-gray-700 hover:bg-gray-900 hover:text-white"
                >
                  {t("controls.compare_disable")}
                </button>
              </div>
            ) : (
              <button
                onClick={toggleCompare}
                className="w-full rounded-md border border-gray-800 bg-gray-950/70 px-3 py-3 text-sm font-medium text-gray-200 hover:border-gray-700 hover:bg-gray-900 hover:text-white"
              >
                {t("controls.compare_enable")}
              </button>
            )}
          </ControlSection>
        </div>

        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1.05fr)_minmax(0,1.15fr)_minmax(0,1fr)]">
          <ControlSection label={t("controls.usage_threshold")}>
            <ThresholdSelector
              threshold={threshold}
              setThreshold={setThreshold}
            />
          </ControlSection>

          <ControlSection label={t("controls.metric")}>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => {
                  if (finalResults) {
                    toggleFinalResults();
                  }
                }}
                className={segmentedButtonClass(!finalResults)}
                aria-pressed={!finalResults}
              >
                {t("peak_x_power")}
              </button>
              <button
                onClick={() => {
                  if (!finalResults) {
                    toggleFinalResults();
                  }
                }}
                className={segmentedButtonClass(finalResults)}
                aria-pressed={finalResults}
              >
                {t("final_x_power")}
              </button>
            </div>
          </ControlSection>

          <ControlSection label={t("controls.entries")}>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => {
                  if (dedupePlayers) {
                    toggleDedupePlayers();
                  }
                }}
                className={segmentedButtonClass(!dedupePlayers)}
                aria-pressed={!dedupePlayers}
              >
                {t("show_all")}
              </button>
              <button
                onClick={() => {
                  if (!dedupePlayers) {
                    toggleDedupePlayers();
                  }
                }}
                className={segmentedButtonClass(dedupePlayers)}
                aria-pressed={dedupePlayers}
              >
                {t("dedupe_data")}
              </button>
            </div>
          </ControlSection>

          <ControlSection label={t("controls.season")}>
            <SeasonSelector
              selectedSeason={selectedSeason}
              setSelectedSeason={setSelectedSeason}
              className="w-full"
            />
          </ControlSection>
        </div>
      </section>
    </Suspense>
  );
};

export default WeaponLeaderboardControls;
