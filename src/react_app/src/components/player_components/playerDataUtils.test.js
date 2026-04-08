import {
  createEmptyPlayerDetailData,
  isLegacyPlayerDetailPayload,
  isPlayerChunkEnvelope,
  mergePlayerDetailPayload,
} from "./playerDataUtils";

describe("playerDataUtils", () => {
  it("creates an empty canonical player-detail payload", () => {
    expect(createEmptyPlayerDetailData()).toEqual({
      player_data: [],
      aggregated_data: {
        weapon_counts: [],
        weapon_winrate: [],
        season_results: [],
        aggregate_season_data: [],
        latest_data: [],
      },
    });
  });

  it("merges progressive snapshot and analysis payloads into one canonical object", () => {
    const snapshotPayload = {
      aggregated_data: {
        season_results: [{ season_number: 6, mode: "Rainmaker", rank: 4 }],
        latest_data: [{ season_number: 5, mode: "Rainmaker", rank: 5 }],
      },
    };
    const analysisPayload = {
      player_data: [{ mode: "Rainmaker", season_number: 5, x_power: 2801.1 }],
      aggregated_data: {
        aggregate_season_data: [
          { season_number: 5, mode: "Rainmaker", peak_x_power: 2801.1 },
        ],
        weapon_counts: [{ mode: "Rainmaker", season_number: 5, count: 10 }],
      },
    };

    const mergedSnapshot = mergePlayerDetailPayload(
      createEmptyPlayerDetailData(),
      snapshotPayload
    );
    const mergedAnalysis = mergePlayerDetailPayload(
      mergedSnapshot,
      analysisPayload
    );

    expect(mergedAnalysis).toEqual({
      player_data: [
        { mode: "Rainmaker", season_number: 5, x_power: 2801.1 },
      ],
      aggregated_data: {
        season_results: [{ season_number: 6, mode: "Rainmaker", rank: 4 }],
        latest_data: [{ season_number: 5, mode: "Rainmaker", rank: 5 }],
        aggregate_season_data: [
          { season_number: 5, mode: "Rainmaker", peak_x_power: 2801.1 },
        ],
        weapon_counts: [{ mode: "Rainmaker", season_number: 5, count: 10 }],
        weapon_winrate: [],
      },
    });
  });

  it("detects progressive chunk envelopes and legacy full payloads", () => {
    expect(
      isPlayerChunkEnvelope({
        type: "player_chunk",
        version: 2,
        phase: "snapshot",
        payload: {},
      })
    ).toBe(true);

    expect(
      isLegacyPlayerDetailPayload({
        player_data: [],
        aggregated_data: {},
      })
    ).toBe(true);

    expect(
      isLegacyPlayerDetailPayload({
        type: "player_chunk",
        version: 2,
        phase: "snapshot",
      })
    ).toBe(false);
  });
});
