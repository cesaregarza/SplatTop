import React, { useState, useEffect } from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts/highstock";
import { getPercentageInSeason, getSeasonName } from "../utils/season_utils";
import {
  filterAndProcessData,
  getSeasonColor,
  getAccessibleColor,
} from "./xchart_helper_functions";
import fetchFestivalDates from "./splatfest_retriever";
import { useTranslation } from "react-i18next";
import { modeKeyMap } from "../constants";
import { getRawSeasonNumber } from "./playerPageUtils";
import "./xchart.css";

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

  const { data, mode, colorMode, selectedSeason } = props;
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

  const currentPercentage = getPercentageInSeason(new Date(), currentSeason);

  const currSeasonIndicator = t("xchart.live_indicator");
  const chartTitle = selectedSeasonData
    ? getSeasonName(selectedSeasonData.season, g) +
      (selectedSeasonData.isCurrent ? ` ${currSeasonIndicator}` : "")
    : t("xchart.title").replace("%MODE%", modeName);
  const chartSubtitle = selectedSeasonData ? modeName : t("no_data");

  const options = {
    chart: {
      zoomType: "x",
      height: 400,
      backgroundColor: "transparent",
    },
    accessibility: {
      enabled: false,
    },
    title: {
      text: chartTitle,
      style: {
        color: "#ffffff",
      },
    },
    subtitle: {
      text: chartSubtitle,
      style: {
        color: "#9ca3af",
      },
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
        selectedSeasonData?.isCurrent
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
      max: 100,
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
        if (selectedSeasonData?.isCurrent && this.y != null) {
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
    series: selectedSeasonData
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
              states: {
                hover: {
                  enabled: true,
                },
              },
            },
          },
        ]
      : [],
    legend: {
      enabled: false,
    },
  };

  return (
    <div className="xchart-container">
      <HighchartsReact highcharts={Highcharts} options={options} />
    </div>
  );
};

export default XChart;
