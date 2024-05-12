import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import drilldown from "highcharts/modules/drilldown";
import { computeDrilldown } from "./weapon_helper_functions";
import "./xchart.css";

drilldown(Highcharts);

class WeaponsChart extends React.Component {

  render() {
    const { weapon_winrate } = this.props.data;
    const { mode } = this.props;
    const { weaponTranslations, weaponReferenceData } = this.props;

    const filteredWinrate = weapon_winrate.filter((d) => d.mode === mode);

    const otherThresholdPercent = 4;

    const { innerSeriesData, outerSeriesData, drilldownData } =
      computeDrilldown(
        filteredWinrate,
        otherThresholdPercent,
        weaponReferenceData,
        weaponTranslations
      );

    const totalUsage = innerSeriesData.reduce((acc, item) => acc + item.y, 0);

    const options = {
      chart: {
        type: "pie",
        height: 400,
        backgroundColor: "#1a202c",
      },
      responsive: {
        rules: [
          {
            condition: {
              maxWidth: 500,
            },
            chartOptions: {
              chart: {
                height: 250,
              },
              series: [
                {},
                {
                  dataLabels: {
                    formatter: function () {
                      return `<b style="font-size: 9px;">${this.point.name}</b>`;
                    },
                    filter: {
                      property: "percentage",
                      operator: ">",
                      value: 5,
                    },
                    distance: 5,
                  },
                },
              ],
            },
          },
        ],
      },
      title: {
        text: `${mode} Weapons Usage`,
        style: {
          color: "#ffffff",
        },
      },
      subtitle: {
        text: "All weapon data is approximate",
        style: {
          color: "#ffcc00",
        },
      },
      series: [
        {
          name: "Total Weapon Usage",
          colorByPoint: true,
          data: innerSeriesData.map((item) => ({
            name: weaponTranslations[item.name] || item.name,
            y: (item.y / totalUsage) * 100,
            drilldown: item.name,
            color: item.color,
            classColor: item.color,
          })),
          size: "60%",
          dataLabels: {
            enabled: true,
            distance: -30,
            inside: true,
            formatter: function () {
              return `<span style="color: #000000;">${this.point.name}</span>`;
            },
          },
        },
        {
          name: "Detailed Weapon Usage",
          colorByPoint: true,
          data: outerSeriesData.map((item) => ({
            name: item.name,
            y: (item.y / totalUsage) * 100,
            color: item.color,
            classColor: item.classColor,
          })),
          size: "100%",
          innerSize: "60%",
          id: "weapons",
          dataLabels: {
            formatter: function () {
              return `<b>${this.point.name}</b>: ${this.y.toFixed(2)}%`;
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
        series: drilldownData.map((series) => ({
          ...series,
          data: series.data.map((item) => ({
            name: item.name,
            y: item.y,
            color: item.color,
            classColor: item.color,
          })),
        })),
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
          '<span style="color:{point.classColor}">{point.name}</span>: <b>{point.y:.2f}%</b> of total<br>',
      },
      plotOptions: {
        pie: {
          allowPointSelect: true,
          cursor: "pointer",
          dataLabels: {
            connectorColor: "#FFFFFF",
            overflow: "justify",
          },
        },
      },
      legend: {
        enabled: false,
      },
      activeDataLabelStyle: {
        textDecoration: "none",
        color: "#ab5ab7",
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
