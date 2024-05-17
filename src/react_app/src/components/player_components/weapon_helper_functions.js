import chroma from "chroma-js";

const weaponColors = {
  Blaster: {
    colorType: "dark",
    color: [30, 45, 26],
  },
  Roller: {
    colorType: "light",
    color: [70, 30, 52],
  },
  Shooter: {
    colorType: "light",
    color: [70, 0, 50],
  },
  Maneuver: {
    colorType: "dark",
    color: [30, -45, 26],
  },
  Stringer: {
    colorType: "light",
    color: [70, -30, 52],
  },
  Shelter: {
    colorType: "light",
    color: [70, -30, -52],
  },
  Saber: {
    colorType: "dark",
    color: [30, -45, -26],
  },
  Brush: {
    colorType: "light",
    color: [70, -60, 0],
  },
  Charger: {
    colorType: "dark",
    color: [30, 0, -52],
  },
  Spinner: {
    colorType: "light",
    color: [70, 60, 0],
  },
  Slosher: {
    colorType: "dark",
    color: [30, 45, -26],
  },
  Other: {
    colorType: "light",
    color: [70, 30, -52],
  },
};

function adjustBrightnessByRank(labColor, rank, delta, maxRank, invert) {
  const [l, a, b] = labColor;
  const clampedRank = Math.min(Math.max(rank, 0), maxRank);
  const newL = l + (invert ? -1 : 1) * clampedRank * delta;
  return chroma.lab(newL, a, b).hex();
}

function getImageFromId(weaponId, weaponReferenceData) {
  const baseCDNUrl = "https://splat-top.nyc3.cdn.digitaloceanspaces.com/";
  const weaponData = weaponReferenceData[weaponId];
  const name = `${weaponData.class}_${weaponData.kit}`;
  if (weaponData) {
    return `${baseCDNUrl}assets/weapon_flat/Path_Wst_${name}.png`;
  }
  return `${baseCDNUrl}assets/weapon_flat/Dummy.png`;
}

function createTranslator(weaponReferenceData, weaponTranslations) {
  const translateWeaponId = (weapon_id) => {
    const weaponClass = weaponReferenceData[weapon_id]?.class;
    const kit = weaponReferenceData[weapon_id]?.reference_kit;
    const translationKey = `${weaponClass}_${kit}`;
    return weaponTranslations[`WeaponName_Main`][translationKey];
  };

  const translateClassName = (className) => {
    if (className === "Other") {
      return className;
    }
    return weaponTranslations["WeaponTypeName"][className];
  };

  return {
    translateWeaponId,
    translateClassName,
  };
}

function computeDrilldown(
  counts,
  percentageThreshold,
  weaponReferenceData,
  weaponTranslations,
  otherString
) {
  const aggCounts = {};
  const classAgg = {};
  const weaponToClassMap = {};
  const maxRank = 5;
  const deltaL = 8;

  const translator = createTranslator(weaponReferenceData, weaponTranslations);
  const translateWeaponId = translator.translateWeaponId;
  const translateClassName = translator.translateClassName;

  const translatedWeaponColors = {};
  for (const weaponClass in weaponColors) {
    const entry = weaponColors[weaponClass];
    const color = chroma.lab(entry.color);
    translatedWeaponColors[translateClassName(weaponClass, otherString)] = {
      colorType: entry.colorType,
      color: color,
    };
  }

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
      weaponReferenceData[originalWeaponId]?.class, otherString
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
        weaponToClassMap[weapon] = otherString;
      });
    } else {
      innerSeriesData.push({
        name: weaponClass,
        y: (classAgg[weaponClass].total_count / totalWeaponCount) * 100,
        drilldown: weaponClass,
        color: translatedWeaponColors[weaponClass].color.hex(),
      });
    }
  }

  // Add "Other" category to inner series data
  innerSeriesData.push({
    name: otherString,
    y: (otherCount / totalWeaponCount) * 100,
    drilldown: otherString,
    color: translatedWeaponColors["Other"].color.hex(),
  });

  // Sort inner series data by prevalence (descending order)
  innerSeriesData.sort((a, b) => b.y - a.y);

  // Prepare outer series data and drilldown data
  const preOuterSeriesData = [];
  const drilldownData = [];
  for (const weaponClass in classAgg) {
    const classData = classAgg[weaponClass].weapons.map((weapon_id) => {
      const weaponPercentage =
        (aggCounts[weapon_id].total_count / totalWeaponCount) * 100;
      return {
        name: weapon_id,
        y: weaponPercentage,
      };
    });
    preOuterSeriesData.push(...classData);
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

  // Sort outer series data first by the rank in inner series data, then by y (descending order)
  preOuterSeriesData.sort((a, b) => {
    const classAIndex = classRanking[weaponToClassMap[a.name]];
    const classBIndex = classRanking[weaponToClassMap[b.name]];
    if (classAIndex !== classBIndex) {
      return classAIndex - classBIndex;
    }
    return b.y - a.y;
  });

  // Create a mapping of weaponClass to its start index in outerSeriesData
  const classStartIndices = innerSeriesData.reduce((acc, item, index) => {
    for (let i = 0; i < preOuterSeriesData.length; i++) {
      const weapon = preOuterSeriesData[i];
      if (weaponToClassMap[weapon.name] === item.name) {
        acc[item.name] = i;
        break;
      }
    }
    return acc;
  }, {});
  translatedWeaponColors[otherString] = translatedWeaponColors["Other"];

  // Adjust brightness of colors based on weapon index
  const outerSeriesData = [];
  preOuterSeriesData.forEach((item, index) => {
    const entry = translatedWeaponColors[weaponToClassMap[item.name]];

    const newColor = adjustBrightnessByRank(
      entry.color.lab(),
      index - classStartIndices[weaponToClassMap[item.name]],
      deltaL,
      maxRank,
      entry.colorType === "dark"
    );
    outerSeriesData.push({
      name: item.name,
      y: item.y,
      color: newColor,
      classColor: entry.color.hex(),
    });
  });

  // Drilldown data for "Other" category
  const otherDrilldownData = otherClasses.map((weapon_id) => {
    const weaponPercentage =
      (aggCounts[weapon_id].total_count / totalWeaponCount) * 100;
    return {
      name: weapon_id,
      y: weaponPercentage,
      color: translatedWeaponColors["Other"].color.hex(),
    };
  });
  drilldownData.push({ id: otherString, name: otherString, data: otherDrilldownData });

  return {
    innerSeriesData,
    outerSeriesData,
    drilldownData,
  };
}

export { getImageFromId, createTranslator, computeDrilldown };
