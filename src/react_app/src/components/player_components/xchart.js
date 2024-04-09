import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { getPercentageInSeason } from "./helper_functions";

const XChart = ({ data }) => {
  const d3Container = useRef(null);
  const [mode, setMode] = useState("Tower Control"); // Default mode

  useEffect(() => {
    if (data && d3Container.current) {
      const filteredData = data.filter((d) => d.mode === mode);
      const margin = { top: 20, right: 30, bottom: 40, left: 90 },
        width = 460 - margin.left - margin.right,
        height = 400 - margin.top - margin.bottom;

      // Clear SVG before redrawing
      d3.select(d3Container.current).selectAll("*").remove();

      const svg = d3
        .select(d3Container.current)
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

      // Add X axis for percentage of the season
      const x = d3
        .scaleLinear()
        .domain([0, 100]) // Percentage of the season
        .range([0, width]);
      svg
        .append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x));

      // Add Y axis for x_power
      const y = d3
        .scaleLinear()
        .domain([0, d3.max(filteredData, (d) => d.x_power)])
        .range([height, 0]);
      svg.append("g").call(d3.axisLeft(y));

      // Group data by season and sort by percentage in season
      const dataBySeason = d3.group(filteredData, (d) => d.season_number);
      const currentSeason = Math.max(...dataBySeason.keys()); // Get the current season as the max
      dataBySeason.forEach((values, season) => {
        // Sort values by percentage in season
        const sortedValues = values.sort((a, b) => getPercentageInSeason(a.timestamp, season) - getPercentageInSeason(b.timestamp, season));

        const line = d3
          .line()
          .x((d) => x(getPercentageInSeason(d.timestamp, season)))
          .y((d) => y(d.x_power));

        svg
          .append("path")
          .datum(sortedValues)
          .attr("fill", "none")
          .attr("stroke", season === currentSeason ? "#ab5ab7" : "gray") // Highlight current season in #ab5ab7, others in gray
          .attr("stroke-width", season == currentSeason ? 3 : 1)
          .attr("d", line);
      });
    }
  }, [data, mode]); // Redraw chart if data or mode changes

  return (
    <div>
      <select value={mode} onChange={(e) => setMode(e.target.value)}>
        <option value="Tower Control">Tower Control</option>
        <option value="Rainmaker">Rainmaker</option>
        <option value="Splat Zones">Splat Zones</option>
        <option value="Clam Blitz">Clam Blitz</option>
      </select>
      <div className="chart-container" ref={d3Container}></div>
    </div>
  );
};

export default XChart;
