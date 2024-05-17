import React, { useEffect, useState } from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import drilldown from "highcharts/modules/drilldown";
import { computeDrilldown } from "./weapon_helper_functions";
import { useTranslation } from "react-i18next";
import "./xchart.css";

drilldown(Highcharts);

const WeaponsChart = (props) => {
  const { t } = useTranslation("player"); 
  const [options, setOptions] = useState({});

  useEffect(() => {
    const { weapon_winrate } = props.data;
    const { mode } = props;
    const { weaponTranslations, weaponReferenceData } = props;

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

    const chartTitle = t("weaponchart.title").replace("%MODE%", mode);

    const chartOptions = {
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
        text: chartTitle,
        style: {
          color: "#ffffff",
        },
      },
      subtitle: {
        text: t("weaponchart.subtitle"),
        style: {
          color: "#ffcc00",
        },
      },
      series: [
        {
          name: t("weaponchart.inner.title"),
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
          name: t("weaponchart.outer.title"),
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
          t("weaponchart.point.format"),
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

    setOptions(chartOptions);
  }, [props, t]);

  return (
    <div>
      <HighchartsReact highcharts={Highcharts} options={options} />
    </div>
  );
};

export default WeaponsChart;
