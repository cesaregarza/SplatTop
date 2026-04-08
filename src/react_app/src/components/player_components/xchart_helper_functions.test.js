import {
  getHistoricalRangeBandData,
  getVisibleSeasonMax,
} from "./xchart_helper_functions";

describe("xchart helper functions", () => {
  it("builds a historical range band from prior seasons through the visible window", () => {
    const processedData = [
      {
        season: 7,
        dataPoints: [
          { x: 0, y: 2400 },
          { x: 50, y: 2600 },
          { x: 100, y: 2500 },
        ],
      },
      {
        season: 8,
        dataPoints: [
          { x: 0, y: 2500 },
          { x: 50, y: 2700 },
          { x: 100, y: 2800 },
        ],
      },
      {
        season: 9,
        dataPoints: [
          { x: 0, y: 2550 },
          { x: 20, y: 2650 },
        ],
      },
    ];

    expect(getHistoricalRangeBandData(processedData, 9, 20, 10)).toEqual([
      [0, 2400, 2500],
      [10, 2440, 2540],
      [20, 2480, 2580],
    ]);
  });

  it("always uses the full season range for the main chart", () => {
    expect(getVisibleSeasonMax(true, 32.4)).toBe(100);
    expect(getVisibleSeasonMax(false, 32.4)).toBe(100);
  });
});
