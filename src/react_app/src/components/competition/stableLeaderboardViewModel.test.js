import {
  buildStableLeaderboardRowView,
  getVisibleStableLeaderboardGrades,
  prepareStableLeaderboardRows,
} from "./stableLeaderboardViewModel";

describe("stableLeaderboardViewModel", () => {
  it("prepares filtered, paginated leaderboard rows with derived grades", () => {
    const prepared = prepareStableLeaderboardRows({
      rows: [
        {
          player_id: "alpha",
          display_name: "Alpha",
          stable_rank: 2,
          display_score: 80,
          window_tournament_count: 4,
        },
        {
          player_id: "beta",
          display_name: "Beta",
          stable_rank: 1,
          display_score: -10,
          window_tournament_count: 3,
        },
      ],
      query: "a",
      page: 1,
      pageSize: 1,
      gradeFilter: "",
      showcaseRows: [],
    });

    expect(prepared.total).toBe(2);
    expect(prepared.pageCount).toBe(2);
    expect(prepared.filtered).toHaveLength(1);
    expect(prepared.filtered[0]).toEqual(
      expect.objectContaining({
        player_id: "beta",
        _grade: "XA+",
      })
    );
    expect(getVisibleStableLeaderboardGrades(prepared.availableGrades)).toEqual([
      "XX",
      "XA+",
    ]);
  });

  it("builds row-view metadata for ranking deltas and inactivity status", () => {
    const view = buildStableLeaderboardRowView(
      {
        player_id: "alpha",
        stable_rank: 4,
        display_name: "Alpha",
        _grade: "XX★",
        _shifted: 305,
        tournament_count: 22,
        window_tournament_count: 3,
        danger_days_left: 0.6,
        delta_has_baseline: true,
        delta_is_new: false,
        rank_delta: 2,
        display_score_delta: -5.5,
      },
      "alpha"
    );

    expect(view).toEqual(
      expect.objectContaining({
        rank: 4,
        grade: "XX★",
        rankScoreDisplay: "305.00",
        daysLabel: "<1d",
        rankChangeLabel: "+2",
        scoreChangeLabel: "-5.50",
        highlightClass: "ring-2 ring-fuchsia-500/40 ring-offset-0",
      })
    );
  });
});
