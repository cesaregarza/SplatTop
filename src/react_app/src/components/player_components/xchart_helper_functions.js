import {
  getPercentageInSeason,
  calculateSeasonNow,
  calculateSeasonByTimestamp,
  getSeasonName,
} from "../utils/season_utils";

const dataWithNulls = (data, threshold, festsForSeason) => {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    result.push(data[i]);
    if (i < data.length - 1 && data[i + 1].x - data[i].x >= threshold) {
      const midPointX = (data[i + 1].x + data[i].x) / 2;
      let isWithinFestival = false;
      for (const fest of festsForSeason) {
        if (midPointX >= fest.start && midPointX <= fest.end) {
          isWithinFestival = true;
          break;
        }
      }
      if (!isWithinFestival) {
        result.push({ x: midPointX, y: null });
      }
    }
  }
  return result;
};

function filterAndProcessData(
  data,
  mode,
  removeValuesNotInTop500,
  festivalDates
) {
  const hoursThreshold = 24 * 1;
  const approxThreshold = (hoursThreshold / (24 * 90)) * 100;
  const filteredData = data ? data.filter((d) => d.mode === mode) : [];

  const seasons = filteredData.reduce((acc, curr) => {
    const season = curr.season_number;
    if (!acc.includes(season)) acc.push(season);
    return acc;
  }, []);

  const currentSeason = calculateSeasonNow();
  if (!festivalDates) {
    festivalDates = [];
  }

  const festivalDatesPercent = festivalDates.map((dateRange) => {
    const startDate = dateRange[0];
    const season = calculateSeasonByTimestamp(startDate);
    return {
      season: season,
      start: getPercentageInSeason(startDate, season),
      end: getPercentageInSeason(dateRange[1], season),
    };
  });

  const dataBySeason = filteredData.reduce((acc, curr) => {
    const season = curr.season_number;
    acc[season] = acc[season] || [];
    acc[season].push({
      x: getPercentageInSeason(curr.timestamp, season),
      y: curr.x_power,
      updated: curr.updated,
    });
    return acc;
  }, {});

  const sortedSeasons = seasons.sort((a, b) =>
    a === currentSeason ? 1 : b === currentSeason ? -1 : b - a
  );

  const processedData = sortedSeasons.map((season) => {
    const sortedValues = dataBySeason[season].sort((a, b) => a.x - b.x);
    const threshold = removeValuesNotInTop500 ? approxThreshold : 100;
    const festsForSeason = festivalDatesPercent.filter(
      (fest) => fest.season === season
    );
    const sortedValuesWithNulls = dataWithNulls(
      sortedValues,
      threshold,
      festsForSeason
    );

    return {
      season,
      dataPoints: sortedValuesWithNulls,
      isCurrent: season === currentSeason,
    };
  });
  return {
    currentSeason,
    processedData: processedData.sort((a, b) => a.season - b.season),
  };
}

const getSeasonColor = (season_number, isCurrent) => {
  const saturation = 100;
  const baseLightness = 25;
  const lightnessStep = 10;
  const season_offset = season_number + 2;
  const season_index = season_offset % 4;
  const year_offset = Math.floor(season_offset / 4);
  const hues = [140, 55, 30, 200]; // Green, Yellow, Orange, Cerulean
  const currentSeasonLightnessBoost = isCurrent ? 15 : 0;
  const lightness =
    baseLightness + year_offset * lightnessStep + currentSeasonLightnessBoost;
  const alpha = isCurrent ? 1 : 0.6;
  return `hsla(${hues[season_index]}, ${saturation}%, ${lightness}%, ${alpha})`;
};

const getClassicColor = (season_number, isCurrent, numSeasons) => {
  if (isCurrent) {
    return "#ab5ab7";
  }
  const minBrightness = 25;
  const maxBrightness = 60;
  const brightnessStep = (maxBrightness - minBrightness) / numSeasons;
  const brightness = minBrightness + season_number * brightnessStep;
  return `hsla(292, 50%, ${brightness}%, 0.6)`;
};

const getAccessibleColor = (season_number) => {
  const colors = ["#117733", "#DDCC77", "#AA4499", "#332288"];
  return colors[season_number % colors.length];
};

const getDefaultWidth = (isCurrent) => {
  return isCurrent ? 5 : 2;
};

const getAccessibleWidth = (seasonNumber) => {
  const currentWidth = 5;
  const minWidth = 1;
  const maxWidth = 3;
  const numSeasons = calculateSeasonNow();
  const widthStep = (maxWidth - minWidth) / numSeasons;
  const width = minWidth + seasonNumber * widthStep;
  return seasonNumber === numSeasons ? currentWidth : width;
};

const getAvailableModes = (data) => {
  const modes = ["Splat Zones", "Tower Control", "Rainmaker", "Clam Blitz"];
  return modes.map((mode) => data.some((item) => item.mode === mode));
};

export {
  dataWithNulls,
  filterAndProcessData,
  getSeasonName,
  getSeasonColor,
  getClassicColor,
  getAccessibleColor,
  getDefaultWidth,
  getAccessibleWidth,
  getAvailableModes,
};
