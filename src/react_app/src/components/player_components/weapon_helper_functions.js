function processGroupedData(groupedData, seasons = null) {
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
}

function calculateTotalPercentage(aggregatedData) {
  let totalCounts = aggregatedData.reduce(
    (acc, val) => acc + val.total_count,
    0
  );
  const groupedByPercent = {};
  for (const row of aggregatedData) {
    if (row.weapon_id in groupedByPercent) {
      groupedByPercent[row.weapon_id] += (row.total_count / totalCounts) * 100;
    } else {
      groupedByPercent[row.weapon_id] = (row.total_count / totalCounts) * 100;
    }
  }
  return groupedByPercent;
}

function computeDrilldown(counts, percentageThreshold, weaponReferenceData) {
  const aggCounts = {};
  const classAgg = {};

  // Aggregate counts by weapon_id
  for (const row of counts) {
    if (row.weapon_id in aggCounts) {
      aggCounts[row.weapon_id].total_count += row.total_count;
      aggCounts[row.weapon_id].win_count += row.sum;
    } else {
      aggCounts[row.weapon_id] = {
        total_count: row.total_count,
        win_count: row.sum,
      };
    }
  }

  // Aggregate counts by class
  for (const weapon_id in aggCounts) {
    const weaponClass = weaponReferenceData[weapon_id]?.class || "Unknown";
    if (weaponClass in classAgg) {
      classAgg[weaponClass].total_count += aggCounts[weapon_id].total_count;
      classAgg[weaponClass].weapons.push(weapon_id);
    } else {
      classAgg[weaponClass] = {
        total_count: aggCounts[weapon_id].total_count,
        weapons: [weapon_id],
      };
    }
  }

  const totalWeaponCount = Object.values(aggCounts).reduce(
    (acc, val) => acc + val.total_count,
    0
  );

  // Determine which classes are "Other"
  let otherCount = 0;
  const otherClasses = [];
  const innerSeriesData = [];
  for (const weaponClass in classAgg) {
    const classPercentage =
      (classAgg[weaponClass].total_count / totalWeaponCount) * 100;
    if (classPercentage < percentageThreshold) {
      otherClasses.push(...classAgg[weaponClass].weapons);
      otherCount += classAgg[weaponClass].total_count;
    } else {
      innerSeriesData.push({
        name: weaponClass,
        y: (classAgg[weaponClass].total_count / totalWeaponCount) * 100,
        drilldown: weaponClass,
      });
    }
  }

  // Add "Other" category
  innerSeriesData.push({
    name: "Other",
    y: (otherCount / totalWeaponCount) * 100,
    drilldown: "Other",
  });

  // Prepare outer series data and drilldown data
  const outerSeriesData = [];
  const drilldownData = [];
  for (const weaponClass in classAgg) {
    if (!otherClasses.includes(weaponClass)) {
      const classData = classAgg[weaponClass].weapons.map((weapon_id) => ({
        name: weapon_id,
        y: (aggCounts[weapon_id].total_count / totalWeaponCount) * 100,
      }));
      outerSeriesData.push(...classData);
      drilldownData.push({
        id: weaponClass,
        name: weaponClass,
        data: classData,
      });
    }
  }

  // Drilldown data for "Other"
  const otherDrilldownData = otherClasses.map((weapon_id) => ({
    name: weapon_id,
    y: (aggCounts[weapon_id].total_count / totalWeaponCount) * 100,
  }));
  drilldownData.push({ id: "Other", name: "Other", data: otherDrilldownData });

  return {
    innerSeriesData,
    outerSeriesData,
    drilldownData,
  };
}

export { processGroupedData, calculateTotalPercentage, computeDrilldown };
