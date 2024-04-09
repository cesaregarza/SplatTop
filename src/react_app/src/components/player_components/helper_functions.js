const getSeasonStartDate = (season) => {
  const yearOffset = Math.floor((season - 1) / 4);
  const monthIndex = (season - 1) % 4;
  const monthMap = [11, 2, 5, 8]; // December, March, June, September
  const year = monthIndex === 0 ? 2023 + yearOffset - 1 : 2023 + yearOffset;
  return new Date(Date.UTC(year, monthMap[monthIndex], 1));
};

// Helper function to get the season end date
const getSeasonEndDate = (season) => {
  const nextSeasonStart = getSeasonStartDate(season + 1);
  return new Date(
    Date.UTC(
      nextSeasonStart.getUTCFullYear(),
      nextSeasonStart.getUTCMonth(),
      nextSeasonStart.getUTCDate(),
      0,
      0,
      0,
      nextSeasonStart.getUTCMilliseconds() - 1000
    )
  );
};

// Helper function to convert timestamp to percentage in season
const getPercentageInSeason = (timestamp, season) => {
  const seasonStart = getSeasonStartDate(season);
  const seasonEnd = getSeasonEndDate(season);
  const totalDuration = seasonEnd - seasonStart;
  const elapsedDuration = new Date(timestamp) - seasonStart;
  return (elapsedDuration / totalDuration) * 100;
};

export { getSeasonStartDate, getSeasonEndDate, getPercentageInSeason };