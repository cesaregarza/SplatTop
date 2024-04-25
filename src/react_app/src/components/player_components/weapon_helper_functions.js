import { calculateSeasonByTimestamp } from "./xchart_helper_functions";

const filterDataAndGroupByWeapon = (data, mode) => {
  const filteredData = data
    ? data.filter((d) => d.mode === mode && d.updated === true)
    : [];

  const groupedByWeaponAndSeason = filteredData.reduce((acc, item) => {
    const { weapon_id, timestamp } = item;
    const season = calculateSeasonByTimestamp(timestamp);
    if (!acc[weapon_id]) {
      acc[weapon_id] = {};
    }
    acc[weapon_id][season] = (acc[weapon_id][season] || 0) + 1;
    return acc;
  }, {});

  return groupedByWeaponAndSeason;
};

const processGroupedData = (groupedData, seasons = null) => {
  const result = {};
  for (const weapon_id in groupedData) {
    let count = 0;
    for (const season in groupedData[weapon_id]) {
      const seasonInt = parseInt(season);
      if (!seasons || seasons.includes(seasonInt)) {
        count += groupedData[weapon_id][season];
      }
    }
    result[weapon_id] = count;
  }
  return result;
};

const calculateTotalPercentage = (groupedByWeaponAndSeason) => {
  let totalCounts = 0;
  for (const weaponSeasons of Object.values(groupedByWeaponAndSeason)) {
    for (const count of Object.values(weaponSeasons)) {
      totalCounts += count;
    }
  }

  const groupedByPercent = {};
  for (const weapon_id of Object.keys(groupedByWeaponAndSeason)) {
    let countsForSeasons = 0;
    for (const count of Object.values(groupedByWeaponAndSeason[weapon_id])) {
      countsForSeasons += count;
    }
    const percentage = (countsForSeasons / totalCounts) * 100;
    groupedByPercent[weapon_id] = percentage;
  }

  return groupedByPercent;
};

const computeDrilldown = (counts, percentageThreshold) => {
  let otherIds = [];
  let otherCount = 0;
  const percentage = calculateTotalPercentage(counts);

  // Identify "other" categories based on the percentage threshold
  for (const key in percentage) {
    if (percentage[key] < percentageThreshold) {
      otherIds.push(key);
      otherCount += Object.values(counts[key]).reduce(
        (acc, val) => acc + val,
        0
      );
    }
  }

  // Prepare series data excluding "other" categories
  let seriesCount = [];
  for (const key in counts) {
    if (!otherIds.includes(key)) {
      seriesCount.push({ name: key, y: counts[key], drilldown: key });
    }
  }

  // Add the "other" category to the series data
  seriesCount.push({ name: "Other", y: otherCount, drilldown: "Other" });

  // Prepare drilldown data for "other" categories
  let drilldownData = [];
  for (const key of otherIds) {
    const sumValues = Object.values(counts[key]).reduce(
      (acc, val) => acc + val,
      0
    );
    drilldownData.push({ name: key, id: "Other", data: [[key, sumValues]] });
  }

  return {
    seriesCount,
    drilldownData,
  };
};

export {
  filterDataAndGroupByWeapon,
  processGroupedData,
  calculateTotalPercentage,
  computeDrilldown,
};
