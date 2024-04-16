import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts/highstock";
import {
  getPercentageInSeason,
  filterAndProcessData,
  getSeasonName,
  getSeasonColor,
  getClassicColor,
} from "./helper_functions";
import fetchFestivalDates from "./splatfest_retriever";
import "./xchart.css";

// This component is the old-style class-based component for performance reasons
// I'm not sure why highcharts doesn't like the functional component instead
class XChart extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      colorMode: "Classic", // Default color mode
    };
  }

  async componentDidMount() {
    try {
      const dates = await fetchFestivalDates();
      this.setState({ festivalDates: dates });
    } catch (error) {
      console.error("Error fetching festival dates:", error);
    }
  }

  toggleColorMode = () => {
    this.setState((prevState) => ({
      colorMode: prevState.colorMode === "Seasonal" ? "Classic" : "Seasonal",
    }));
  };

  render() {
    const { data, mode, removeValuesNotInTop500 } = this.props;
    const { currentSeason, processedData } = filterAndProcessData(
      data,
      mode,
      removeValuesNotInTop500,
      this.state.festivalDates
    );

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
        color:
          this.state.colorMode === "Seasonal"
            ? getSeasonColor(seasonData.season, seasonData.isCurrent)
            : getClassicColor(
                seasonData.season,
                seasonData.isCurrent,
                processedData.length
              ),
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
        <label
          htmlFor="toggleColorMode"
          className="inline-flex items-center justify-center w-full cursor-pointer"
        >
          <span className="text-sm font-medium text-gray-900 dark:text-gray-300 mr-2">
            Classic
          </span>
          <div className="relative" title="Change the color scheme">
            <input
              type="checkbox"
              id="toggleColorMode"
              className="sr-only peer"
              checked={this.state.colorMode === "Seasonal"}
              onChange={this.toggleColorMode}
            />
            <div
              className={`w-11 h-6 rounded-full peer peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5 ${
                this.state.colorMode === "Seasonal"
                  ? "seasonal-bg"
                  : "classic-bg"
              }`}
            ></div>
          </div>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-300 ml-2">
            Seasonal
          </span>
        </label>
        <HighchartsReact highcharts={Highcharts} options={options} />
      </div>
    );
  }
}

export default XChart;
