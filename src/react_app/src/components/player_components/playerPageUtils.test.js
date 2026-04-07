import {
  countDiamondSeasons,
  getCareerHighlights,
  getDefaultPlayerMode,
  getDefaultSeasonResultTab,
  getDefaultSelectedDisplaySeason,
  getModeAnalysisSummary,
  getPlayerSummary,
  getSeasonArchiveRows,
} from "./playerPageUtils";

describe("playerPageUtils", () => {
  it("defaults the selected mode to the first mode that has data", () => {
    const playerData = [{ mode: "Rainmaker" }, { mode: "Clam Blitz" }];

    expect(getDefaultPlayerMode(playerData)).toBe("Rainmaker");
  });

  it("defaults season results to the newest available season", () => {
    const aggregatedData = {
      season_results: [
        { season_number: 8, mode: "Splat Zones" },
        { season_number: 10, mode: "Rainmaker" },
      ],
      latest_data: [],
    };

    expect(getDefaultSeasonResultTab(aggregatedData)).toBe(10);
  });

  it("defaults the selected display season to the newest season for the selected mode", () => {
    const chartData = {
      player_data: [
        { mode: "Rainmaker", season_number: 5 },
        { mode: "Clam Blitz", season_number: 4 },
      ],
      aggregated_data: {
        season_results: [],
        latest_data: [],
        aggregate_season_data: [],
      },
    };

    expect(getDefaultSelectedDisplaySeason(chartData, "Rainmaker")).toBe(6);
  });

  it("derives the player summary from alias and chart payloads", () => {
    const aliasData = [
      {
        splashtag: "Earlier#1111",
        latest_updated_timestamp: "2024-01-01T00:00:00.000Z",
      },
      {
        splashtag: "Latest#2222",
        latest_updated_timestamp: "2024-03-01T00:00:00.000Z",
      },
    ];
    const chartData = {
      player_data: [{ mode: "Tower Control" }, { mode: "Rainmaker" }],
      aggregated_data: {
        season_results: [
          { season_number: 9, rank: 12, x_power: 2520.4 },
          { season_number: 10, rank: 3, x_power: 2641.2 },
        ],
        latest_data: [{ mode: "Rainmaker", rank: 6, x_power: 2715.5 }],
        aggregate_season_data: [
          { season_number: 9, peak_x_power: 2690.1 },
          { season_number: 10, peak_x_power: 2740.8 },
        ],
      },
    };

    expect(getPlayerSummary(aliasData, chartData)).toEqual(
      expect.objectContaining({
        currentAlias: "Latest#2222",
        lastSeen: "2024-03-01T00:00:00.000Z",
        aliasCount: 2,
        bestRank: 3,
        bestXp: 2740.8,
        activeModeCount: 2,
        diamondSeasonCount: 1,
      })
    );
  });

  it("builds compact career highlights from historical season results", () => {
    const chartData = {
      aggregated_data: {
        season_results: [
          { season_number: 8, mode: "Splat Zones", rank: 1, region: true },
          { season_number: 8, mode: "Tower Control", rank: 21, region: true },
          { season_number: 7, mode: "Rainmaker", rank: 430, region: false },
          { season_number: 6, mode: "Clam Blitz", rank: 12, region: false },
          { season_number: 6, mode: "Splat Zones", rank: 700, region: false },
        ],
      },
    };

    expect(getCareerHighlights(chartData)).toEqual(
      expect.objectContaining({
        totalTop10: 1,
        totalTop500: 4,
        diamondSeasonCount: 0,
        bestFinish: 1,
        bestMode: "Splat Zones",
        notableSeasons: [
          expect.objectContaining({
            season_number: 8,
            finishes: [
              expect.objectContaining({ mode: "Splat Zones", rank: 1 }),
              expect.objectContaining({ mode: "Tower Control", rank: 21 }),
            ],
          }),
          expect.objectContaining({
            season_number: 7,
            finishes: [expect.objectContaining({ mode: "Rainmaker", rank: 430 })],
          }),
          expect.objectContaining({
            season_number: 6,
            finishes: [expect.objectContaining({ mode: "Clam Blitz", rank: 12 })],
          }),
        ],
      })
    );
  });

  it("builds season archive rows using display-season numbering", () => {
    const chartData = {
      player_data: [
        {
          mode: "Rainmaker",
          season_number: 4,
          timestamp: "2024-09-01T00:00:00.000Z",
          x_power: 2500,
        },
        {
          mode: "Rainmaker",
          season_number: 4,
          timestamp: "2024-09-10T00:00:00.000Z",
          x_power: 2600,
        },
        {
          mode: "Rainmaker",
          season_number: 5,
          timestamp: "2024-12-05T00:00:00.000Z",
          x_power: 2700,
        },
      ],
      aggregated_data: {
        season_results: [
          { season_number: 5, mode: "Rainmaker", rank: 8, region: true },
        ],
        latest_data: [{ season_number: 5, mode: "Rainmaker", rank: 4, region: false }],
        aggregate_season_data: [
          { season_number: 4, mode: "Rainmaker", peak_x_power: 2620 },
          { season_number: 5, mode: "Rainmaker", peak_x_power: 2730 },
        ],
      },
    };

    expect(getSeasonArchiveRows(chartData, "Rainmaker")).toEqual([
      expect.objectContaining({
        season_number: 6,
        raw_season_number: 5,
        finishRank: 4,
        peakXp: 2730,
        sparklineValues: [2700],
        hasModeData: true,
      }),
      expect.objectContaining({
        season_number: 5,
        raw_season_number: 4,
        finishRank: 8,
        peakXp: 2620,
        sparklineValues: [2500, 2600],
        hasModeData: true,
      }),
    ]);
  });

  it("derives a sparse live-season analysis summary for the selected mode", () => {
    const RealDate = Date;
    try {
      global.Date = class extends RealDate {
        constructor(...args) {
          if (args.length === 0) {
            return new RealDate("2025-01-20T00:00:00.000Z");
          }
          return new RealDate(...args);
        }

        static now() {
          return new RealDate("2025-01-20T00:00:00.000Z").getTime();
        }

        static parse(value) {
          return RealDate.parse(value);
        }

        static UTC(...args) {
          return RealDate.UTC(...args);
        }
      };

      const chartData = {
        player_data: [
          {
            mode: "Rainmaker",
            season_number: 9,
            timestamp: "2024-12-01T00:00:00.000Z",
            x_power: 2720.2,
          },
          {
            mode: "Rainmaker",
            season_number: 9,
            timestamp: "2025-01-10T00:00:00.000Z",
            x_power: 2765.5,
          },
        ],
        aggregated_data: {
          season_results: [],
          latest_data: [
            {
              season_number: 9,
              mode: "Rainmaker",
              rank: 7,
              x_power: 2765.5,
            },
          ],
          aggregate_season_data: [
            {
              season_number: 9,
              mode: "Rainmaker",
              peak_x_power: 2780.1,
            },
          ],
        },
      };

      expect(getModeAnalysisSummary(chartData, "Rainmaker", 10)).toEqual(
        expect.objectContaining({
          currentXp: 2765.5,
          isCurrent: true,
          isSparse: true,
          peakXp: 2780.1,
          rank: 7,
          trackedUpdates: 2,
        })
      );
    } finally {
      global.Date = RealDate;
    }
  });

  it("counts only all-top-10 seasons as diamond seasons", () => {
    const seasonResults = [
      { season_number: 3, rank: 2 },
      { season_number: 3, rank: 7 },
      { season_number: 4, rank: 5 },
      { season_number: 4, rank: 11 },
    ];

    expect(countDiamondSeasons(seasonResults)).toBe(1);
  });
});
