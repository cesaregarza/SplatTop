import React from "react";
import { useTranslation } from "react-i18next";
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
import { countDiamondSeasons } from "./playerPageUtils";

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
const rowPaddingY = "py-2";

const Achievements = ({ data }) => {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
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
      seasonCounts[season_number].top10 += 1;
      modeCounts[mode].top10 += 1;
    } else if (rank > 10 && rank <= 500) {
      seasonCounts[season_number].top500 += 1;
      modeCounts[mode].top500 += 1;
    }

    if (rank > 10) {
      seasonCounts[season_number].hasDiamond = false;
    }
  });

  const totalTop10 = Object.values(modeCounts).reduce(
    (accumulator, value) => accumulator + value.top10,
    0
  );
  const totalTop500 = Object.values(modeCounts).reduce(
    (accumulator, value) => accumulator + value.top500,
    0
  );
  const diamondSeasonCount = countDiamondSeasons(activeData);
  const seasonEntries = Object.entries(seasonCounts).sort(
    ([left], [right]) => Number(right) - Number(left)
  );
  const summaryText = t("achievements.summary")
    .replace("%TOP10%", totalTop10)
    .replace("%TOP500%", totalTop500)
    .replace("%DIAMOND%", diamondSeasonCount);

  return (
    <section className="rounded-lg border border-gray-800/60 bg-gray-950/25 p-4">
      <div className="mb-3 border-b border-gray-800/60 pb-3">
        <h2 className="text-lg font-semibold text-white">
          {t("achievements.title")}
        </h2>
        <p className="mt-1 text-sm text-gray-400">{summaryText}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[40rem] mx-auto text-white">
          <thead className="border-b border-gray-800 text-left text-xs uppercase tracking-[0.12em] text-gray-400">
            <tr>
              <th className={columnPaddingX + " " + rowPaddingY}>
                {t("achievements.table.season")}
              </th>
              <th className={columnPaddingX + " " + rowPaddingY}>
                {t("achievements.table.region")}
              </th>
              {allModes.map((mode) => (
                <th key={mode} className={columnPaddingX + " " + rowPaddingY}>
                  <img
                    src={modeIcons[mode]}
                    alt={mode}
                    className="mx-auto h-6 w-6"
                  />
                </th>
              ))}
              <th className={columnPaddingX + " " + rowPaddingY}>
                {t("achievements.table.total")}
              </th>
            </tr>
          </thead>
          <tbody>
            {seasonEntries.map(([season, counts]) => (
              <tr
                key={season}
                className="border-b border-gray-900/80"
              >
                <td className={columnPaddingX + " " + rowPaddingY}>
                  <span className="text-sm">
                    {getSeasonName(Number(season) - 1, g)}
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
            <tr className="border-t border-gray-800/80 bg-gray-900/40">
              <td className={columnPaddingX + " " + rowPaddingY}>
                {t("achievements.table.total")}
              </td>
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
    </section>
  );
};

export default Achievements;
