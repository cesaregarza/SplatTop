import React, { useEffect, useState } from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import drilldown from "highcharts/modules/drilldown";
import { computeDrilldown } from "./weapon_helper_functions";
import { useTranslation } from "react-i18next";
import { modeKeyMap } from "../constants";
import "./xchart.css";

drilldown(Highcharts);

const WeaponsChart = (props) => {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const [options, setOptions] = useState({});
  const [legendItems, setLegendItems] = useState([]);

  useEffect(() => {
    const { weapon_winrate } = props.data;
    const { mode } = props;
    const modeName = g(modeKeyMap[mode]);
    const { weaponTranslations, weaponReferenceData } = props;

    const filteredWinrate = weapon_winrate.filter((entry) => entry.mode === mode);
    const otherThresholdPercent = 4;

    if (filteredWinrate.length === 0) {
      setOptions({
        chart: {
          type: "pie",
          height: 300,
          backgroundColor: "transparent",
        },
        title: {
          text: t("weaponchart.title").replace("%MODE%", modeName),
          style: { color: "#ffffff" },
        },
        subtitle: {
          text: t("no_data"),
          style: { color: "#9ca3af" },
        },
        series: [],
      });
      setLegendItems([]);
      return;
    }

    const drilldownResult = computeDrilldown(
      filteredWinrate,
      otherThresholdPercent,
      weaponReferenceData,
      weaponTranslations,
      t("weaponchart.other")
    );
    const innerSeriesData = drilldownResult?.innerSeriesData ?? [];
    const outerSeriesData = drilldownResult?.outerSeriesData ?? [];
    const drilldownData = drilldownResult?.drilldownData ?? [];

    if (innerSeriesData.length === 0) {
      setOptions({
        chart: {
          type: "pie",
          height: 300,
          backgroundColor: "transparent",
        },
        title: {
          text: t("weaponchart.title").replace("%MODE%", modeName),
          style: { color: "#ffffff" },
        },
        subtitle: {
          text: t("no_data"),
          style: { color: "#9ca3af" },
        },
        series: [],
      });
      setLegendItems([]);
      return;
    }

    const totalUsage = innerSeriesData.reduce((acc, item) => acc + item.y, 0);
    const chartTitle = t("weaponchart.title").replace("%MODE%", modeName);

    const chartOptions = {
      chart: {
        type: "pie",
        height: 360,
        backgroundColor: "transparent",
      },
      accessibility: {
        enabled: false,
      },
      responsive: {
        rules: [
          {
            condition: {
              maxWidth: 640,
            },
            chartOptions: {
              chart: {
                height: 280,
              },
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
          color: "#fcd34d",
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
            distance: -24,
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
            enabled: false,
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
        pointFormat: t("weaponchart.point.format"),
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
    setLegendItems(
      [...outerSeriesData]
        .sort((left, right) => right.y - left.y)
        .slice(0, 8)
        .map((item) => ({
          ...item,
          share: (item.y / totalUsage) * 100,
        }))
    );
  }, [props, t, g]);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_16rem] lg:items-start">
      <div className="min-w-0">
        <HighchartsReact highcharts={Highcharts} options={options} />
      </div>
      <aside className="border-t border-gray-800/60 pt-3 lg:border-t-0 lg:border-l lg:pl-4 lg:pt-0">
        <h3 className="text-xs font-medium uppercase tracking-[0.16em] text-gray-400">
          {t("weaponchart.outer.title")}
        </h3>
        <div className="mt-3 space-y-2">
          {legendItems.map((item, index) => (
            <div
              key={item.name}
              className="flex items-center gap-3 text-sm text-white"
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: item.classColor }}
              ></span>
              <span className="w-5 shrink-0 text-xs tabular-nums text-gray-500">
                {index + 1}
              </span>
              <span className="min-w-0 flex-1 truncate">{item.name}</span>
              <span className="shrink-0 tabular-nums text-gray-300">
                {item.share.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
};

export default WeaponsChart;
