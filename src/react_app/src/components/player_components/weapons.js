import React from "react";
import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import drilldown from "highcharts/modules/drilldown";
import axios from "axios";
import { computeDrilldown } from "./weapon_helper_functions";
import "./xchart.css";

drilldown(Highcharts);

const isDevelopment = process.env.NODE_ENV === "development";
const apiUrl = isDevelopment
  ? "http://localhost:5000"
  : process.env.REACT_APP_API_URL || "";
const endpoint = `${apiUrl}/api/weapon_info`;

const hues = [
  0, 32.72727273, 65.45454545, 98.18181818, 130.90909091, 163.63636364,
  196.36363636, 229.09090909, 261.81818182, 294.54545455, 327.27272727,
];
const weaponOrder = [
  "Blaster",
  "Roller",
  "Shooter",
]

class WeaponsChart extends React.Component {
  constructor(props) {
    super(props);
    const localData = localStorage.getItem("weaponReferenceData");
    this.state = {
      weaponReferenceData: localData ? JSON.parse(localData) : null,
    };
    if (!localData) {
      this.fetchWeaponReferenceData();
    }
  }

  componentDidMount() {
    // Data fetching is now initiated in the constructor if local storage is empty
  }

  fetchWeaponReferenceData() {
    const fetchData = () => {
      axios
        .get(endpoint)
        .then((response) => {
          if (response.status === 200 && response.data) {
            this.setState({ weaponReferenceData: response.data });
            localStorage.setItem(
              "weaponReferenceData",
              JSON.stringify(response.data)
            );
          } else {
            console.error("No data received:", response);
          }
        })
        .catch((error) => {
          if (error.response && error.response.status === 503) {
            console.error("Service unavailable, retrying fetch:", error);
            setTimeout(fetchData, 1000);
          } else {
            console.error("Error fetching weapon reference data:", error);
          }
        });
    };
    fetchData();
  }

  render() {
    const { weapon_winrate } = this.props.data;
    const { mode } = this.props;
    const { weaponTranslations } = this.props;

    const filteredWinrate = weapon_winrate.filter((d) => d.mode === mode);

    const otherThresholdPercent = 4;

    const { innerSeriesData, outerSeriesData, drilldownData } =
      computeDrilldown(
        filteredWinrate,
        otherThresholdPercent,
        this.state.weaponReferenceData,
        weaponTranslations
      );

    console.log("innerSeriesData", innerSeriesData);
    console.log("outerSeriesData", outerSeriesData);
    console.log("drilldownData", drilldownData);

    const totalUsage = innerSeriesData.reduce((acc, item) => acc + item.y, 0);

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
          data: innerSeriesData.map((item) => ({
            name: weaponTranslations[item.name] || item.name, // Use translated name if available
            name: item.name,
            y: (item.y / totalUsage) * 100,
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
          data: outerSeriesData.map((item) => ({
            name: item.name,
            y: (item.y / totalUsage) * 100,
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
        series: drilldownData,
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
          '<span style="color:{point.color}">{point.name}</span>: <b>{point.y:.2f}%</b> of total<br>',
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
