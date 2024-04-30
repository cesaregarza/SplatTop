function computeDrilldown(
  counts,
  percentageThreshold,
  weaponReferenceData,
  weaponTranslations
) {
  const aggCounts = {};
  const classAgg = {};
  const weaponToClassMap = {};

  // Helper function to translate weapon IDs using the provided translation data
  const translateWeaponId = (weapon_id) => {
    const weaponClass = weaponReferenceData[weapon_id]?.class;
    const kit = weaponReferenceData[weapon_id]?.reference_kit;
    const translationKey = `${weaponClass}_${kit}`;
    return weaponTranslations[`WeaponName_Main`][translationKey];
  };

  // Helper function to translate class names using the provided translation
  //data
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
    weaponToClassMap[translatedWeaponId] = weaponClass;

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

  // Determine which classes are "Other" based on the percentage threshold
  let otherCount = 0;
  const otherClasses = [];
  const innerSeriesData = [];
  for (const weaponClass in classAgg) {
    const classPercentage =
      (classAgg[weaponClass].total_count / totalWeaponCount) * 100;
    if (classPercentage < percentageThreshold) {
      otherClasses.push(...classAgg[weaponClass].weapons);
      otherCount += classAgg[weaponClass].total_count;
      classAgg[weaponClass].weapons.forEach((weapon) => {
        weaponToClassMap[weapon] = "Other";
      });
    } else {
      innerSeriesData.push({
        name: weaponClass,
        y: (classAgg[weaponClass].total_count / totalWeaponCount) * 100,
        drilldown: weaponClass,
      });
    }
  }

  // Add "Other" category to inner series data
  innerSeriesData.push({
    name: "Other",
    y: (otherCount / totalWeaponCount) * 100,
    drilldown: "Other",
  });

  // Sort inner series data by prevalence (descending order)
  innerSeriesData.sort((a, b) => b.y - a.y);

  // Prepare outer series data and drilldown data
  const outerSeriesData = [];
  const drilldownData = [];
  for (const weaponClass in classAgg) {
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

  // Create a mapping of weaponClass to its index in innerSeriesData for sorting
  const classRanking = innerSeriesData.reduce((acc, item, index) => {
    acc[item.name] = index;
    return acc;
  }, {});

  // Sort outer series data first by the rank in inner series data, then by y
  //(descending order)
  outerSeriesData.sort((a, b) => {
    const classAIndex = classRanking[weaponToClassMap[a.name]];
    const classBIndex = classRanking[weaponToClassMap[b.name]];
    if (classAIndex !== classBIndex) {
      return classAIndex - classBIndex;
    }
    return b.y - a.y;
  });

  // Drilldown data for "Other" category
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

export { computeDrilldown };
