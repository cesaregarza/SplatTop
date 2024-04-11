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

const calculateSeasonNow = () => {
  const now_utc = new Date();
  return calculateSeasonByTimestamp(now_utc);
};

const calculateSeasonByTimestamp = (timestamp) => {
  const timestamp_utc = new Date(timestamp);
  const timestamp_utc_month = (timestamp_utc.getUTCMonth() + 1) % 12;
  const timestamp_utc_year =
    timestamp_utc.getUTCFullYear() + (timestamp_utc_month === 0 ? 1 : 0);
  return (
    4 * (timestamp_utc_year - 2022) + Math.floor(timestamp_utc_month / 3) - 3
  );
};

const dataWithNulls = (data, threshold = 2) => {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    result.push(data[i]);
    if (i < data.length - 1 && data[i + 1].x - data[i].x >= threshold) {
      result.push({ x: (data[i + 1].x + data[i].x) / 2, y: null });
    }
  }
  return result;
};

export {
  getSeasonStartDate,
  getSeasonEndDate,
  getPercentageInSeason,
  calculateSeasonNow,
  dataWithNulls,
};
