import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import TakorokaIcon from "../../assets/icons/takoroka.png";
import TentatekIcon from "../../assets/icons/tentatek.png";
import { getSeasonName } from "../utils/season_utils";
import { getSeasonArchiveSections } from "./playerPageUtils";

const RegionBadge = ({ region }) => (
  <img
    src={region ? TakorokaIcon : TentatekIcon}
    alt={region ? "Takoroka" : "Tentatek"}
    className="h-6 w-6 shrink-0"
  />
);

const Sparkline = ({ values, active }) => {
  if (!values || values.length < 2) {
    return <span className="text-xs text-gray-600">--</span>;
  }

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valueRange = maxValue - minValue || 1;
  const pointWidth = 100 / (values.length - 1);
  const points = values
    .map((value, index) => {
      const x = index * pointWidth;
      const y = 22 - ((value - minValue) / valueRange) * 18;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      viewBox="0 0 100 24"
      className="h-6 w-full overflow-visible"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <polyline
        fill="none"
        stroke={active ? "#d8b4fe" : "#94a3b8"}
        strokeWidth="2"
        points={points}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

const formatPeakXp = (value) => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }

  return value.toFixed(1);
};

const formatFinish = (rank) => {
  if (typeof rank !== "number" || !Number.isFinite(rank)) {
    return "--";
  }

  return `#${rank}`;
};

const SeasonArchive = ({ data, mode, activeSeason, onSeasonChange }) => {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const [isArchiveOpen, setIsArchiveOpen] = useState(false);
  const { visibleRows, hiddenRows, hasHiddenRows } =
    getSeasonArchiveSections(data, mode, activeSeason);
  const currentDisplaySeason = [...visibleRows, ...hiddenRows].find(
    (row) => row.season_number === activeSeason
  );

  useEffect(() => {
    if (!hasHiddenRows && isArchiveOpen) {
      setIsArchiveOpen(false);
    }
  }, [hasHiddenRows, isArchiveOpen]);

  const renderRow = (row) => {
    const isActive = row.season_number === activeSeason;

    return (
      <button
        key={row.season_number}
        type="button"
        onClick={() =>
          typeof onSeasonChange === "function"
            ? onSeasonChange(row.season_number)
            : null
        }
        className={`grid w-full gap-3 rounded-md border px-3 py-3 text-left transition md:grid-cols-[minmax(0,1.3fr)_5rem_4.5rem_minmax(0,1fr)] md:items-center ${
          isActive
            ? "border-purple-500/60 bg-purple-950/30"
            : "border-gray-800/80 bg-black/10 hover:border-gray-700 hover:bg-gray-900/60"
        } ${!row.hasModeData ? "opacity-70" : ""}`}
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <RegionBadge region={row.region} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-white">
                  {getSeasonName(row.raw_season_number, g)}
                </span>
                {row.season_number === activeSeason ? (
                  <span className="rounded-full border border-purple-500/50 bg-purple-950/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-purple-100">
                    {t("archive.selected")}
                  </span>
                ) : null}
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {row.hasModeData
                  ? t("archive.row_hint")
                  : t("archive.no_mode_data")}
              </p>
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500 md:hidden">
            {t("archive.table.peak_xp")}
          </p>
          <p className="font-medium tabular-nums text-white">
            {formatPeakXp(row.peakXp)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500 md:hidden">
            {t("archive.table.finish")}
          </p>
          <p
            className={`font-medium tabular-nums ${
              row.finishRank && row.finishRank <= 10
                ? "text-purple-200"
                : "text-gray-200"
            }`}
          >
            {formatFinish(row.finishRank)}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500 md:hidden">
            {t("archive.table.progression")}
          </p>
          <Sparkline values={row.sparklineValues} active={isActive} />
        </div>
      </button>
    );
  };

  return (
    <section className="rounded-lg border border-gray-800/60 bg-gray-950/25">
      <div className="flex flex-col gap-2 border-b border-gray-800/60 px-4 py-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">
            {t("sections.season_archive")}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-white">
            {t("archive.title")}
          </h2>
        </div>
        <p className="text-xs text-gray-500">
          {currentDisplaySeason
            ? `${t("archive.selected_hint").replace(
                "%SEASON%",
                getSeasonName(currentDisplaySeason.raw_season_number, g)
              )}${
                currentDisplaySeason.hasModeData
                  ? ""
                  : ` \u00b7 ${t("archive.no_mode_data")}`
              }`
            : t("archive.empty_hint")}
        </p>
      </div>

      <div className="px-4 py-3">
        <div className="hidden grid-cols-[minmax(0,1.3fr)_5rem_4.5rem_minmax(0,1fr)] gap-3 border-b border-gray-800/60 pb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500 md:grid">
          <span>{t("archive.table.season")}</span>
          <span className="text-right">{t("archive.table.peak_xp")}</span>
          <span className="text-right">{t("archive.table.finish")}</span>
          <span>{t("archive.table.progression")}</span>
        </div>
        <div className="space-y-2 pt-2">
          {visibleRows.map(renderRow)}
          {isArchiveOpen ? hiddenRows.map(renderRow) : null}
        </div>
        {hasHiddenRows ? (
          <div className="pt-3">
            <button
              type="button"
              onClick={() => setIsArchiveOpen((currentValue) => !currentValue)}
              className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400 transition hover:text-gray-200"
            >
              {isArchiveOpen
                ? t("archive.hide_more")
                : t("archive.show_more").replace(
                    "%COUNT%",
                    hiddenRows.length.toString()
                  )}
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
};

export default SeasonArchive;
