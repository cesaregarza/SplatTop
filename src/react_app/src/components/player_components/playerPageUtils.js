import { modes as defaultModes } from "../constants";
import {
  calculateSeasonNow,
  getPercentageInSeason,
} from "../utils/season_utils";

const modeShortLabels = {
  "Splat Zones": "SZ",
  "Tower Control": "TC",
  Rainmaker: "RM",
  "Clam Blitz": "CB",
};

const isFiniteNumber = (value) =>
  typeof value === "number" && Number.isFinite(value);

const getTimestampValue = (value) => {
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
};

const getDisplaySeasonNumber = (rawSeasonNumber) =>
  isFiniteNumber(rawSeasonNumber) ? rawSeasonNumber + 1 : null;

const getRawSeasonNumber = (displaySeasonNumber) =>
  isFiniteNumber(displaySeasonNumber) ? displaySeasonNumber - 1 : null;

const getLatestSeasonRows = (latestData = []) =>
  latestData
    .filter(
      (item, index, collection) =>
        index === collection.findIndex((candidate) => candidate.mode === item.mode)
    )
    .map((item) => ({
      ...item,
      season_number: getDisplaySeasonNumber(item.season_number),
    }));

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

const getAvailableModes = (playerData = [], supportedModes = defaultModes) =>
  supportedModes.filter((mode) =>
    playerData.some((entry) => entry.mode === mode)
  );

const getAvailableDisplaySeasons = (chartData = {}) => {
  const aggregatedData = chartData.aggregated_data || {};
  const displaySeasons = new Set(getAvailableSeasonResultTabs(aggregatedData));

  (chartData.player_data || []).forEach((entry) => {
    const displaySeason = getDisplaySeasonNumber(entry.season_number);
    if (isFiniteNumber(displaySeason)) {
      displaySeasons.add(displaySeason);
    }
  });

  (aggregatedData.aggregate_season_data || []).forEach((entry) => {
    const displaySeason = getDisplaySeasonNumber(entry.season_number);
    if (isFiniteNumber(displaySeason)) {
      displaySeasons.add(displaySeason);
    }
  });

  return [...displaySeasons].sort((left, right) => right - left);
};

const getAvailableDisplaySeasonsForMode = (chartData = {}, mode) => {
  const aggregatedData = chartData.aggregated_data || {};
  const displaySeasons = new Set(
    getCombinedSeasonResults(aggregatedData)
      .filter((entry) => entry.mode === mode)
      .map((entry) => entry.season_number)
      .filter(Number.isFinite)
  );

  (chartData.player_data || []).forEach((entry) => {
    if (entry.mode !== mode) {
      return;
    }

    const displaySeason = getDisplaySeasonNumber(entry.season_number);
    if (isFiniteNumber(displaySeason)) {
      displaySeasons.add(displaySeason);
    }
  });

  (aggregatedData.aggregate_season_data || []).forEach((entry) => {
    if (entry.mode !== mode) {
      return;
    }

    const displaySeason = getDisplaySeasonNumber(entry.season_number);
    if (isFiniteNumber(displaySeason)) {
      displaySeasons.add(displaySeason);
    }
  });

  return [...displaySeasons].sort((left, right) => right - left);
};

const getDefaultSeasonResultTab = (aggregatedData = {}) => {
  const availableSeasons = getAvailableSeasonResultTabs(aggregatedData);

  if (availableSeasons.length > 0) {
    return availableSeasons[0];
  }

  return getDisplaySeasonNumber(calculateSeasonNow());
};

const getDefaultPlayerMode = (
  playerData = [],
  supportedModes = defaultModes
) => {
  const availableModes = getAvailableModes(playerData, supportedModes);
  return availableModes[0] || supportedModes[0];
};

const getDefaultSelectedDisplaySeason = (chartData = {}, mode) => {
  const modeSeasons = getAvailableDisplaySeasonsForMode(chartData, mode);
  if (modeSeasons.length > 0) {
    return modeSeasons[0];
  }

  const allSeasons = getAvailableDisplaySeasons(chartData);
  if (allSeasons.length > 0) {
    return allSeasons[0];
  }

  return getDisplaySeasonNumber(calculateSeasonNow());
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

const getHistoricalSeasonResults = (chartData = {}) =>
  chartData.aggregated_data?.season_results || [];

const getBestMode = (seasonResults = []) => {
  const modeStats = {};

  seasonResults.forEach((row) => {
    if (!row.mode || !isFiniteNumber(row.rank)) {
      return;
    }

    if (!modeStats[row.mode]) {
      modeStats[row.mode] = {
        mode: row.mode,
        bestRank: row.rank,
        top10Count: 0,
        top500Count: 0,
      };
    }

    modeStats[row.mode].bestRank = Math.min(modeStats[row.mode].bestRank, row.rank);

    if (row.rank <= 10) {
      modeStats[row.mode].top10Count += 1;
    }

    if (row.rank <= 500) {
      modeStats[row.mode].top500Count += 1;
    }
  });

  return Object.values(modeStats).sort((left, right) => {
    if (left.bestRank !== right.bestRank) {
      return left.bestRank - right.bestRank;
    }

    if (left.top10Count !== right.top10Count) {
      return right.top10Count - left.top10Count;
    }

    if (left.top500Count !== right.top500Count) {
      return right.top500Count - left.top500Count;
    }

    return left.mode.localeCompare(right.mode);
  })[0]?.mode || null;
};

const getCareerHighlights = (chartData = {}) => {
  const seasonResults = getHistoricalSeasonResults(chartData);
  const totalTop10 = seasonResults.filter(
    (row) => isFiniteNumber(row.rank) && row.rank <= 10
  ).length;
  const totalTop500 = seasonResults.filter(
    (row) => isFiniteNumber(row.rank) && row.rank <= 500
  ).length;
  const bestFinish = seasonResults
    .map((row) => row.rank)
    .filter((rank) => isFiniteNumber(rank) && rank > 0)
    .sort((left, right) => left - right)[0] || null;

  const groupedSeasons = seasonResults.reduce((accumulator, row) => {
    if (!isFiniteNumber(row.season_number)) {
      return accumulator;
    }

    if (!accumulator[row.season_number]) {
      accumulator[row.season_number] = {
        season_number: row.season_number,
        region: row.region ?? null,
        finishes: [],
      };
    }

    if (accumulator[row.season_number].region == null && row.region != null) {
      accumulator[row.season_number].region = row.region;
    }

    if (isFiniteNumber(row.rank) && row.rank <= 500) {
      accumulator[row.season_number].finishes.push({
        mode: row.mode,
        rank: row.rank,
        shortLabel: modeShortLabels[row.mode] || row.mode,
      });
    }

    return accumulator;
  }, {});

  const notableSeasons = Object.values(groupedSeasons)
    .filter((season) => season.finishes.length > 0)
    .map((season) => ({
      ...season,
      finishes: [...season.finishes].sort((left, right) => left.rank - right.rank),
    }))
    .sort((left, right) => right.season_number - left.season_number);

  return {
    totalTop10,
    totalTop500,
    diamondSeasonCount: countDiamondSeasons(seasonResults),
    bestFinish,
    bestMode: getBestMode(seasonResults),
    notableSeasons,
  };
};

const getSeasonPoints = (chartData = {}, displaySeasonNumber, mode) => {
  const rawSeasonNumber = getRawSeasonNumber(displaySeasonNumber);

  return [...(chartData.player_data || [])]
    .filter(
      (entry) =>
        entry.mode === mode && entry.season_number === rawSeasonNumber
    )
    .sort(
      (left, right) => getTimestampValue(left.timestamp) - getTimestampValue(right.timestamp)
    );
};

const getModeAnalysisSummary = (chartData = {}, mode, displaySeasonNumber) => {
  const aggregatedData = chartData.aggregated_data || {};
  const rawSeasonNumber = getRawSeasonNumber(displaySeasonNumber);
  const seasonPoints = getSeasonPoints(chartData, displaySeasonNumber, mode);
  const pointValues = seasonPoints
    .map((entry) => entry.x_power)
    .filter(isFiniteNumber);
  const latestPointXp =
    pointValues.length > 0 ? pointValues[pointValues.length - 1] : null;
  const seasonResult = getCombinedSeasonResults(aggregatedData).find(
    (entry) =>
      entry.mode === mode && entry.season_number === displaySeasonNumber
  );
  const seasonAggregate = (aggregatedData.aggregate_season_data || []).find(
    (entry) => entry.season_number === rawSeasonNumber && entry.mode === mode
  );
  const currentXp = isFiniteNumber(latestPointXp)
    ? latestPointXp
    : isFiniteNumber(seasonResult?.x_power)
      ? seasonResult.x_power
      : null;
  const peakCandidates = [
    seasonAggregate?.peak_x_power,
    seasonResult?.x_power,
    ...pointValues,
  ].filter(isFiniteNumber);
  const peakXp =
    peakCandidates.length > 0 ? Math.max(...peakCandidates) : null;
  const currentSeason = calculateSeasonNow();
  const isCurrent = rawSeasonNumber === currentSeason;
  const seasonElapsed = isCurrent
    ? Math.max(
        0,
        Math.min(100, getPercentageInSeason(new Date(), rawSeasonNumber))
      )
    : 100;
  const trackedUpdates = pointValues.length;

  return {
    currentXp,
    isCurrent,
    isSparse: isCurrent && trackedUpdates <= 3,
    peakXp,
    rank: isFiniteNumber(seasonResult?.rank) ? seasonResult.rank : null,
    rawSeasonNumber,
    seasonElapsed,
    trackedUpdates,
  };
};

const getSeasonArchiveRows = (chartData = {}, mode) => {
  const aggregatedData = chartData.aggregated_data || {};
  const combinedResults = getCombinedSeasonResults(aggregatedData);
  const displaySeasons = getAvailableDisplaySeasons(chartData);

  return displaySeasons.map((displaySeasonNumber) => {
    const rawSeasonNumber = getRawSeasonNumber(displaySeasonNumber);
    const modeResult = combinedResults.find(
      (entry) =>
        entry.season_number === displaySeasonNumber && entry.mode === mode
    );
    const regionResult = combinedResults.find(
      (entry) => entry.season_number === displaySeasonNumber && entry.region != null
    );
    const sparklineRows = getSeasonPoints(chartData, displaySeasonNumber, mode);
    const seasonAggregate = (aggregatedData.aggregate_season_data || []).find(
      (entry) => entry.season_number === rawSeasonNumber && entry.mode === mode
    );
    const peakFromSnapshots = sparklineRows
      .map((entry) => entry.x_power)
      .filter(isFiniteNumber)
      .sort((left, right) => right - left)[0];
    const peakXp = isFiniteNumber(seasonAggregate?.peak_x_power)
      ? seasonAggregate.peak_x_power
      : peakFromSnapshots || null;

    return {
      season_number: displaySeasonNumber,
      raw_season_number: rawSeasonNumber,
      region: regionResult?.region ?? modeResult?.region ?? null,
      finishRank: isFiniteNumber(modeResult?.rank) ? modeResult.rank : null,
      peakXp,
      sparklineValues: sparklineRows
        .map((entry) => entry.x_power)
        .filter(isFiniteNumber),
      hasModeData:
        sparklineRows.length > 0 ||
        isFiniteNumber(modeResult?.rank) ||
        isFiniteNumber(peakXp),
    };
  });
};

export {
  countDiamondSeasons,
  getAvailableDisplaySeasons,
  getAvailableDisplaySeasonsForMode,
  getAvailableModes,
  getAvailableSeasonResultTabs,
  getBestMode,
  getBestRank,
  getBestXp,
  getCareerHighlights,
  getCombinedSeasonResults,
  getDefaultPlayerMode,
  getDefaultSeasonResultTab,
  getDefaultSelectedDisplaySeason,
  getDisplaySeasonNumber,
  getModeAnalysisSummary,
  getPlayerSummary,
  getRawSeasonNumber,
  getSeasonArchiveRows,
  getSeasonPoints,
  modeShortLabels,
  sortAliasesByLastSeen,
  splitSplashtag,
};
