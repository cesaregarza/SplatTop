import React, { useState } from "react";
import { getSeasonName, calculateSeasonNow } from "./xchart_helper_functions";
import { getImageFromId } from "./weapon_helper_functions";
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

const SeasonResults = ({ data, weaponReferenceData }) => {
  const keyPrefix = "SeasonResults-";
  const activeData = data.aggregated_data.season_results;
  const latestData = data.aggregated_data.latest_data;
  const weaponData = data.aggregated_data.weapon_counts;
  const aggSeasonData = data.aggregated_data.aggregate_season_data;

  const latestDataUnique = latestData
    .filter(
      (item, index, self) =>
        index === self.findIndex((t) => t.mode === item.mode)
    )
    .map((item) => ({ ...item, season_number: item.season_number + 1 }));

  const combinedData = [...activeData, ...latestDataUnique];
  const seasons = [
    ...new Set(combinedData.map((item) => item.season_number)),
  ].sort((a, b) => b - a);
  const currentSeason = calculateSeasonNow() + 1;
  const [activeTab, setActiveTab] = useState(currentSeason);

  const filteredData = combinedData
    .filter((item) => item.season_number === activeTab)
    .map((item) => {
      const { season_number, mode } = item;

      // Find the most popular weapon for the current season_number+mode combination
      const popularWeapon = weaponData
        .filter(
          (weapon) =>
            weapon.season_number === season_number - 1 && weapon.mode === mode
        )
        .sort((a, b) => b.count - a.count)[0];

      // Find the corresponding peak_x_power for the current season_number+mode combination
      const seasonData = aggSeasonData.find(
        (data) => data.season_number === season_number - 1 && data.mode === mode
      );

      return {
        ...item,
        popular_weapon: popularWeapon ? popularWeapon.weapon_id : null,
        peak_x_power: seasonData ? seasonData.peak_x_power : null,
      };
    });

  const modeData = allModes.map((mode) => {
    const modeEntry = filteredData.find((item) => item.mode === mode);
    return modeEntry || { mode: mode, rank: "--", x_power: "--" };
  });

  return (
    <div className="container mx-auto px-4 py-4">
      <h2 className="text-2xl font-semibold mb-4 text-white">Season Results</h2>
      <div className="flex overflow-x-auto">
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
              ? `${getSeasonName(season - 1)} (Live)`
              : getSeasonName(season - 1)}
          </button>
        ))}
      </div>

      <div className="relative overflow-x-auto">
        <table className="w-full text-white">
          <thead>
            <tr className="text-left">
              <th className="px-4 py-2 text-sm">Mode</th>
              <th className="px-4 py-2 text-sm">Rank</th>
              <th className="px-4 py-2 text-sm">Final XP</th>
              <th className="px-4 py-2 text-sm">Peak XP</th>
              <th className="px-4 py-2 text-sm">
                {activeTab === currentSeason
                  ? "Current Weapon"
                  : "Final Weapon"}
              </th>
              <th className="px-4 py-2 text-sm">Most Used Weapon</th>
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
                    className="w-8 h-8 mr-2"
                  />
                </td>
                <td className="px-4 py-2">
                  {item.rank >= 1 && item.rank <= 10 ? (
                    <span className="text-purplelight font-bold">
                      {item.rank}
                    </span>
                  ) : (
                    item.rank
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  {typeof item.x_power !== "string" ? (
                    <>
                      <span className="text-purplelight text-lg">
                        {item.x_power.toFixed(1).toString().slice(0, 2)}
                      </span>
                      <span className="text-sm">
                        {item.x_power.toFixed(1).toString().slice(2)}
                      </span>
                    </>
                  ) : (
                    item.x_power
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  {typeof item.peak_x_power !== "undefined" ? (
                    <>
                      <span className="text-purplelight text-lg">
                        {item.peak_x_power.toFixed(1).toString().slice(0, 2)}
                      </span>
                      <span className="text-sm">
                        {item.peak_x_power.toFixed(1).toString().slice(2)}
                      </span>
                    </>
                  ) : (
                    "--"
                  )}
                </td>
                <td className="px-4 py-2">
                  {item.weapon_id ? (
                    <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mx-auto">
                      {weaponReferenceData ? (
                        <img
                          src={getImageFromId(
                            item.weapon_id,
                            weaponReferenceData
                          )}
                          alt="Weapon name not yet supported"
                          className="h-10 w-10 object-cover aspect-square"
                        />
                      ) : null}
                    </div>
                  ) : (
                    <div className="flex justify-center items-center h-10">
                      --
                    </div>
                  )}
                </td>
                <td className="px-4 py-2">
                  {item.popular_weapon ? (
                    <div className="bg-black rounded-full flex justify-center items-center h-10 w-10 mx-auto">
                      {weaponReferenceData ? (
                        <img
                          src={getImageFromId(
                            item.popular_weapon,
                            weaponReferenceData
                          )}
                          alt="Weapon name not yet supported"
                          className="h-10 w-10 object-cover aspect-square"
                        />
                      ) : null}
                    </div>
                  ) : (
                    <div className="flex justify-center items-center h-10">
                      --
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SeasonResults;
