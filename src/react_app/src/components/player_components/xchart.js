import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { getPercentageInSeason } from "./helper_functions";

const XChart = ({ data }) => {
  const d3Container = useRef(null);
  const [mode, setMode] = useState("Splat Zones"); // Default mode

  useEffect(() => {
    const handleResize = () => {
      if (data && d3Container.current) {
        const filteredData = data.filter((d) => d.mode === mode);
        const margin = { top: 20, right: 30, bottom: 40, left: 90 };
        const containerRect = d3Container.current.getBoundingClientRect();
        const width = containerRect.width;
        const minHeight = 500; // Set a minimum height for the chart
        const height = Math.max(containerRect.height, minHeight) - margin.top - margin.bottom;

        // Clear SVG before redrawing
        d3.select(d3Container.current).selectAll("*").remove();

        const svg = d3
          .select(d3Container.current)
          .append("svg")
          .attr("width", "100%")
          .attr("height", height + margin.top + margin.bottom)
          .append("g")
          .attr("transform", `translate(${margin.left},${margin.top})`);

        const x = d3
          .scaleLinear()
          .domain([0, 100])
          .range([0, width - margin.left - margin.right]);
        svg
          .append("g")
          .attr("transform", `translate(0,${height})`)
          .call(d3.axisBottom(x));

        const y = d3
          .scaleLinear()
          .domain([0, d3.max(filteredData, (d) => d.x_power)])
          .range([height, 0]);
        svg.append("g").call(d3.axisLeft(y));

        const dataBySeason = d3.group(filteredData, (d) => d.season_number);
        const currentSeason = Math.max(...dataBySeason.keys());
        const seasonsDescending = Array.from(dataBySeason.keys()).sort((a, b) => a - b);
        const colorScale = d3.scaleLinear().domain([0, seasonsDescending.length - 1]).range(["#ab5ab7", "black"]);

        seasonsDescending.forEach(season => {
          const values = dataBySeason.get(season);
          const sortedValues = values.sort(
            (a, b) =>
              getPercentageInSeason(a.timestamp, season) -
              getPercentageInSeason(b.timestamp, season)
          );

          const line = d3
            .line()
            .x((d) => x(getPercentageInSeason(d.timestamp, season)))
            .y((d) => y(d.x_power));

          svg
            .append("path")
            .datum(sortedValues)
            .attr("fill", "none")
            .attr("stroke", season === currentSeason ? "#ab5ab7" : colorScale(seasonsDescending.indexOf(season)))
            .attr("stroke-width", season === currentSeason ? 3 : 1)
            .attr("d", line);
        });
      }
    };

    const initialRender = () => {
      handleResize();
      window.addEventListener("resize", handleResize);
    };

    setTimeout(initialRender, 0); // Delay the initial rendering

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [data, mode]);

  return (
    <>
      <select value={mode} onChange={(e) => setMode(e.target.value)}>
        <option value="Tower Control">Tower Control</option>
        <option value="Rainmaker">Rainmaker</option>
        <option value="Splat Zones">Splat Zones</option>
        <option value="Clam Blitz">Clam Blitz</option>
      </select>
      <div className="chart-container flex-grow" ref={d3Container}>
        <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}></div>
      </div>
    </>
  );
};

export default XChart;
