import React from "react";
import * as V from "victory";
import { getPercentageInSeason } from "./helper_functions";
import "./xchart.css";

class AnimatedGlowDot extends React.Component {
  render() {
    const { x, y } = this.props;
    return (
      <g filter="url(#glow)">
        {/* Original Dot */}
        <circle cx={x} cy={y} r="4" fill="#ab5ab7" />

        {/* Animated Glow Dot */}
        <circle cx={x} cy={y} r="4" fill="#ab5ab7" opacity="0.3">
          <animate
            attributeName="r"
            from="4"
            to="12"
            dur="1.5s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            from="0.3"
            to="0"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </circle>
      </g>
    );
  }
}

class XChart extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      mode: "Splat Zones",
      isSmooth: true,
      zoomDomain: { x: [0, 100] },
    };
  }

  handleZoom(domain) {
    this.setState({ selectedDomain: domain });
  }

  handleBrush(domain) {
    this.setState({ zoomDomain: domain });
  }

  render() {
    const { data } = this.props;
    const { mode, isSmooth, zoomDomain } = this.state;

    const filteredData = data
      ? data.filter((d) => d.mode === mode && d.updated)
      : [];

    const seasons = filteredData.reduce((acc, curr) => {
      const season = curr.season_number;
      if (!acc.includes(season)) acc.push(season);
      return acc;
    }, []);

    const currentSeason = Math.max(...seasons);

    const dataBySeason = filteredData.reduce((acc, curr) => {
      const season = curr.season_number;
      if (!acc[season]) acc[season] = [];
      acc[season].push({
        x: getPercentageInSeason(curr.timestamp, season),
        y: curr.x_power,
      });
      return acc;
    }, {});

    const sortedSeasons = seasons.sort((a, b) => {
      if (a === currentSeason) return 1;
      if (b === currentSeason) return -1;
      return b - a;
    });

    const lines = sortedSeasons.map((season, index) => {
      const sortedValues = dataBySeason[season].sort((a, b) => a.x - b.x);
      const baseHue = 292;
      const saturation = 40;
      const lightness = 42 - 5 * index;
      const strokeColor =
        season === currentSeason
          ? "#ab5ab7"
          : `hsl(${baseHue}, ${saturation}%, ${lightness}%)`;

      return (
        <V.VictoryLine
          key={season}
          data={sortedValues}
          style={{
            data: {
              stroke: strokeColor,
              strokeWidth: season === currentSeason ? 4 : 2,
              strokeLinecap: "round",
              opacity: season === currentSeason ? 1.0 : 0.8,
            },
          }}
          interpolation={isSmooth ? "monotoneX" : "linear"}
        />
      );
    });

    const latestDataPoint = dataBySeason[currentSeason]
      ? dataBySeason[currentSeason][dataBySeason[currentSeason].length - 1]
      : null;

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
          <label className="smooth-toggle">
            <input
              type="checkbox"
              checked={isSmooth}
              onChange={() => this.setState({ isSmooth: !isSmooth })}
            />{" "}
            Enable Smoothing
          </label>
        </div>
        <svg style={{ height: 0 }}>
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
        </svg>

        <div className="chart-container">
          <V.VictoryChart
            theme={V.VictoryTheme.material}
            style={{
              grid: { stroke: "none", opacity: 0.1 },
              parent: { position: "relative", zIndex: 0 },
            }}
            scale={{ x: "linear", y: "linear" }}
            width={800}
            height={400}
            containerComponent={
              <V.VictoryZoomContainer
                zoomDimension="x"
                zoomDomain={zoomDomain}
                onZoomDomainChange={this.handleZoom.bind(this)}
                allowZoom={true}
                style={{
                  brushArea: {
                    stroke: "lightgray",
                    fill: "white",
                    opacity: 0.5,
                  },
                }}
              />
            }
          >
            <V.VictoryAxis
              dependentAxis
              style={{ axis: { stroke: "white" } }}
              tickFormat={(t) => `${(t / 1000).toFixed(1)}k`}
            />
            <V.VictoryAxis
              style={{ axis: { stroke: "white" } }}
              tickValues={[0, 20, 40, 60, 80, 100]}
              tickFormat={["Start", "20%", "40%", "60%", "80%", "End"]}
            />
            {lines}
            {latestDataPoint && (
              <V.VictoryScatter
                data={[latestDataPoint]}
                dataComponent={<AnimatedGlowDot />}
                style={{
                  data: {
                    fill: "#ab5ab7",
                    stroke: "none",
                    filter: "url(#glow)",
                  },
                }}
                size={4}
                symbol="circle"
              />
            )}
          </V.VictoryChart>
          <V.VictoryChart
            theme={V.VictoryTheme.material}
            style={{
              grid: { stroke: "none", opacity: 0.1 },
              parent: { position: "relative", zIndex: 0 },
            }}
            scale={{ x: "linear", y: "linear" }}
            width={800}
            height={100}
            padding={{ top: 0, bottom: 20, left: 50, right: 50 }}
            containerComponent={
              <V.VictoryBrushContainer
                brushDimension="x"
                brushDomain={this.state.selectedDomain}
                onBrushDomainChange={this.handleBrush.bind(this)}
                brushStyle={{ fill: "darkgray", opacity: 0.4 }}
              />
            }
          >
            <V.VictoryAxis
              style={{
                axis: { stroke: "white" },
                ticks: { size: 5 },
                tickLabels: { fontSize: 7, padding: 5 },
              }}
              tickValues={[0, 20, 40, 60, 80, 100]}
              tickFormat={["Start", "20%", "40%", "60%", "80%", "End"]}
            />
            {lines}
          </V.VictoryChart>
        </div>
      </div>
    );
  }
}

export default XChart;
