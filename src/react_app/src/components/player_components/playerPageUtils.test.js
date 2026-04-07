import {
  countDiamondSeasons,
  getDefaultPlayerMode,
  getDefaultSeasonResultTab,
  getPlayerSummary,
} from "./playerPageUtils";

describe("playerPageUtils", () => {
  it("defaults the selected mode to the first mode that has data", () => {
    const playerData = [
      { mode: "Rainmaker" },
      { mode: "Clam Blitz" },
    ];

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
