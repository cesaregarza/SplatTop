import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts/highstock";
import {
  getPercentageInSeason,
  filterAndProcessData,
  getSeasonName,
  getSeasonColor,
} from "./helper_functions";
import "./xchart.css";

class XChart extends React.Component {
  render() {
    const { data, mode, removeValuesNotInTop500 } = this.props;
    const { currentSeason, processedData } = filterAndProcessData(
      data,
      mode,
      removeValuesNotInTop500
    );
    console.log(processedData);

    const currentPercentage = getPercentageInSeason(new Date(), currentSeason);

    const options = {
      chart: {
        zoomType: "x",
        height: 400,
        events: {
          load: function () {
            this.series.forEach((series) => {
              if (!series.name.includes("(Current)")) {
                series.update({
                  enableMouseTracking: false,
                  marker: {
                    states: {
                      hover: {
                        enabled: false,
                      },
                    },
                  },
                });
              }
            });
          },
        },
        backgroundColor: "#1a202c",
      },
      title: {
        text: `${mode} X Power`,
        style: {
          color: "#ffffff",
        },
      },
      xAxis: {
        title: {
          text: "Percentage of Season Elapsed",
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
              return "Start";
            } else if (this.value === 100) {
              return "End";
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
              text: "Time right now",
              align: "left",
              style: {
                color: "rgba(255, 255, 255, 0.4)",
              },
            },
          },
        ],
        min: 0,
        max: 100,
      },
      yAxis: {
        title: {
          text: "X Power",
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
            this.points.some((point) => point.series.name.includes("(Current)"))
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
          getSeasonName(seasonData.season) +
          (seasonData.isCurrent ? " (Current)" : ""),
        data: seasonData.dataPoints.map((point) => [point.x, point.y]),
        pointStart: 0,
        pointInterval: 20,
        color: getSeasonColor(seasonData.season, seasonData.isCurrent),
        zIndex: seasonData.isCurrent ? 10 : 0,
        lineWidth: seasonData.isCurrent ? 5 : 2,
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
        <HighchartsReact highcharts={Highcharts} options={options} />
      </div>
    );
  }
}

export default XChart;
