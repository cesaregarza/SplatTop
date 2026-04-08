import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";
import { useTranslation } from "react-i18next";
import Loading from "./misc_components/loading";
import useFetchWithCache from "./top500_components/fetch_with_cache";
import { modeKeyMap } from "./constants";
import { getBaseApiUrl } from "./utils";
import { getPercentageInSeason, getSeasonName } from "./utils/season_utils";

const currentPalette = [
  "#f472b6",
  "#38bdf8",
  "#f59e0b",
  "#34d399",
  "#c084fc",
  "#fb7185",
  "#60a5fa",
  "#facc15",
];

const formatXp = (value) =>
  typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(1)
    : "--";

const formatDate = (value) => {
  if (!value) {
    return "--";
  }

  return new Date(value).toLocaleString("default", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
};

const clampPercent = (value) => Math.max(0, Math.min(100, value));

const RaceTo5000 = () => {
  const { t } = useTranslation("main_page");
  const { t: g } = useTranslation("game");
  const apiUrl = getBaseApiUrl();
  const endpoint = `${apiUrl}/api/race-to-5000`;
  const { data, error, isLoading } = useFetchWithCache(endpoint);

  const chartData = useMemo(() => {
    const currentRuns = data?.current_runs || [];
    const historicalRuns = data?.historical_runs || [];
    const currentSeason = data?.current_season;
    const nowPercent = currentSeason
      ? clampPercent(getPercentageInSeason(new Date(), currentSeason))
      : null;

    const currentSeries = currentRuns.map((run, index) => ({
      type: "line",
      name: `${run.splashtag} · ${
        g(modeKeyMap[run.mode], { defaultValue: run.mode }) || run.mode
      } · ${run.region}`,
      data: (run.points || [])
        .map((point) => [
          clampPercent(getPercentageInSeason(point.timestamp, run.season_number)),
          point.x_power,
        ])
        .sort((left, right) => left[0] - right[0]),
      color: currentPalette[index % currentPalette.length],
      lineWidth: 3,
      zIndex: 10 + index,
      marker: {
        enabled: (run.points || []).length <= 3,
        radius: 3,
      },
      custom: {
        playerId: run.player_id,
        mode: run.mode,
        region: run.region,
        peakXp: run.peak_x_power,
      },
    }));

    const historicalSeries = historicalRuns.map((run) => ({
      type: "line",
      name: `${run.splashtag} · ${getSeasonName(run.season_number - 1, g)}`,
      data: (run.points || [])
        .map((point) => [
          clampPercent(getPercentageInSeason(point.timestamp, run.season_number)),
          point.x_power,
        ])
        .sort((left, right) => left[0] - right[0]),
      color: "rgba(148, 163, 184, 0.18)",
      lineWidth: 1.5,
      zIndex: 1,
      enableMouseTracking: false,
      states: {
        inactive: {
          opacity: 1,
        },
      },
    }));

    return {
      currentSeason,
      currentSeries,
      historicalSeries,
      nowPercent,
    };
  }, [data, g]);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-950/55 px-4 py-8 text-center">
        <Loading text={t("race.loading", { defaultValue: "Loading race to 5000..." })} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-900/60 bg-red-950/20 px-4 py-6 text-center text-red-300">
        {error.message}
      </div>
    );
  }

  const currentRuns = data?.current_runs || [];
  const historicalRuns = data?.historical_runs || [];
  const currentSeasonLabel = data?.current_season
    ? getSeasonName(data.current_season - 1, g)
    : t("race.current_season_fallback", { defaultValue: "Current season" });

  const chartOptions = {
    chart: {
      backgroundColor: "transparent",
      height: 420,
      spacingTop: 8,
    },
    title: { text: null },
    accessibility: { enabled: false },
    xAxis: {
      min: 0,
      max: 100,
      title: {
        text: t("race.chart.xaxis", { defaultValue: "Season Progress" }),
        style: { color: "#cbd5e1" },
      },
      labels: {
        style: { color: "#94a3b8" },
        formatter: function () {
          if (this.value === 0) return t("race.chart.start", { defaultValue: "Start" });
          if (this.value === 100) return t("race.chart.end", { defaultValue: "End" });
          return `${this.value}%`;
        },
      },
      gridLineColor: "rgba(148, 163, 184, 0.12)",
      plotLines:
        chartData.nowPercent != null
          ? [
              {
                value: chartData.nowPercent,
                color: "rgba(244, 114, 182, 0.4)",
                width: 2,
                dashStyle: "Dash",
                label: {
                  text: t("race.chart.now", { defaultValue: "Now" }),
                  style: { color: "rgba(244, 114, 182, 0.8)" },
                },
              },
            ]
          : [],
    },
    yAxis: {
      title: {
        text: t("race.chart.yaxis", { defaultValue: "X Power" }),
        style: { color: "#cbd5e1" },
      },
      labels: {
        style: { color: "#94a3b8" },
        formatter: function () {
          return this.value >= 1000 ? `${(this.value / 1000).toFixed(1)}k` : this.value;
        },
      },
      gridLineColor: "rgba(148, 163, 184, 0.12)",
    },
    legend: { enabled: false },
    tooltip: {
      shared: false,
      formatter: function () {
        return `<b>${this.series.name}</b><br/>${this.x.toFixed(1)}% · ${this.y.toFixed(1)} XP`;
      },
    },
    plotOptions: {
      series: {
        animation: false,
      },
    },
    series: [...chartData.historicalSeries, ...chartData.currentSeries],
  };

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-gray-800 bg-gray-950/55">
        <div className="border-b border-gray-800 px-4 py-4">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-gray-400">
            {t("race.kicker", { defaultValue: "Live Chase" })}
          </p>
          <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-white">
                {t("race.title", { defaultValue: "Race to 5000" })}
              </h2>
              <p className="mt-2 text-sm text-gray-300">
                {t("race.metadata", {
                  defaultValue:
                    "%season% · %current% contenders over %threshold% XP · %historical% historical %historical_threshold%+ runs",
                })
                  .replace("%season%", currentSeasonLabel)
                  .replace("%current%", currentRuns.length)
                  .replace("%threshold%", data?.current_threshold ?? 4000)
                  .replace("%historical%", historicalRuns.length)
                  .replace(
                    "%historical_threshold%",
                    data?.historical_threshold ?? 5000
                  )}
              </p>
            </div>
            <p className="text-xs text-gray-500">
              {t("race.updated_at", {
                defaultValue: "Updated %DATE%",
              }).replace("%DATE%", formatDate(data?.updated_at))}
            </p>
          </div>
        </div>
        <div className="px-4 py-3">
          {currentRuns.length === 0 && historicalRuns.length === 0 ? (
            <div className="rounded-md border border-gray-800/70 bg-black/15 px-4 py-8 text-center text-gray-400">
              {t("race.empty", {
                defaultValue: "No current-season runs above 4000 XP yet.",
              })}
            </div>
          ) : (
            <>
              <div className="mb-3 flex flex-wrap gap-4 text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                <span className="flex items-center gap-2">
                  <span className="h-3 w-6 rounded-sm bg-slate-400/20"></span>
                  <span>
                    {t("race.legend.historical", {
                      defaultValue: "Historical 5000+ runs",
                    })}
                  </span>
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-0.5 w-6 rounded-full bg-pink-400"></span>
                  <span>
                    {t("race.legend.current", {
                      defaultValue: "Current contenders",
                    })}
                  </span>
                </span>
              </div>
              <HighchartsReact highcharts={Highcharts} options={chartOptions} />
            </>
          )}
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border border-gray-800 bg-gray-950/55">
        <div className="border-b border-gray-800 px-4 py-3">
          <h3 className="text-lg font-semibold text-white">
            {t("race.table.title", { defaultValue: "Current Contenders" })}
          </h3>
          <p className="text-sm text-gray-400">
            {t("race.table.subtitle", {
              defaultValue:
                "Any current-season run over %threshold% XP, regardless of mode.",
            }).replace("%threshold%", data?.current_threshold ?? 4000)}
          </p>
        </div>
        {currentRuns.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-400">
            {t("race.empty", {
              defaultValue: "No current-season runs above 4000 XP yet.",
            })}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[48rem] border-collapse text-white">
              <thead className="border-b border-gray-800 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-400">
                <tr>
                  <th className="px-4 py-2">{t("race.table.player", { defaultValue: "Player" })}</th>
                  <th className="px-4 py-2">{t("race.table.mode", { defaultValue: "Mode" })}</th>
                  <th className="px-4 py-2">{t("race.table.region", { defaultValue: "Region" })}</th>
                  <th className="px-4 py-2 text-right">{t("race.table.current", { defaultValue: "Current" })}</th>
                  <th className="px-4 py-2 text-right">{t("race.table.peak", { defaultValue: "Peak" })}</th>
                  <th className="px-4 py-2 text-right">{t("race.table.updated", { defaultValue: "Updated" })}</th>
                </tr>
              </thead>
              <tbody>
                {currentRuns.map((run) => (
                  <tr
                    key={run.run_id}
                    className="border-b border-gray-900/80 text-sm last:border-b-0"
                  >
                    <td className="px-4 py-3 font-medium text-white">
                      <Link
                        to={`/player/${run.player_id}`}
                        className="transition hover:text-purplelight"
                      >
                        {run.splashtag}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-200">
                      {g(modeKeyMap[run.mode], { defaultValue: run.mode })}
                    </td>
                    <td className="px-4 py-3 text-gray-300">{run.region}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-white">
                      {formatXp(run.current_x_power)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-purple-200">
                      {formatXp(run.peak_x_power)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-400">
                      {formatDate(run.last_updated)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default RaceTo5000;
