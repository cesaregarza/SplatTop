import { mergeCompetitionSnapshotRows } from "./competitionSnapshotUtils";

describe("mergeCompetitionSnapshotRows", () => {
  it("merges danger metadata and keeps fresh deltas", () => {
    const rows = mergeCompetitionSnapshotRows({
      stable: {
        generated_at_ms: 1_700_000_000_000,
        deltas: {
          baseline_generated_at_ms: 1_699_900_000_000,
          newcomers: ["p2"],
          players: {
            p1: {
              rank_delta: 2,
              display_score_delta: 6.5,
              previous_rank: 4,
              previous_display_score: 210,
            },
            p2: {
              rank_delta: 0,
              score_delta: 0.2,
              is_new: true,
            },
          },
        },
        data: [
          {
            player_id: "p1",
            last_tournament_ms: 1_699_999_000_000,
            window_tournament_count: 4,
          },
          {
            player_id: "p2",
            last_tournament_ms: 1_699_999_500_000,
          },
        ],
      },
      danger: {
        data: [
          {
            player_id: "p1",
            days_left: 5,
            next_expiry_ms: 1_700_010_000_000,
            oldest_in_window_ms: 1_699_500_000_000,
            window_tournament_count: 5,
          },
        ],
      },
    });

    expect(rows).toEqual([
      expect.objectContaining({
        player_id: "p1",
        danger_days_left: 5,
        danger_next_expiry_ms: 1_700_010_000_000,
        danger_oldest_in_window_ms: 1_699_500_000_000,
        window_tournament_count: 5,
        rank_delta: 2,
        display_score_delta: 6.5,
        delta_has_baseline: true,
        delta_is_new: false,
        delta_previous_rank: 4,
        delta_previous_display_score: 210,
      }),
      expect.objectContaining({
        player_id: "p2",
        danger_days_left: null,
        window_tournament_count: null,
        rank_delta: 0,
        display_score_delta: 5,
        delta_has_baseline: true,
        delta_is_new: true,
      }),
    ]);
  });

  it("drops stale display-score deltas when the player has been inactive for more than a day", () => {
    const [row] = mergeCompetitionSnapshotRows({
      stable: {
        generated_at_ms: 1_700_000_000_000,
        deltas: {
          baseline_generated_at_ms: 1_699_900_000_000,
          players: {
            p1: {
              display_score_delta: 3.25,
            },
          },
        },
        data: [
          {
            player_id: "p1",
            last_tournament_ms: 1_699_800_000_000,
          },
        ],
      },
      danger: { data: [] },
    });

    expect(row.display_score_delta).toBeNull();
    expect(row.delta_has_baseline).toBe(true);
  });
});
