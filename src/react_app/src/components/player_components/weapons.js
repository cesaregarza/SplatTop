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

    const innerSeriesCount = seriesCount.map((item) => {
      if (item.name !== "Other") {
        const total = Object.values(item.y).reduce((acc, val) => acc + val, 0);
        return {
          name: item.name,
          y: total,
          drilldown: item.name,
          data: Object.entries(item.y).map(([season, value]) => ({
            name: `${item.name}:Season ${season}`,
            y: value,
          })),
        };
      }
      return item;
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
        series: drilldownData.map((item) => ({
          ...item,
          id: item.name,
          data: item.data.map((d) => ({
            name: `${item.name}:Season ${d[0]}`,
            y: d[1],
          })),
        })),
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
