import { modes as defaultModes } from "../constants";
import { calculateSeasonNow } from "../utils/season_utils";

const isFiniteNumber = (value) =>
  typeof value === "number" && Number.isFinite(value);

const getTimestampValue = (value) => {
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
};

const getLatestSeasonRows = (latestData = []) =>
  latestData
    .filter(
      (item, index, collection) =>
        index === collection.findIndex((candidate) => candidate.mode === item.mode)
    )
    .map((item) => ({ ...item, season_number: item.season_number + 1 }));

const sortAliasesByLastSeen = (aliases = []) =>
  [...aliases].sort(
    (left, right) =>
      getTimestampValue(right.latest_updated_timestamp) -
      getTimestampValue(left.latest_updated_timestamp)
  );

const splitSplashtag = (splashtag = "") => {
  const match = splashtag.match(/^(.*?)(#\d{4}[0-9a-f]?)$/i);

  if (!match) {
    return { namePart: splashtag, tagPart: "" };
  }

  return {
    namePart: match[1],
    tagPart: match[2],
  };
};

const getCombinedSeasonResults = (aggregatedData = {}) => {
  const activeData = Array.isArray(aggregatedData.season_results)
    ? aggregatedData.season_results
    : [];
  const latestData = Array.isArray(aggregatedData.latest_data)
    ? aggregatedData.latest_data
    : [];

  return [...activeData, ...getLatestSeasonRows(latestData)];
};

const getAvailableSeasonResultTabs = (aggregatedData = {}) =>
  Array.from(
    new Set(
      getCombinedSeasonResults(aggregatedData)
        .map((item) => item.season_number)
        .filter(Number.isFinite)
    )
  ).sort((left, right) => right - left);

const getDefaultSeasonResultTab = (aggregatedData = {}) => {
  const availableSeasons = getAvailableSeasonResultTabs(aggregatedData);

  if (availableSeasons.length > 0) {
    return availableSeasons[0];
  }

  return calculateSeasonNow() + 1;
};

const getAvailableModes = (playerData = [], supportedModes = defaultModes) =>
  supportedModes.filter((mode) =>
    playerData.some((entry) => entry.mode === mode)
  );

const getDefaultPlayerMode = (
  playerData = [],
  supportedModes = defaultModes
) => {
  const availableModes = getAvailableModes(playerData, supportedModes);
  return availableModes[0] || supportedModes[0];
};

const getActiveModeCount = (chartData, supportedModes = defaultModes) => {
  if (!chartData) {
    return null;
  }

  const activeModes = new Set();

  (chartData.player_data || []).forEach((entry) => {
    if (entry.mode) {
      activeModes.add(entry.mode);
    }
  });

  (chartData.aggregated_data?.latest_data || []).forEach((entry) => {
    if (entry.mode) {
      activeModes.add(entry.mode);
    }
  });

  return supportedModes.filter((mode) => activeModes.has(mode)).length;
};

const getBestRank = (chartData) => {
  if (!chartData) {
    return null;
  }

  const rankValues = [
    ...(chartData.aggregated_data?.season_results || []).map((row) => row.rank),
    ...(chartData.aggregated_data?.latest_data || []).map((row) => row.rank),
  ].filter((value) => isFiniteNumber(value) && value > 0);

  if (rankValues.length === 0) {
    return null;
  }

  return Math.min(...rankValues);
};

const getBestXp = (chartData) => {
  if (!chartData) {
    return null;
  }

  const xpValues = [
    ...(chartData.aggregated_data?.season_results || []).map((row) => row.x_power),
    ...(chartData.aggregated_data?.latest_data || []).map((row) => row.x_power),
    ...(chartData.aggregated_data?.aggregate_season_data || []).map(
      (row) => row.peak_x_power
    ),
  ].filter(isFiniteNumber);

  if (xpValues.length === 0) {
    return null;
  }

  return Math.max(...xpValues);
};

const countDiamondSeasons = (seasonResults = []) => {
  const seasonIndex = {};

  seasonResults.forEach(({ season_number, rank }) => {
    if (!Number.isFinite(season_number)) {
      return;
    }

    if (!Object.prototype.hasOwnProperty.call(seasonIndex, season_number)) {
      seasonIndex[season_number] = true;
    }

    if (!isFiniteNumber(rank) || rank > 10) {
      seasonIndex[season_number] = false;
    }
  });

  return Object.values(seasonIndex).filter(Boolean).length;
};

const getPlayerSummary = (
  aliasData = [],
  chartData,
  supportedModes = defaultModes
) => {
  const aliases = sortAliasesByLastSeen(aliasData);

  return {
    aliases,
    currentAlias: aliases[0]?.splashtag || null,
    lastSeen: aliases[0]?.latest_updated_timestamp || null,
    aliasCount: aliases.length,
    bestRank: getBestRank(chartData),
    bestXp: getBestXp(chartData),
    activeModeCount: getActiveModeCount(chartData, supportedModes),
    diamondSeasonCount: countDiamondSeasons(
      chartData?.aggregated_data?.season_results || []
    ),
  };
};

export {
  countDiamondSeasons,
  getAvailableModes,
  getAvailableSeasonResultTabs,
  getBestRank,
  getBestXp,
  getCombinedSeasonResults,
  getDefaultPlayerMode,
  getDefaultSeasonResultTab,
  getPlayerSummary,
  sortAliasesByLastSeen,
  splitSplashtag,
};
