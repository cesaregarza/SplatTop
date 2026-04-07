import React, { useEffect, useState } from "react";
import { getSeasonName, calculateSeasonNow } from "../utils/season_utils";
import { modeKeyMap } from "../constants";
import { getImageFromId } from "./weapon_helper_functions";
import { useTranslation } from "react-i18next";
import SplatZonesIcon from "../../assets/icons/splat_zones.png";
import TowerControlIcon from "../../assets/icons/tower_control.png";
import RainmakerIcon from "../../assets/icons/rainmaker.png";
import ClamBlitzIcon from "../../assets/icons/clam_blitz.png";
import {
  getAvailableDisplaySeasons,
  getCombinedSeasonResults,
  getDefaultSeasonResultTab,
} from "./playerPageUtils";

const modeIcons = {
  "Splat Zones": SplatZonesIcon,
  "Tower Control": TowerControlIcon,
  Rainmaker: RainmakerIcon,
  "Clam Blitz": ClamBlitzIcon,
};

const allModes = ["Splat Zones", "Tower Control", "Rainmaker", "Clam Blitz"];

const formatXpValue = (value) => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }

  return value.toFixed(1);
};

const WeaponCell = ({ weaponId, weaponReferenceData }) => {
  if (!weaponId) {
    return <div className="flex h-9 items-center justify-center">--</div>;
  }

  return (
    <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-black">
      {weaponReferenceData ? (
        <img
          src={getImageFromId(weaponId, weaponReferenceData)}
          alt="Weapon name not yet supported"
          className="aspect-square h-9 w-9 object-cover"
        />
      ) : null}
    </div>
  );
};

const SeasonResults = ({
  data,
  weaponReferenceData,
  headerControls = null,
  activeSeason = null,
  onSeasonChange = null,
}) => {
  const { t } = useTranslation("player");
  const { t: g } = useTranslation("game");
  const keyPrefix = "SeasonResults-";
  const aggregatedData = data.aggregated_data;
  const weaponData = aggregatedData.weapon_counts;
  const aggSeasonData = aggregatedData.aggregate_season_data;
  const combinedData = getCombinedSeasonResults(aggregatedData);
  const seasons = getAvailableDisplaySeasons(data);
  const currentSeason = calculateSeasonNow() + 1;
  const [internalActiveSeason, setInternalActiveSeason] = useState(() =>
    getDefaultSeasonResultTab(aggregatedData)
  );
  const resolvedActiveSeason =
    typeof activeSeason === "number" && Number.isFinite(activeSeason)
      ? activeSeason
      : internalActiveSeason;

  const handleSeasonChange = (nextSeason) => {
    if (typeof onSeasonChange === "function") {
      onSeasonChange(nextSeason);
    }

    if (!(typeof activeSeason === "number" && Number.isFinite(activeSeason))) {
      setInternalActiveSeason(nextSeason);
    }
  };

  useEffect(() => {
    if (!seasons.includes(resolvedActiveSeason)) {
      handleSeasonChange(seasons[0] || getDefaultSeasonResultTab(aggregatedData));
    }
  }, [aggregatedData, resolvedActiveSeason, seasons]); // eslint-disable-line react-hooks/exhaustive-deps

  const filteredData = combinedData
    .filter((item) => item.season_number === resolvedActiveSeason)
    .map((item) => {
      const { season_number, mode } = item;

      const popularWeapon = weaponData
        .filter(
          (weapon) =>
            weapon.season_number === season_number - 1 && weapon.mode === mode
        )
        .sort((left, right) => right.count - left.count)[0];

      const seasonEntry = aggSeasonData.find(
        (entry) =>
          entry.season_number === season_number - 1 && entry.mode === mode
      );

      return {
        ...item,
        popular_weapon: popularWeapon ? popularWeapon.weapon_id : null,
        peak_x_power: seasonEntry ? seasonEntry.peak_x_power : null,
      };
    });

  const modeData = allModes.map((mode) => {
    const modeEntry = filteredData.find((item) => item.mode === mode);

    return (
      modeEntry || {
        season_number: resolvedActiveSeason,
        mode,
        rank: "--",
        x_power: null,
        peak_x_power: null,
        weapon_id: null,
        popular_weapon: null,
      }
    );
  });

  const statusText =
    resolvedActiveSeason === currentSeason
      ? t("results.status.live")
      : t("results.status.final");
  const visibleSeasons = seasons.slice(0, 4);
  const overflowSeasons = seasons.slice(4);
  const archiveValue = overflowSeasons.includes(resolvedActiveSeason)
    ? String(resolvedActiveSeason)
    : "";

  return (
    <section className="rounded-lg border border-gray-800/60 bg-gray-950/25">
      <div className="border-b border-gray-800/60 px-4 py-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">
            {t("sections.season_snapshot")}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
            <h2 className="text-lg font-semibold text-white">
              {t("results.title")}
            </h2>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-400">
              {statusText}
            </p>
          </div>
        </div>
        {headerControls ? (
          <div className="mt-3">{headerControls}</div>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-gray-800/60 px-4 py-3">
        {visibleSeasons.map((season) => (
          <button
            key={`${keyPrefix}${season}`}
            className={`rounded-md border px-3 py-1.5 text-sm font-medium whitespace-nowrap transition ${
              resolvedActiveSeason === season
                ? "border-purple-500/60 bg-purple-950/40 text-purple-100"
                : "border-gray-800 bg-black/20 text-gray-300 hover:border-gray-700 hover:bg-gray-900/70 hover:text-white"
            } focus:outline-hidden focus:ring-2 focus:ring-purple-500`}
            onClick={() => handleSeasonChange(season)}
          >
            <span className="flex items-center gap-2">
              <span>{getSeasonName(season - 1, g)}</span>
              {season === currentSeason ? (
                <span className="rounded-full border border-purple-500/50 bg-purple-950/50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-purple-100">
                  {t("xchart.live_indicator")}
                </span>
              ) : null}
            </span>
          </button>
        ))}
        {overflowSeasons.length > 0 ? (
          <label className="ml-auto flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
            <span>{t("results.archive")}</span>
            <select
              value={archiveValue}
              onChange={(event) => {
                if (event.target.value) {
                  handleSeasonChange(Number(event.target.value));
                }
              }}
              className="rounded-md border border-gray-800 bg-black/20 px-3 py-1.5 text-sm font-medium normal-case tracking-normal text-gray-200 focus:border-purple-500 focus:outline-hidden"
              style={{ colorScheme: "dark" }}
            >
              <option
                value=""
                style={{ backgroundColor: "#030712", color: "#e5e7eb" }}
              >
                {t("results.archive")}
              </option>
              {overflowSeasons.map((season) => (
                <option
                  key={`${keyPrefix}archive-${season}`}
                  value={season}
                  style={{ backgroundColor: "#030712", color: "#e5e7eb" }}
                >
                  {getSeasonName(season - 1, g)}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <div className="overflow-x-auto px-4 py-2">
        <table className="min-w-[40rem] w-full text-white">
          <thead className="border-b border-gray-800 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-400">
            <tr>
              <th className="px-3 py-2">{t("results.table.mode")}</th>
              <th className="px-3 py-2">{t("results.table.rank")}</th>
              <th className="px-3 py-2">
                {resolvedActiveSeason === currentSeason
                  ? t("results.table.current_xp")
                  : t("results.table.final_xp")}
              </th>
              <th className="px-3 py-2">{t("results.table.peak_xp")}</th>
              <th className="px-3 py-2">
                {resolvedActiveSeason === currentSeason
                  ? t("results.table.current_weapon")
                  : t("results.table.final_weapon")}
              </th>
              <th className="px-3 py-2">
                {t("results.table.most_used_weapon")}
              </th>
            </tr>
          </thead>
          <tbody>
            {modeData.map((item) => (
              <tr
                key={`${keyPrefix}${item.season_number}-${item.mode}`}
                className="border-b border-gray-900/80 align-middle text-sm last:border-b-0"
              >
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2.5">
                    <img
                      src={modeIcons[item.mode]}
                      alt={`${item.mode} Icon`}
                      className="h-7 w-7"
                    />
                    <span className="font-medium">{g(modeKeyMap[item.mode])}</span>
                  </div>
                </td>
                <td className="px-3 py-2.5 tabular-nums">
                  {item.rank >= 1 && item.rank <= 10 ? (
                    <span className="font-semibold text-purple-200">
                      {item.rank}
                    </span>
                  ) : (
                    item.rank
                  )}
                </td>
                <td className="px-3 py-2.5 text-right font-medium tabular-nums text-white">
                  {formatXpValue(item.x_power)}
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums text-gray-300">
                  {formatXpValue(item.peak_x_power)}
                </td>
                <td className="px-3 py-2.5">
                  <WeaponCell
                    weaponId={item.weapon_id}
                    weaponReferenceData={weaponReferenceData}
                  />
                </td>
                <td className="px-3 py-2.5">
                  <WeaponCell
                    weaponId={item.popular_weapon}
                    weaponReferenceData={weaponReferenceData}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default SeasonResults;
