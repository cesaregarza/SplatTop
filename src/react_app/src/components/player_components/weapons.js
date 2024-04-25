import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts/highstock";
import {
  filterAndProcessWeapons,
  computeDrilldown,
} from "./weapon_helper_functions";
import "./xchart.css";

class WeaponsChart extends React.Component {
  render() {
    const { data, mode } = this.props;
    const { counts, percentage } = filterAndProcessWeapons(data, mode);

    const otherThresholdPercent = 2;
    const { seriesPercentage, drilldownPercent, otherCount } = computeDrilldown(
      counts,
      percentage,
      otherThresholdPercent
    );

    let newCounts = {...counts};
    newCounts["Other"] = otherCount;

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
      series: [{
        name: "Weapon Usage",
        colorByPoint: true,
        data: seriesPercentage,
      }],
      drilldown: {
        series: drilldownPercent.map(item => ({
          name: item.name,
          id: item.name,
          data: [item]
        }))
      },
      tooltip: {
        headerFormat: '<span style="font-size:11px">{series.name}</span><br>',
        pointFormat: '<span style="color:{point.color}">{point.name}</span>: <b>{point.y:.2f}%</b> of total<br/>'
      },
      plotOptions: {
        pie: {
          allowPointSelect: true,
          cursor: 'pointer',
          dataLabels: {
            enabled: true,
            format: '<b>{point.name}</b>: {point.y:.2f} %'
          },
          showInLegend: true
        }
      },
      legend: {
        itemStyle: {
          color: "#ffffff",
        },
      },
    };

    return (
      <div>
        <HighchartsReact
          highcharts={Highcharts}
          options={options}
        />
      </div>
    );
  }
}

export default WeaponsChart;

