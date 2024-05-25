import React, { useState } from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import { useTranslation } from "react-i18next";

const SkillOffsetGraph = ({ data, weaponTranslations, logarithmic }) => {
  const { t } = useTranslation("analytics");
  const [showTooltip, setShowTooltip] = useState(false);
  const imageSize = 32;
  const minSkillOffset = data.reduce(
    (acc, item) => Math.min(acc, item.skill_offset),
    0
  );
  const maxSkillOffset = data.reduce(
    (acc, item) => Math.max(acc, item.skill_offset),
    0
  );
  const xMin = 1;
  const xMax = data.reduce((acc, item) => Math.max(acc, item.count), 0);
  const xOffset = logarithmic ? 50 : 10;

  const chartOptions = {
    chart: {
      type: "scatter",
      backgroundColor: "#1a202c",
      style: {
        fontFamily: "'Roboto', sans-serif",
      },
      zoomType: "xy",
      resetZoomButton: {
        theme: {
          fill: "#1a202c",
          stroke: "#ffffff",
          style: {
            color: "#ffffff",
          },
          states: {
            hover: {
              fill: "#ffffff",
              style: {
                color: "#1a202c",
              },
            },
          },
        },
        position: {
          align: "right",
          verticalAlign: "top",
          x: -10,
          y: 10,
        },
      },
    },
    title: {
      text: t("skill_offset.graph_label"),
      style: {
        color: "#ffffff",
        fontSize: "20px",
      },
    },
    subtitle: {
      text: t("skill_offset.graph_subtitle"),
      style: {
        color: "#ffcc00",
        fontSize: "16px",
      },
    },
    xAxis: {
      type: logarithmic ? "logarithmic" : "linear",
      title: {
        text: t("skill_offset.xaxis.title"),
        style: {
          color: "#ffffff",
          fontSize: "16px",
        },
      },
      labels: {
        style: {
          color: "#ffffff",
          fontSize: "14px",
        },
      },
      min: xMin - 0.1,
      max: xMax + xOffset,
      gridLineColor: "#444444",
    },
    yAxis: {
      title: {
        text: t("skill_offset.yaxis.title"),
        style: {
          color: "#ffffff",
          fontSize: "16px",
        },
      },
      labels: {
        style: {
          color: "#ffffff",
          fontSize: "14px",
        },
      },
      min: minSkillOffset - 0.1,
      max: maxSkillOffset + 0.1,
      gridLineColor: "#444444",
    },
    series: [
      {
        name: t("skill_offset.marker.label"),
        data: data.map((item) => ({
          x: item.count,
          y: item.skill_offset,
          marker: {
            symbol: `url(${item.weapon_image})`,
            width: imageSize,
            height: imageSize,
          },
          weaponName:
            weaponTranslations["WeaponName_Main"][item.weapon_name] ||
            item.weapon_name,
        })),
        dataLabels: {
          enabled: false,
        },
      },
    ],
    legend: {
      enabled: false,
    },
    plotOptions: {
      scatter: {
        marker: {
          radius: 5,
        },
        enableMouseTracking: true,
        tooltip: {
          headerFormat: "",
          pointFormat: t("skill_offset.marker.format"),
        },
      },
    },
    credits: {
      enabled: false,
    },
  };

  return (
    <div className="graph-container relative" style={{ padding: "20px" }}>
      <HighchartsReact highcharts={Highcharts} options={chartOptions} />
      <button
        className="absolute top-0 right-0 mt-2 mr-2 bg-blue-500 text-white rounded-full p-2 focus:outline-none"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        ?
      </button>
      {showTooltip && (
        <div className="tooltip absolute right-0 mt-1 bg-gray-800 text-white text-xs rounded p-2 z-50">
          {t("skill_offset.tooltip")}
        </div>
      )}
    </div>
  );
};

export default SkillOffsetGraph;
