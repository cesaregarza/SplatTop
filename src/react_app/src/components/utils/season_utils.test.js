import {
  calculateSeasonByTimestamp,
  getPercentageInSeason,
  getSeasonEndDate,
  getSeasonName,
  getSeasonStartDate,
} from "./season_utils";

describe("season_utils", () => {
  it("computes season start dates", () => {
    const season1 = getSeasonStartDate(1);
    expect(season1.getUTCFullYear()).toBe(2022);
    expect(season1.getUTCMonth()).toBe(11);
    expect(season1.getUTCDate()).toBe(1);

    const season2 = getSeasonStartDate(2);
    expect(season2.getUTCFullYear()).toBe(2023);
    expect(season2.getUTCMonth()).toBe(2);
    expect(season2.getUTCDate()).toBe(1);
  });

  it("computes season end dates", () => {
    const endSeason1 = getSeasonEndDate(1);
    expect(endSeason1.getUTCFullYear()).toBe(2023);
    expect(endSeason1.getUTCMonth()).toBe(1);
    expect(endSeason1.getUTCDate()).toBe(28);
    expect(endSeason1.getUTCHours()).toBe(23);
    expect(endSeason1.getUTCMinutes()).toBe(59);
    expect(endSeason1.getUTCSeconds()).toBe(59);
  });

  it("calculates season progress percentage", () => {
    const seasonStart = getSeasonStartDate(1);
    expect(getPercentageInSeason(seasonStart, 1)).toBe(0);
  });

  it("calculates season numbers from timestamps", () => {
    expect(calculateSeasonByTimestamp("2022-12-01T00:00:00Z")).toBe(1);
    expect(calculateSeasonByTimestamp("2023-03-01T00:00:00Z")).toBe(2);
  });

  it("formats season names with translations", () => {
    const t = (key) =>
      ({
        spring: "Spring",
        summer: "Summer",
        autumn: "Autumn",
        winter: "Winter",
        format_short: "%SEASON% %YEAR%",
      }[key]);

    expect(getSeasonName(2, t)).toBe("Spring 2023");
  });
});
