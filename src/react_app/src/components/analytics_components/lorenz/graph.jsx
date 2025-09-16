import React, { useState } from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import { useTranslation } from "react-i18next";

const LorenzGraph = ({ data, weaponTranslations }) => {
  const { t } = useTranslation("analytics");
  const [showTooltip, setShowTooltip] = useState(false);
  const imageSize = 32;
  const yMax = 1;
  const yMin = 0;

  const giniHealthCutoffs = {
    0.0: t("lorenz.gini.equality"),
    0.1: t("lorenz.gini.very_very_low"),
    0.2: t("lorenz.gini.very_low"),
    0.3: t("lorenz.gini.low"),
    0.4: t("lorenz.gini.low_medium"),
    0.5: t("lorenz.gini.medium"),
    0.6: t("lorenz.gini.high"),
    0.7: t("lorenz.gini.very_high"),
    0.8: t("lorenz.gini.very_very_high"),
    0.9: t("lorenz.gini.extremely_high"),
    1.0: t("lorenz.gini.unequal"),
  };

  const subtitle = t("lorenz.graph_subtitle");

  const generateSeries = (isResponsive) => [
    {
      name: t("lorenz.marker.label"),
      data: data.lorenz.map((item) => ({
        y: parseFloat(item.count),
        y_percent: parseFloat(item.count) * 100,
        name:
          weaponTranslations["WeaponName_Main"][item.weapon_name] ||
          item.weapon_name,
        marker: isResponsive
          ? "circle"
          : {
              symbol: `url(${item.weapon_image})`,
              width: imageSize,
              height: imageSize,
            },
        diff: parseFloat(item.diff) * 100,
      })),
      color: "#ab5ab7",
    },
    {
      name: t("lorenz.gini.equality"),
      data: data.lorenz.map((item, index) => index / (data.lorenz.length - 1)),
      marker: {
        enabled: false,
        states: {
          hover: {
            enabled: false,
          },
        },
      },
      color: "rgba(255, 255, 255, 0.2)",
      zIndex: -1,
      enableMouseTracking: false,
    },
  ];

  const lorenzChartOptions = {
    chart: {
      type: "area",
      backgroundColor: "#1a202c",
      style: {
        fontFamily: "'Roboto', sans-serif",
      },
      zoomType: "xy",
      plotBorderColor: null,
      plotBorderWidth: 0,
    },
    accessibility: {
      enabled: false,
    },
    title: {
      text: t("lorenz.graph_label"),
      style: {
        color: "#ffffff",
        fontSize: "20px",
      },
    },
    subtitle: {
      text: subtitle,
      style: {
        color: "#ffcc00",
        fontSize: "16px",
      },
    },
    xAxis: {
      title: {
        text: t("lorenz.xaxis.title"),
        style: {
          color: "#ffffff",
          fontSize: "16px",
        },
      },
      labels: {
        enabled: false,
      },
    },
    yAxis: {
      categories: data.lorenz.map((item) => item.weapon_id),
      labels: {
        useHTML: true,
        formatter: function () {
          const item = data.lorenz[this.pos];
          return `<img src="${item.weapon_image}" width="${imageSize}" height="${imageSize}" />`;
        },
        style: {
          color: "#ffffff",
          fontSize: "14px",
        },
      },
      title: {
        text: t("lorenz.yaxis.title"),
        style: {
          color: "#ffffff",
          fontSize: "16px",
        },
      },
      min: yMin,
      max: yMax,
    },
    series: generateSeries(false),
    plotOptions: {
      area: {
        enableMouseTracking: true,
        tooltip: {
          headerFormat: "",
          pointFormat: t("lorenz.marker.format"),
        },
      },
    },
    legend: {
      itemStyle: {
        color: "#ffffff",
      },
    },
    credits: {
      enabled: false,
    },
    responsive: {
      rules: [
        {
          condition: {
            maxWidth: 1000,
          },
          chartOptions: {
            series: generateSeries(true),
          },
        },
      ],
    },
  };

  const giniChartOptions = {
    chart: {
      type: "scatter",
      backgroundColor: "#1a202c",
      style: {
        fontFamily: "'Roboto', sans-serif",
      },
      height: 200,
      marginTop: 20,
      marginBottom: 100,
    },
    accessibility: {
      enabled: false,
    },
    title: {
      text: t("lorenz.gini.title"),
      style: {
        color: "#ffffff",
        fontSize: "16px",
      },
      floating: true,
    },
    xAxis: {
      title: {
        text: "",
        style: {
          color: "#ffffff",
          fontSize: "16px",
        },
      },
      min: 0,
      max: 1,
      tickInterval: 0.1,
      startOnTick: true,
      endOnTick: true,
      showLastLabel: true,
      labels: {
        style: {
          color: "#ffffff",
        },
        formatter: function () {
          const tick_fixed = this.value.toFixed(1);
          return giniHealthCutoffs[tick_fixed];
        },
      },
    },
    yAxis: {
      title: {
        text: "",
      },
      min: 0,
      max: 1,
      tickPositions: [0.1],
      labels: {
        enabled: false,
      },
      gridLineWidth: 0,
    },
    series: [
      {
        name: t("lorenz.gini.indicator"),
        data: [[parseFloat(data.gini), 0.5]],
        marker: {
          symbol: "diamond",
          radius: 8,
        },
        color: "#ffcc00",
        tooltip: {
          pointFormat: t("lorenz.gini.indicator_format"),
        },
      },
    ],
    plotOptions: {
      scatter: {
        marker: {
          radius: 8,
          states: {
            hover: {
              enabled: true,
              lineColor: "rgb(100,100,100)",
            },
          },
        },
      },
    },
    legend: {
      enabled: false,
    },
    responsive: {
      rules: [
        {
          condition: {
            maxWidth: 1000,
          },
          chartOptions: {
            xAxis: {
              style: {
                fontSize: "10px",
              },
              tickInterval: 0.2,
              labels: {
                style: {
                  fontSize: "10px",
                },
                rotation: -60,
              },
            },
          },
        },
      ],
    },
  };

  return (
    <div className="graph-container relative" style={{ padding: "20px" }}>
      <HighchartsReact highcharts={Highcharts} options={lorenzChartOptions} />
      <HighchartsReact highcharts={Highcharts} options={giniChartOptions} />
      <button
        className="absolute top-0 right-0 mt-2 mr-2 bg-blue-500 text-white rounded-full p-2 focus:outline-hidden"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        ?
      </button>
      {showTooltip && (
        <div className="tooltip absolute right-0 mt-1 bg-gray-800 text-white text-xs rounded-sm p-2 z-50">
          {t("lorenz.tooltip")}
        </div>
      )}
    </div>
  );
};

export default LorenzGraph;
