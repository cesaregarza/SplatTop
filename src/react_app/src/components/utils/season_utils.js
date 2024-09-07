const getSeasonStartDate = (season) => {
  const yearOffset = Math.floor((season - 1) / 4);
  const monthIndex = (season - 1) % 4;
  const monthMap = [11, 2, 5, 8]; // December, March, June, September
  const year = monthIndex === 0 ? 2023 + yearOffset - 1 : 2023 + yearOffset;
  return new Date(Date.UTC(year, monthMap[monthIndex], 1));
};

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

const getSeasonName = (season_number, t) => {
  const season_offset = season_number + 2;
  const season_index = season_offset % 4;
  const year = 2022 + Math.floor(season_offset / 4);
  const season_names = [t("spring"), t("summer"), t("autumn"), t("winter")];
  return t("format_short")
    .replace("%SEASON%", season_names[season_index])
    .replace("%YEAR%", year);
};

export {
  getSeasonStartDate,
  getSeasonEndDate,
  getPercentageInSeason,
  calculateSeasonNow,
  calculateSeasonByTimestamp,
  getSeasonName,
};
