import React, { useState } from "react";
import { getSeasonName, calculateSeasonNow } from "./xchart_helper_functions";
import SplatZonesIcon from "../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../assets/icons/tower_control.png";
import RainmakerIcon from "../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../assets/icons/clam_blitz.png";

const modeIcons = {
  "Splat Zones": SplatZonesIcon,
  "Tower Control": TowerControlIcon,
  Rainmaker: RainmakerIcon,
  "Clam Blitz": ClamBlitzIcon,
};

const allModes = ["Splat Zones", "Tower Control", "Rainmaker", "Clam Blitz"];

const SeasonResults = (data) => {
  const keyPrefix = "SeasonResults-";
  const activeData = data.data.aggregated_data.season_results;
  const latestData = data.data.aggregated_data.latest_data;

  const latestDataUnique = latestData
    .filter(
      (item, index, self) =>
        index === self.findIndex((t) => t.mode === item.mode)
    )
    .map((item) => ({ ...item, season_number: item.season_number + 2 }));

  const currentSeason = calculateSeasonNow() + 2;
  const combinedData = [...activeData, ...latestDataUnique];
  const seasons = [
    ...new Set(combinedData.map((item) => item.season_number)),
  ].sort((a, b) => b - a);

  const [activeTab, setActiveTab] = useState(currentSeason);

  const filteredData = combinedData.filter(
    (item) => item.season_number === activeTab
  );

  const modeData = allModes.map((mode) => {
    const modeEntry = filteredData.find((item) => item.mode === mode);
    return modeEntry || { mode: mode, rank: "--", x_power: "--" };
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-2xl font-semibold mb-4 text-white">Season Results</h2>
      <div className="flex overflow-x-auto mb-8">
        {seasons.map((season) => (
          <button
            key={`${keyPrefix}${season}`}
            className={`px-4 py-2 mr-2 rounded-lg text-sm font-medium whitespace-nowrap transition duration-300 ease-in-out ${
              activeTab === season
                ? "bg-purple-600 text-white shadow-md"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white"
            } focus:outline-none focus:ring-2 focus:ring-purple-500`}
            onClick={() => setActiveTab(season)}
          >
            {season === currentSeason
              ? `${getSeasonName(season - 2)} (Live)`
              : getSeasonName(season - 2)}
          </button>
        ))}
      </div>

      <table className="w-full text-white">
        <thead>
          <tr className="text-left">
            <th className="px-4 py-2">Mode</th>
            <th className="px-4 py-2">Rank</th>
            <th className="px-4 py-2">X Power</th>
          </tr>
        </thead>
        <tbody>
          {modeData.map((item) => (
            <tr
              key={`${keyPrefix}${item.season_number}-${item.mode}`}
              className="bg-gray-800 shadow-lg"
            >
              <td className="px-4 py-2 flex items-center">
                <img
                  src={modeIcons[item.mode]}
                  alt={`${item.mode} Icon`}
                  className="w-6 h-6 mr-2"
                />
                {item.mode}
              </td>
              <td className="px-4 py-2">{item.rank}</td>
              <td className="px-4 py-2">{item.x_power}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default SeasonResults;
