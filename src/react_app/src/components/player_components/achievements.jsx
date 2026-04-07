import React from "react";
import { useTranslation } from "react-i18next";
import TakorokaIcon from "../../assets/icons/takoroka.png";
import TentatekIcon from "../../assets/icons/tentatek.png";
import { modeKeyMap } from "../constants";
import { getSeasonName } from "../utils/season_utils";
import { getCareerHighlights } from "./playerPageUtils";

const metricClassName =
  "rounded-md border border-gray-800/80 bg-black/20 px-3 py-2";

const formatBestFinish = (value) => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }

  return `#${value}`;
};

const Achievements = ({ data }) => {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const highlights = getCareerHighlights(data) || {
    totalTop10: 0,
    totalTop500: 0,
    diamondSeasonCount: 0,
    bestFinish: null,
    bestMode: null,
    notableSeasons: [],
  };

  const metrics = [
    {
      label: t("highlights.metrics.top10"),
      value: highlights.totalTop10,
    },
    {
      label: t("highlights.metrics.top500"),
      value: highlights.totalTop500,
    },
    {
      label: t("highlights.metrics.diamonds"),
      value: highlights.diamondSeasonCount,
      hint: t("highlights.metrics.diamonds_hint"),
    },
    {
      label: t("highlights.metrics.best_finish"),
      value: formatBestFinish(highlights.bestFinish),
    },
    {
      label: t("highlights.metrics.best_mode"),
      value: highlights.bestMode ? g(modeKeyMap[highlights.bestMode]) : "--",
    },
  ];

  return (
    <section className="rounded-lg border border-gray-800/60 bg-gray-950/25 p-4">
      <div className="mb-3 border-b border-gray-800/60 pb-3">
        <h2 className="text-lg font-semibold text-white">
          {t("highlights.title")}
        </h2>
        <p className="mt-1 text-sm text-gray-400">
          {t("highlights.subtitle")}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {metrics.map((metric) => (
          <div key={metric.label} className={metricClassName}>
            <p className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
              <span>{metric.label}</span>
              {metric.hint ? (
                <abbr
                  title={metric.hint}
                  aria-label={metric.hint}
                  className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-gray-700 text-[10px] font-bold text-gray-400 no-underline"
                >
                  ?
                </abbr>
              ) : null}
            </p>
            <p className="mt-1 text-sm font-medium text-white tabular-nums">
              {metric.value}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4 border-t border-gray-800/60 pt-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">
            {t("highlights.notable_title")}
          </h3>
          <span className="text-xs text-gray-600 tabular-nums">
            {highlights.notableSeasons.length}
          </span>
        </div>
        {highlights.notableSeasons.length === 0 ? (
          <p className="text-sm text-gray-500">{t("highlights.no_notable")}</p>
        ) : (
          <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
            {highlights.notableSeasons.map((season) => (
              <div
                key={season.season_number}
                className="rounded-md border border-gray-800/70 bg-black/10 px-3 py-3"
              >
                <div className="flex items-center gap-2">
                  <img
                    src={season.region ? TakorokaIcon : TentatekIcon}
                    alt={season.region ? "Takoroka" : "Tentatek"}
                    className="h-6 w-6 shrink-0"
                  />
                  <span className="font-medium text-white">
                    {getSeasonName(season.season_number - 1, g)}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-300">
                  {season.finishes
                    .map((finish) => `${finish.shortLabel} #${finish.rank}`)
                    .join(" · ")}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

export default Achievements;
