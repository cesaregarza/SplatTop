import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import drilldown from "highcharts/modules/drilldown";
import {
  filterDataAndGroupByWeapon,
  computeDrilldown,
} from "./weapon_helper_functions";
import "./xchart.css";

drilldown(Highcharts);

class WeaponsChart extends React.Component {
  render() {
    const { data, mode } = this.props;
    const groupedData = filterDataAndGroupByWeapon(data, mode);

    const otherThresholdPercent = 4;
    const { seriesCount, drilldownData } = computeDrilldown(
      groupedData,
      otherThresholdPercent
    );

    console.log(seriesCount);
    console.log(drilldownData);

    const innerSeriesCount = seriesCount.map((item) => {
      if (item.name !== "Other") {
        const total = Object.values(item.y).reduce((acc, val) => acc + val, 0);
        return {
          name: item.name,
          y: total,
          drilldown: item.name,
          data: Object.entries(item.y).map(([season, value]) => [
            `Season ${season}`,
            value,
          ]),
        };
      } else {
        return {
          name: item.name,
          y: item.y,
          drilldown: item.name,
        };
      }
    });

    const outerSeriesCount = seriesCount.flatMap((item) => {
      if (item.name === "Other") {
        return [{ name: item.name, y: item.y }];
      }
      return Object.entries(item.y).map(([season, count]) => ({
        name: `${item.name}:${season}`,
        y: count,
      }));
    });

    const options = {
      chart: {
        type: "pie",
        height: 400,
        backgroundColor: "#1a202c",
      },
      title: {
        text: `${mode} Weapons Usage`,
        style: {
          color: "#ffffff",
        },
      },
      series: [
        {
          name: "Total Weapon Usage",
          colorByPoint: true,
          data: innerSeriesCount.map((item) => ({
            name: item.name,
            y: item.y,
            drilldown: item.name,
          })),
          size: "60%",
          dataLabels: {
            enabled: false,
          },
        },
        {
          name: "Detailed Weapon Usage",
          colorByPoint: true,
          data: outerSeriesCount,
          size: "100%",
          innerSize: "60%",
          id: "weapons",
          dataLabels: {
            formatter: function () {
              return `<b>${this.point.name}</b>: ${this.y}`;
            },
            filter: {
              property: "percentage",
              operator: ">",
              value: 2,
            },
          },
          showInLegend: false,
        },
      ],
      drilldown: {
        series: innerSeriesCount
          .filter((item) => item.name !== "Other")
          .map((item) => ({
            id: item.name,
            name: item.name,
            data: item.data,
          }))
          .concat({
            id: "Other",
            name: "Other",
            data: drilldownData.map(([id, count]) => [id.toString(), count]),
          }),
          breadcrumbs: {
            style: {
              fontSize: "14px",
              fontWeight: "bold",
              color: "#ffffff",
            },
            buttonTheme: {
              style: {
                color: "#ffffff",
                fill: "transparent",
                fontWeight: "normal",
                fontSize: "14px",
              },
              states: {
                hover: {
                  fill: "transparent",
                  style: {
                    color: "#c183e1",
                  },
                },
                select: {
                  fill: "transparent",
                  style: {
                    color: "#ab5ab7",
                    textDecoration: "none",
                    fontWeight: "bold",
                  },
                },
              },
            },
          },
      },
      tooltip: {
        headerFormat: '<span style="font-size:11px">{series.name}</span><br>',
        pointFormat:
          '<span style="color:{point.color}">{point.name}</span>: <b>{point.y}</b><br/>',
      },
      plotOptions: {
        pie: {
          allowPointSelect: true,
          cursor: "pointer",
        },
      },
      legend: {
        enabled: false,
      },
    };

    return (
      <div>
        <HighchartsReact highcharts={Highcharts} options={options} />
      </div>
    );
  }
}

export default WeaponsChart;
