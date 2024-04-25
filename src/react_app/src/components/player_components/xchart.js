import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts/highstock";
import {
  getPercentageInSeason,
  filterAndProcessData,
  getSeasonName,
  getSeasonColor,
  getAccessibleColor,
  getDefaultWidth,
  getAccessibleWidth,
} from "./helper_functions";
import fetchFestivalDates from "./splatfest_retriever";
import "./xchart.css";

class XChart extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      festivalDates: null,
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

  render() {
    const { data, mode, colorMode } = this.props;
    const { festivalDates } = this.state;
    const { currentSeason, processedData } = filterAndProcessData(
      data,
      mode,
      true,
      festivalDates
    );
    

    const currentPercentage = getPercentageInSeason(new Date(), currentSeason);

    const options = {
      chart: {
        zoomType: "x",
        height: 400,
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
          text: "% of Season Elapsed",
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
              text: "Now",
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
          (colorMode === "Seasonal"
            ? getSeasonColor(seasonData.season, seasonData.isCurrent)
            : getAccessibleColor(
                seasonData.season,
            )
          ),
        zIndex: seasonData.isCurrent ? 10 : 0,
        lineWidth: (colorMode === "Seasonal")
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
        <HighchartsReact highcharts={Highcharts} options={options} />
      </div>
    );
  }
}

export default XChart;
