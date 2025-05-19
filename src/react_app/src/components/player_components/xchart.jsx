import React, { useState, useEffect } from "react";
import { getPercentageInSeason, getSeasonName } from "../utils/season_utils";
import {
  filterAndProcessData,
  getSeasonColor,
  getAccessibleColor,
  getDefaultWidth,
  getAccessibleWidth,
} from "./xchart_helper_functions";
import fetchFestivalDates from "./splatfest_retriever";
import { useTranslation } from "react-i18next";
import { modeKeyMap } from "../constants";
import "./xchart.css";

const XChart = (props) => {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const [festivalDates, setFestivalDates] = useState(null);
  const [Highcharts, setHighcharts] = useState(null);
  const [HighchartsReact, setHighchartsReact] = useState(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      import("highcharts/highstock"),
      import("highcharts-react-official"),
    ]).then(([hc, hcr]) => {
      if (mounted) {
        setHighcharts(hc.default || hc);
        setHighchartsReact(hcr.default || hcr);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

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

  const { data, mode, colorMode } = props;
  const modeName = g(modeKeyMap[mode]);
  const { currentSeason, processedData } = filterAndProcessData(
    data,
    mode,
    true,
    festivalDates
  );

  const currentPercentage = getPercentageInSeason(new Date(), currentSeason);

  const chartTitle = t("xchart.title").replace("%MODE%", modeName);
  const currSeasonIndicator = t("xchart.live_indicator");

  const options = {
    chart: {
      zoomType: "x",
      height: 400,
      backgroundColor: "#1a202c",
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
      plotLines: [
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
      ],
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
      shared: true,
      formatter: function () {
        if (
          this.points.some((point) =>
            point.series.name.includes(currSeasonIndicator)
          )
        ) {
          return this.points
            .map((point) => `<b>${point.series.name}</b>: ${point.y}`)
            .join("<br/>");
        }
        return false;
      },
    },
    plotOptions: {
      series: {
        marker: {
          enabled: false,
        },
        showInNavigator: true,
      },
    },
    series: processedData.map((seasonData, index) => ({
      name:
        getSeasonName(seasonData.season, g) +
        (seasonData.isCurrent ? " " + currSeasonIndicator : ""),
      data: seasonData.dataPoints.map((point) => [point.x, point.y]),
      pointStart: 0,
      pointInterval: 20,
      color:
        colorMode === "Seasonal"
          ? getSeasonColor(seasonData.season, seasonData.isCurrent)
          : getAccessibleColor(seasonData.season),
      zIndex: seasonData.isCurrent ? 10 : 0,
      lineWidth:
        colorMode === "Seasonal"
          ? getDefaultWidth(seasonData.isCurrent)
          : getAccessibleWidth(seasonData.season),
      enableMouseTracking: seasonData.isCurrent,
      marker: {
        states: {
          hover: {
            enabled: seasonData.isCurrent,
          },
        },
      },
    })),
    legend: {
      itemStyle: {
        color: "#ffffff",
      },
    },
    navigator: {
      enabled: true,
      xAxis: {
        min: -5,
        max: 105,
        labels: {
          style: {
            color: "#ffffff",
          },
          formatter: function () {
            if (this.value === 0) {
              return "Start";
            } else if (this.value === 100) {
              return "End";
            } else {
              return this.value;
            }
          },
        },
      },
      scrollbar: {
        enabled: true,
      },
      maskFill: "rgba(255, 255, 255, 0.1)",
    },
  };

  return (
    <div className="xchart-container">
      {Highcharts &&
        HighchartsReact && (
          <HighchartsReact highcharts={Highcharts} options={options} />
        )}
    </div>
  );
};

export default XChart;
