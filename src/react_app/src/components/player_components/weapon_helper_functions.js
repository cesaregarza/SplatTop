const filterAndProcessWeapons = (data, mode) => {
  const filteredData = data
    ? data.filter((d) => d.mode === mode && d.updated === true)
    : [];

  const groupedByWeapon = filteredData.reduce((acc, item) => {
    const { weapon_id } = item;
    acc[weapon_id] = (acc[weapon_id] || 0) + 1;
    return acc;
  }, {});

  const totalCounts = filteredData.length;
  const groupedByPercent = Object.keys(groupedByWeapon).reduce((acc, key) => {
    const count = groupedByWeapon[key];
    const percentage = (count / totalCounts) * 100;
    acc[key] = percentage;
    return acc;
  }, {});

  return {
    counts: groupedByWeapon,
    percentage: groupedByPercent,
  };
};

const computeDrilldown = (counts, percentage, percentageThreshold) => {
  let otherIds = [];
  let otherCount = 0;
  let otherPercentage = 0;
  for (const key in percentage) {
    if (percentage[key] < percentageThreshold) {
      otherIds.push(key);
      otherCount += counts[key];
      otherPercentage += percentage[key];
    }
  }

  let drilldownPercent = [];
  for (const key in counts) {
    if (otherIds.includes(key)) {
      drilldownPercent.push({ name: key, y: percentage[key] });
    }
  }

  let seriesPercentage = [];
  for (const key in counts) {
    if (!otherIds.includes(key)) {
      seriesPercentage.push({ name: key, y: percentage[key] });
    }
  }
  seriesPercentage.push({
    name: "Other",
    y: otherPercentage,
    drilldown: "Other",
  });

  return {
    seriesPercentage,
    drilldownPercent,
    otherCount,
  };
};

export { filterAndProcessWeapons, computeDrilldown };
