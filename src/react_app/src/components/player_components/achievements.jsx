import React from "react";
import SplatZonesIcon from "../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../assets/icons/tower_control.png";
import RainmakerIcon from "../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../assets/icons/clam_blitz.png";
import DiamondBadge from "../top500_components/badges/diamond_badge";
import Top10Badge from "../top500_components/badges/top10_badge";
import Top500Badge from "../top500_components/badges/top500_badge";
import CombinedBadge from "../top500_components/badges/combined_badge";
import TakorokaIcon from "../../assets/icons/takoroka.png";
import TentatekIcon from "../../assets/icons/tentatek.png";
import { getSeasonName } from "./xchart_helper_functions";

const modeIcons = {
  "Splat Zones": SplatZonesIcon,
  "Tower Control": TowerControlIcon,
  Rainmaker: RainmakerIcon,
  "Clam Blitz": ClamBlitzIcon,
};

const allModes = ["Splat Zones", "Tower Control", "Rainmaker", "Clam Blitz"];

const disabledBadge = true;
const badgeSize = "h-10 w-10";
const regionBadgeSize = "h-10 w-10";
const columnPaddingX = "px-2";
const rowPaddingY = "py-1";

const Achievements = ({ data }) => {
  const activeData = data.aggregated_data.season_results;

  const seasonCounts = {};
  const modeCounts = {
    "Splat Zones": { top10: 0, top500: 0 },
    "Tower Control": { top10: 0, top500: 0 },
    Rainmaker: { top10: 0, top500: 0 },
    "Clam Blitz": { top10: 0, top500: 0 },
  };

  activeData.forEach((result) => {
    const { season_number, mode, rank } = result;
    if (!seasonCounts[season_number]) {
      seasonCounts[season_number] = {
        top10: 0,
        top500: 0,
        hasDiamond: true,
      };
    }

    if (rank >= 1 && rank <= 10) {
      seasonCounts[season_number].top10++;
      modeCounts[mode].top10++;
    } else if (rank > 10 && rank <= 500) {
      seasonCounts[season_number].top500++;
      modeCounts[mode].top500++;
    }

    if (rank > 10) {
      seasonCounts[season_number].hasDiamond = false;
    }
  });

  const totalTop10 = Object.values(modeCounts).reduce(
    (acc, curr) => acc + curr.top10,
    0
  );
  const totalTop500 = Object.values(modeCounts).reduce(
    (acc, curr) => acc + curr.top500,
    0
  );

  return (
    <div className="container mx-auto px-4 py-4 flex justify-center">
      <div className="w-full max-w-6xl">
        <h2 className="text-2xl font-semibold mb-4 text-white text-center">
          Achievements
        </h2>
        <div className="relative max-h-96 overflow-x-auto">
          <table className="min-w-max text-white mx-auto">
            <thead>
              <tr className="text-left">
                <th className={columnPaddingX + " " + rowPaddingY}>Season</th>
                <th className={columnPaddingX + " " + rowPaddingY}>Region</th>
                {allModes.map((mode) => (
                  <th key={mode} className={columnPaddingX + " " + rowPaddingY}>
                    <img
                      src={modeIcons[mode]}
                      alt={mode}
                      className="w-6 h-6 mx-auto"
                    />
                  </th>
                ))}
                <th className={columnPaddingX + " " + rowPaddingY}>Total</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(seasonCounts).map(([season, counts]) => (
                <tr key={season} className="bg-gray-800 shadow-lg">
                  <td className={columnPaddingX + " " + rowPaddingY}>
                    <span className="text-sm">
                      {getSeasonName(Number(season) - 1)}
                    </span>
                  </td>
                  <td className={columnPaddingX + " " + rowPaddingY}>
                    <img
                      src={
                        activeData.find(
                          (result) => result.season_number === Number(season)
                        ).region
                          ? TakorokaIcon
                          : TentatekIcon
                      }
                      alt="Region Icon"
                      className={regionBadgeSize + " mx-auto"}
                    />
                  </td>
                  {allModes.map((mode) => {
                    const modeResult = activeData.find(
                      (result) =>
                        result.season_number === Number(season) &&
                        result.mode === mode
                    );
                    const top10 = modeResult && modeResult.rank <= 10 ? 1 : 0;
                    const top500 =
                      modeResult &&
                      modeResult.rank > 10 &&
                      modeResult.rank <= 500
                        ? 1
                        : 0;
                    return (
                      <td
                        key={`${season}-${mode}`}
                        className={
                          columnPaddingX + " " + rowPaddingY + " text-center"
                        }
                      >
                        {top10 > 0 && (
                          <Top10Badge
                            count={top10}
                            disable={disabledBadge}
                            size={badgeSize}
                            className="mr-1"
                          />
                        )}
                        {top500 > 0 && (
                          <Top500Badge
                            count={top500}
                            disable={disabledBadge}
                            size={badgeSize}
                          />
                        )}
                        {top10 === 0 && top500 === 0 && "--"}
                      </td>
                    );
                  })}
                  <td className={columnPaddingX + " " + rowPaddingY}>
                    {counts.hasDiamond ? (
                      <DiamondBadge
                        count={1}
                        disable={false}
                        size={badgeSize}
                        className="mr-2"
                      />
                    ) : (
                      <CombinedBadge
                        top10Count={counts.top10}
                        top500Count={counts.top500}
                        disable={disabledBadge}
                        size={badgeSize}
                      />
                    )}
                  </td>
                </tr>
              ))}
              <tr className="bg-gray-800 shadow-lg">
                <td className={columnPaddingX + " " + rowPaddingY}>Total</td>
                <td className={columnPaddingX + " " + rowPaddingY}></td>
                {allModes.map((mode) => (
                  <td
                    key={`total-${mode}`}
                    className={
                      columnPaddingX + " " + rowPaddingY + " text-center"
                    }
                  >
                    <CombinedBadge
                      top10Count={modeCounts[mode].top10}
                      top500Count={modeCounts[mode].top500}
                      disable={false}
                      size={badgeSize}
                    />
                  </td>
                ))}
                <td className={columnPaddingX + " " + rowPaddingY}>
                  <CombinedBadge
                    top10Count={totalTop10}
                    top500Count={totalTop500}
                    disable={disabledBadge}
                    size={badgeSize}
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Achievements;
