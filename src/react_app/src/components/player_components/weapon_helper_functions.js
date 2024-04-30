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

function computeDrilldown(
  counts,
  percentageThreshold,
  weaponReferenceData,
  weaponTranslations
) {
  const aggCounts = {};
  const classAgg = {};
  console.log("weaponReferenceData", weaponReferenceData);

  const translateWeaponId = (weapon_id) => {
    const weaponClass = weaponReferenceData[weapon_id]?.class;
    const kit = weaponReferenceData[weapon_id]?.reference_kit;
    const translationKey = `${weaponClass}_${kit}`;
    return weaponTranslations[`WeaponName_Main`][translationKey];
  };

  const translateClassName = (className) => {
    return weaponTranslations["WeaponTypeName"][className];
  };

  // Aggregate counts by translated weapon ID
  for (const row of counts) {
    const translatedWeaponId = translateWeaponId(row.weapon_id);
    if (translatedWeaponId in aggCounts) {
      aggCounts[translatedWeaponId].total_count += row.total_count;
      aggCounts[translatedWeaponId].win_count += row.sum;
    } else {
      aggCounts[translatedWeaponId] = {
        total_count: row.total_count,
        win_count: row.sum,
      };
    }
  }

  // Aggregate counts by class using original weapon ID for class determination
  for (const translatedWeaponId in aggCounts) {
    const originalWeaponId = Object.keys(weaponReferenceData).find(
      (id) => translateWeaponId(id) === translatedWeaponId
    );
    const weaponClass = translateClassName(
      weaponReferenceData[originalWeaponId]?.class
    );

    if (weaponClass in classAgg) {
      classAgg[weaponClass].total_count +=
        aggCounts[translatedWeaponId].total_count;
      classAgg[weaponClass].weapons.push(translatedWeaponId);
    } else {
      classAgg[weaponClass] = {
        total_count: aggCounts[translatedWeaponId].total_count,
        weapons: [translatedWeaponId],
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
