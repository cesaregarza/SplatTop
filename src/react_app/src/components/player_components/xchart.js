import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import {
  getPercentageInSeason,
  calculateSeasonNow,
  dataWithNulls,
  filterAndProcessData,
} from "./helper_functions";
import "./xchart.css";

class XChart extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      mode: "Splat Zones",
      zoomDomain: { x: [0, 100] },
      removeValuesNotInTop500: false,
    };
  }

  handleZoom = (event) => {
    const { x } = event.xAxis[0];
    this.setState({ zoomDomain: { x } });
  };

  handleBrush = (event) => {
    const { x } = event.xAxis[0];
    this.setState({ zoomDomain: { x } });
  };

  toggleRemoveValuesNotInTop500 = () => {
    this.setState((prevState) => ({
      removeValuesNotInTop500: !prevState.removeValuesNotInTop500,
    }));
  };

  render() {
    const { data } = this.props;
    const { mode, zoomDomain, removeValuesNotInTop500 } = this.state;
    const { currentSeason, processedData } =
      filterAndProcessData(data, mode, removeValuesNotInTop500);
    console.log(processedData);

    const options = {
      chart: {
        zoomType: "x",
        height: 400,
        events: {
          selection: this.handleZoom,
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
              } else {
                series.update({
                  enableMouseTracking: true,
                  marker: {
                    enabled: true,
                    states: {
                      hover: {
                        enabled: true,
                      },
                    },
                  },
                });
              }
            });
          },
        },
        backgroundColor: "#1a202c", // Set the chart background color to dark
      },
      title: {
        text: "X Power Chart",
        style: {
          color: "#ffffff", // Set the title color to white
        },
      },
      xAxis: {
        categories: ["Start", ...Array(4).fill(""), "End"], // Set the desired categories
        crosshair: true,
        labels: {
          style: {
            color: "#ffffff", // Set the xAxis label color to white
          },
        },
      },
      yAxis: {
        title: {
          text: "X Power",
          style: {
            color: "#ffffff", // Set the yAxis title color to white
          },
        },
        labels: {
          style: {
            color: "#ffffff", // Set the yAxis label color to white
          },
        },
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
          return false; // Don't show tooltips for non-current seasons
        },
      },
      plotOptions: {
        series: {
          marker: {
            enabled: false, // Disable markers for all series
          },
        },
      },
      series: processedData.map((seasonData, index) => ({
        name:
          `Season ${seasonData.season} X Power` +
          (seasonData.isCurrent ? " (Current)" : ""),
        data: seasonData.dataPoints.map((point) => ([
          point.x,
          point.y,
        ])),
        pointStart: 0,
        pointInterval: 20,
        color: seasonData.isCurrent
          ? "#ab5ab7"
          : `hsl(0, 0%, ${100 - index * 10}%)`, // Set the series color
        zIndex: seasonData.isCurrent ? 10 : 0, // Set higher zIndex for the current season
      })),
    };

    return (
      <div className="xchart-container">
        <div className="controls">
          <select
            className="mode-selector bg-gray-800 text-white p-2.5 rounded-md border-none"
            value={mode}
            onChange={(e) => this.setState({ mode: e.target.value })}
          >
            <option value="Splat Zones">Splat Zones</option>
            <option value="Tower Control">Tower Control</option>
            <option value="Rainmaker">Rainmaker</option>
            <option value="Clam Blitz">Clam Blitz</option>
          </select>
          <div className="flex items-center space-x-2">
            <input
              id="top500Checkbox"
              type="checkbox"
              checked={removeValuesNotInTop500}
              onChange={this.toggleRemoveValuesNotInTop500}
              className="w-4 h-4 text-purple-600 bg-gray-800 border-gray-600 rounded focus:ring-purple-500"
            />
            <label htmlFor="top500Checkbox" className="text-white text-sm">
              Remove Values Not in Top 500
            </label>
          </div>
        </div>
        <HighchartsReact highcharts={Highcharts} options={options} />
      </div>
    );
  }
}

export default XChart;
