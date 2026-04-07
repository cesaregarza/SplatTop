import React, { useState, useEffect } from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts/highstock";
import HighchartsMore from "highcharts/highcharts-more";
import { getPercentageInSeason, getSeasonName } from "../utils/season_utils";
import {
  filterAndProcessData,
  getFiniteSeasonPoints,
  getHistoricalRangeBandData,
  getSeasonColor,
  getAccessibleColor,
  getVisibleSeasonMax,
} from "./xchart_helper_functions";
import fetchFestivalDates from "./splatfest_retriever";
import { useTranslation } from "react-i18next";
import { modeKeyMap } from "../constants";
import { getRawSeasonNumber } from "./playerPageUtils";
import "./xchart.css";

HighchartsMore(Highcharts);

const formatMetricValue = (value, digits = 0, prefix = "") => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }

  return `${prefix}${digits > 0 ? value.toFixed(digits) : value.toString()}`;
};

const formatSeasonElapsed = (value) => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }

  return `${Math.round(value)}%`;
};

const XChart = (props) => {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const [festivalDates, setFestivalDates] = useState(null);

  useEffect(() => {
    const fetchDates = async () => {
      try {
        const dates = await fetchFestivalDates();
        setFestivalDates(dates);
      } catch (error) {
        console.error("Error fetching festival dates:", error);
      }
    };

    fetchDates();
  }, []);

  const { analysisSummary, data, mode, colorMode, selectedSeason } = props;
  const modeName = g(modeKeyMap[mode]);
  const { currentSeason, processedData } = filterAndProcessData(
    data,
    mode,
    true,
    festivalDates
  );
  const selectedRawSeason = getRawSeasonNumber(selectedSeason);
  const selectedSeasonData =
    processedData.find((seasonData) => seasonData.season === selectedRawSeason) ||
    null;
  const selectedSeasonPoints = getFiniteSeasonPoints(selectedSeasonData);

  const currentPercentage = getPercentageInSeason(new Date(), currentSeason);
  const visibleMax = getVisibleSeasonMax(
    Boolean(analysisSummary?.isCurrent),
    currentPercentage
  );
  const historicalBandData = getHistoricalRangeBandData(
    processedData,
    selectedRawSeason,
    visibleMax
  );
  const chartHeight = analysisSummary?.isSparse ? 260 : 300;
  const showSparseStats = Boolean(analysisSummary?.isSparse);
  const chartTitle = selectedSeasonData
    ? getSeasonName(selectedSeasonData.season, g)
    : t("xchart.title").replace("%MODE%", modeName);
  const statItems = [
    {
      label: t("analysis.stats.current_xp"),
      value: formatMetricValue(analysisSummary?.currentXp, 1),
    },
    {
      label: t("analysis.stats.peak_xp"),
      value: formatMetricValue(analysisSummary?.peakXp, 1),
    },
    {
      label: t("analysis.stats.rank"),
      value: formatMetricValue(analysisSummary?.rank, 0, "#"),
    },
    {
      label: t("analysis.stats.season_elapsed"),
      value: formatSeasonElapsed(analysisSummary?.seasonElapsed),
    },
    {
      label: t("analysis.stats.tracked_updates"),
      value: formatMetricValue(analysisSummary?.trackedUpdates),
    },
  ];

  const options = {
    chart: {
      zoomType: "x",
      height: chartHeight,
      backgroundColor: "transparent",
      spacingTop: 8,
    },
    accessibility: {
      enabled: false,
    },
    title: {
      text: null,
    },
    subtitle: {
      text: null,
    },
    xAxis: {
      title: {
        text: t("xchart.xaxis.title"),
        style: {
          color: "#ffffff",
        },
      },
      crosshair: true,
      labels: {
        style: {
          color: "#ffffff",
        },
        formatter: function () {
          if (this.value === 0) {
            return t("xchart.xaxis.start");
          } else if (this.value === 100) {
            return t("xchart.xaxis.end");
          } else {
            return `${this.value}%`;
          }
        },
      },
      gridLineColor: "rgba(255, 255, 255, 0.1)",
      plotLines:
        analysisSummary?.isCurrent
          ? [
              {
                color: "rgba(255, 255, 255, 0.4)",
                width: 2,
                value: currentPercentage,
                dashStyle: "Dash",
                label: {
                  text: t("xchart.now"),
                  align: "left",
                  style: {
                    color: "rgba(255, 255, 255, 0.8)",
                  },
                },
              },
            ]
          : [],
      min: 0,
      max: visibleMax,
    },
    yAxis: {
      title: {
        text: t("xchart.yaxis.title"),
        style: {
          color: "#ffffff",
        },
      },
      labels: {
        style: {
          color: "#ffffff",
        },
        formatter: function () {
          if (this.value >= 1000) {
            return `${(this.value / 1000).toFixed(1)}k`;
          } else {
            return this.value;
          }
        },
      },
      gridLineColor: "rgba(255, 255, 255, 0.1)",
    },
    tooltip: {
      shared: false,
      formatter: function () {
        if (analysisSummary?.isCurrent && this.y != null) {
          return `<b>${chartTitle}</b>: ${this.y}`;
        }
        return this.y != null ? `<b>${chartTitle}</b>: ${this.y}` : false;
      },
    },
    plotOptions: {
      series: {
        marker: {
          enabled: false,
        },
      },
    },
    series: [
      ...(historicalBandData.length > 0
        ? [
            {
              type: "arearange",
              name: t("analysis.legend.historical_range"),
              data: historicalBandData,
              color: "rgba(148, 163, 184, 0.16)",
              fillOpacity: 0.16,
              lineWidth: 0,
              enableMouseTracking: false,
              zIndex: 1,
            },
          ]
        : []),
      ...(selectedSeasonData
        ? [
            {
              name: chartTitle,
              data: selectedSeasonData.dataPoints.map((point) => [point.x, point.y]),
              color:
                colorMode === "Seasonal"
                  ? getSeasonColor(
                      selectedSeasonData.season,
                      selectedSeasonData.isCurrent
                    )
                  : getAccessibleColor(selectedSeasonData.season),
              zIndex: 10,
              lineWidth: 4,
              enableMouseTracking: true,
              marker: {
                enabled: selectedSeasonPoints.length <= 3,
                radius: 4,
                states: {
                  hover: {
                    enabled: true,
                  },
                },
              },
            },
          ]
        : []),
    ],
    legend: {
      enabled: false,
    },
  };

  return (
    <div className="space-y-3">
      {showSparseStats ? (
        <div className="grid gap-2 sm:grid-cols-5">
          {statItems.map((item) => (
            <div
              key={item.label}
              className="rounded-md border border-gray-800/70 bg-black/15 px-3 py-2"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
                {item.label}
              </p>
              <p className="mt-1 text-sm font-medium text-white tabular-nums">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
        <span className="flex items-center gap-2">
          <span
            className="h-0.5 w-6 rounded-full"
            style={{
              backgroundColor:
                colorMode === "Seasonal"
                  ? getSeasonColor(
                      selectedSeasonData?.season ?? selectedRawSeason,
                      Boolean(selectedSeasonData?.isCurrent)
                    )
                  : getAccessibleColor(selectedSeasonData?.season ?? selectedRawSeason),
            }}
          ></span>
          <span>{t("analysis.legend.selected_run")}</span>
        </span>
        {historicalBandData.length > 0 ? (
          <span className="flex items-center gap-2">
            <span className="h-3 w-6 rounded-sm bg-slate-400/30"></span>
            <span>{t("analysis.legend.historical_range")}</span>
          </span>
        ) : null}
      </div>
      <HighchartsReact highcharts={Highcharts} options={options} />
    </div>
  );
};

export default XChart;
