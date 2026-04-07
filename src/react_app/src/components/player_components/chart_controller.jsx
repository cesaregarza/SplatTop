import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import ModeSelector from "../top500_components/selectors/mode_selector";
import XChart from "./xchart";
import WeaponsChart from "./weapons";
import SeasonSelector from "./season_selector";
import SeasonResults from "./season_results";
import SeasonArchive from "./season_archive";
import {
  getAvailableDisplaySeasons,
  getDefaultPlayerMode,
  getModeAnalysisSummary,
  getDefaultSelectedDisplaySeason,
} from "./playerPageUtils";
import { modeKeyMap } from "../constants";
import { calculateSeasonNow, getSeasonName } from "../utils/season_utils";

function ChartController({
  data,
  modes,
  weaponTranslations,
  weaponReferenceData,
}) {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const [mode, setMode] = useState(() =>
    getDefaultPlayerMode(data.player_data, modes)
  );
  const [selectedSeason, setSelectedSeason] = useState(() =>
    getDefaultSelectedDisplaySeason(
      data,
      getDefaultPlayerMode(data.player_data, modes)
    )
  );
  const [colorMode, setColorMode] = useState("Seasonal");
  const [selectedSeasons, setSelectedSeasons] = useState([]);

  const allowedModes = modes.map((currentMode) =>
    data.player_data.some((entry) => entry.mode === currentMode)
  );

  useEffect(() => {
    if (!allowedModes[modes.indexOf(mode)]) {
      setMode(getDefaultPlayerMode(data.player_data, modes));
    }
  }, [allowedModes, data.player_data, mode, modes]);

  useEffect(() => {
    const availableSeasons = getAvailableDisplaySeasons(data);
    if (availableSeasons.length > 0 && !availableSeasons.includes(selectedSeason)) {
      setSelectedSeason(getDefaultSelectedDisplaySeason(data, mode));
    }
  }, [data, mode, selectedSeason]);

  const filterBySeasonAndMode = (rows) => {
    if (selectedSeasons.length === 0) {
      return rows.filter((entry) => entry.mode === mode);
    }

    return rows.filter(
      (entry) =>
        entry.mode === mode && selectedSeasons.includes(entry.season_number)
    );
  };

  const filteredAggregatedData = {
    weapon_counts: filterBySeasonAndMode(data.aggregated_data.weapon_counts),
    weapon_winrate: filterBySeasonAndMode(data.aggregated_data.weapon_winrate),
  };
  const selectedModeLabel = g(modeKeyMap[mode]);
  const selectedSeasonLabel = getSeasonName(selectedSeason - 1, g);
  const analysisSummary = getModeAnalysisSummary(data, mode, selectedSeason);
  const isCurrentSeason = selectedSeason === calculateSeasonNow() + 1;
  const seasonToolbar = (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[13rem] flex-1">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
            {t("controller.mode")}
          </span>
          <ModeSelector
            selectedMode={mode}
            setSelectedMode={setMode}
            allowedModes={allowedModes}
            showTitle={false}
            baseClass="w-auto"
            buttonPadding="px-2.5 py-1.5"
            imageWidth="w-5"
            imageHeight="h-5"
            showLabels={true}
            buttonVariant="utility"
          />
        </div>
        <div className="min-w-[10rem]">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
            {t("controller.color")}
          </span>
          <div
            className="inline-flex rounded-md border border-gray-800 bg-black/20 p-1"
            title={t("controller.color_hint")}
          >
            {["Seasonal", "Accessible"].map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setColorMode(option)}
                className={`rounded px-3 py-1.5 text-sm font-medium transition ${
                  colorMode === option
                    ? "bg-purple-950/50 text-purple-100"
                    : "text-gray-300 hover:bg-gray-900 hover:text-white"
                }`}
                aria-pressed={colorMode === option}
              >
                {option === "Seasonal"
                  ? t("controller.seasonal")
                  : t("controller.accessible")}
              </button>
            ))}
          </div>
        </div>
        <div className="min-w-[13rem] flex-1">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
            {t("controller.weapon_seasons")}
          </span>
          <SeasonSelector
            compact={true}
            data={data.aggregated_data}
            mode={mode}
            onSeasonChange={setSelectedSeasons}
          />
        </div>
      </div>
      <p className="text-xs text-gray-500">
        {t("controller.color_hint")}
      </p>
    </div>
  );

  return (
    <div className="space-y-4 pb-24">
      <SeasonResults
        data={data}
        weaponReferenceData={weaponReferenceData}
        headerControls={seasonToolbar}
        activeSeason={selectedSeason}
        onSeasonChange={setSelectedSeason}
      />
      <SeasonArchive
        data={data}
        mode={mode}
        activeSeason={selectedSeason}
        onSeasonChange={setSelectedSeason}
      />
      <section className="rounded-lg border border-gray-800/60 bg-gray-950/25">
        <div className="flex flex-col gap-3 border-b border-gray-800/60 px-4 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">
              {t("sections.mode_analysis")}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-white">
                {selectedSeasonLabel}
              </h2>
              {isCurrentSeason ? (
                <span className="rounded-full border border-purple-500/50 bg-purple-950/40 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-purple-100">
                  {t("xchart.live_indicator")}
                </span>
              ) : null}
              <span className="text-sm text-gray-400">{selectedModeLabel}</span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-gray-500 sm:justify-end">
            <span className="rounded-full border border-gray-800 bg-black/20 px-2.5 py-1">
              {t(
                colorMode === "Seasonal"
                  ? "controller.seasonal"
                  : "controller.accessible"
              )}
            </span>
            <span className="rounded-full border border-gray-800 bg-black/20 px-2.5 py-1">
              {selectedModeLabel}
            </span>
          </div>
        </div>
        <div className="px-4 py-3">
          <XChart
            data={data.player_data}
            mode={mode}
            colorMode={colorMode}
            selectedSeason={selectedSeason}
            analysisSummary={analysisSummary}
          />
        </div>
        <div className="border-t border-gray-800/60 px-4 py-3">
          <WeaponsChart
            data={filteredAggregatedData}
            mode={mode}
            colorMode={colorMode}
            weaponTranslations={weaponTranslations}
            weaponReferenceData={weaponReferenceData}
          />
        </div>
      </section>
    </div>
  );
}

export default ChartController;
