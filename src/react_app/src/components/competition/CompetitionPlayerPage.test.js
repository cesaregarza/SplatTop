import React, { act } from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  CompetitionPlayerPageContent,
} from "./CompetitionPlayerPage";

jest.mock("../../hooks/useCrackleEffect", () => jest.fn());

const makeProfile = (overrides = {}) => ({
  player_id: "p1",
  display_name: "Player One",
  eligible: true,
  minimum_required_tournaments: 3,
  lifetime_ranked_tournaments: 12,
  window_tournament_count: 4,
  progress_to_minimum: { current: 3, required: 3, remaining: 0 },
  stable_rank: 7,
  display_score: 80,
  danger_days_left: 6,
  last_tournament_ms: 1_700_000_000_000,
  generated_at_ms: 1_700_000_010_000,
  delta_has_baseline: true,
  delta_is_new: false,
  rank_delta: 1,
  display_score_delta: 2.5,
  history_generated_at_ms: 1_700_000_010_000,
  history_record_count: 0,
  tournament_history_ranked: [],
  match_loo_generated_at_ms: 1_700_000_010_000,
  match_loo_record_count: 0,
  match_loo_max_records: 20,
  match_loo_impacts: [],
  ...overrides,
});

const renderPage = (profile, overrides = {}) => {
  return render(
    <MemoryRouter>
      <CompetitionPlayerPageContent
        error={null}
        loading={false}
        playerId="p1"
        profile={profile}
        refresh={jest.fn()}
        top500Href="/"
        {...overrides}
      />
    </MemoryRouter>
  );
};

describe("CompetitionPlayerPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the dense profile layout instead of the old dashboard sections", () => {
    const openSpy = jest.spyOn(window, "open").mockImplementation(() => null);
    const historyRows = [
      {
        tournament_id: 44,
        tournament_name: "Midnight Splat",
        event_ms: 1_700_000_000_000,
        ranked: true,
        team_name: "Luma",
        result_summary: "4W-1L",
      },
      {
        tournament_id: 45,
        tournament_name: "Dawn Cup",
        event_ms: 1_699_000_000_000,
        ranked: true,
        team_name: "Luma",
        result_summary: "2W-3L",
      },
    ];

    renderPage(
      makeProfile({
        previous_display_score: 77.5,
        history_record_count: historyRows.length,
        tournament_history_ranked: historyRows,
      })
    );

    expect(screen.queryByRole("heading", { name: "At a glance" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Recent activity" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tablist", { name: "Profile data views" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share" })).toBeInTheDocument();
    expect(screen.getByText("Win rate")).toBeInTheDocument();
    expect(screen.getAllByText("Midnight Splat").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Luma").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Profile data" })).not.toBeInTheDocument();
    expect(screen.queryByText("Snapshot briefing")).not.toBeInTheDocument();
    expect(screen.queryByText("Recent stretch")).not.toBeInTheDocument();
    expect(screen.queryByText("Competition pulse")).not.toBeInTheDocument();
    expect(screen.queryByText("Recent form")).not.toBeInTheDocument();
    expect(screen.queryByText("Share profile")).not.toBeInTheDocument();
    expect(
      screen.queryByText("One snapshot line for standing, activity, and archive footprint.")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Dense views for strongest results and ranked history.")
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Snapshot:/)).not.toBeInTheDocument();
    expect(screen.queryByText("90d activity")).not.toBeInTheDocument();
    expect(screen.queryByText("Primary team")).not.toBeInTheDocument();
    expect(screen.queryByText("Archive span")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByText("Midnight Splat")[0].closest("tr"));

    expect(openSpy).toHaveBeenCalledWith(
      "https://sendou.ink/to/44",
      "_blank",
      "noopener,noreferrer"
    );

    openSpy.mockRestore();
  });

  it("supports filtering and pagination in the history explorer", () => {
    const openSpy = jest.spyOn(window, "open").mockImplementation(() => null);
    const historyRows = Array.from({ length: 14 }, (_, idx) => ({
      tournament_id: idx + 1,
      tournament_name: `Cup ${idx + 1}`,
      event_ms: 1_700_000_000_000 + idx,
      ranked: true,
      team_name: `Team ${idx + 1}`,
      result_summary: `${idx % 4}W-${(idx + 1) % 3}L`,
    }));

    renderPage(
      makeProfile({
        history_record_count: historyRows.length,
        tournament_history_ranked: historyRows,
      })
    );

    fireEvent.click(screen.getByRole("tab", { name: "History explorer" }));

    const historyPanel = screen
      .getByRole("tablist", { name: "Profile data views" })
      .closest("section");

    expect(within(historyPanel).getByText("Cup 14")).toBeInTheDocument();
    expect(within(historyPanel).queryByText("Cup 1")).not.toBeInTheDocument();
    expect(screen.getByText("Showing page 1 of 2")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Search tournaments or teams"),
      { target: { value: "Cup 3" } }
    );

    expect(within(historyPanel).getByText("Cup 3")).toBeInTheDocument();
    expect(within(historyPanel).queryByText("Cup 14")).not.toBeInTheDocument();
    expect(screen.getByText("Showing page 1 of 1")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Search tournaments or teams"),
      { target: { value: "" } }
    );
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(within(historyPanel).getByText("Cup 1")).toBeInTheDocument();
    expect(screen.getByText("Showing page 2 of 2")).toBeInTheDocument();

    fireEvent.click(within(historyPanel).getByText("Cup 1").closest("tr"));

    expect(openSpy).toHaveBeenCalledWith(
      "https://sendou.ink/to/1",
      "_blank",
      "noopener,noreferrer"
    );

    openSpy.mockRestore();
  });

  it("shows the full archive without pagination when admin history is unbounded", () => {
    const historyRows = Array.from({ length: 14 }, (_, idx) => ({
      tournament_id: idx + 1,
      tournament_name: `Cup ${idx + 1}`,
      event_ms: 1_700_000_000_000 + idx,
      ranked: true,
      team_name: `Team ${idx + 1}`,
      result_summary: `${idx % 4}W-${(idx + 1) % 3}L`,
    }));

    renderPage(
      makeProfile({
        history_record_count: historyRows.length,
        history_max_records: null,
        tournament_history_ranked: historyRows,
      })
    );

    fireEvent.click(screen.getByRole("tab", { name: "History explorer" }));

    const historyPanel = screen
      .getByRole("tablist", { name: "Profile data views" })
      .closest("section");

    expect(within(historyPanel).getByText("Cup 14")).toBeInTheDocument();
    expect(within(historyPanel).getByText("Cup 1")).toBeInTheDocument();
    expect(
      screen.getByText("Showing all 14 matching tournaments")
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Showing page \d+ of \d+/)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Next" })
    ).not.toBeInTheDocument();
  });

  it("shows only the history explorer when strongest results are not visible", () => {
    renderPage(
      makeProfile({
        history_record_count: 2,
        tournament_history_ranked: [
          {
            tournament_id: 44,
            tournament_name: "Midnight Splat",
            event_ms: 1_700_000_000_000,
            ranked: true,
            team_name: "Luma",
            result_summary: "4W-1L",
          },
          {
            tournament_id: 45,
            tournament_name: "Dawn Cup",
            event_ms: 1_699_000_000_000,
            ranked: true,
            team_name: "Luma",
            result_summary: "2W-3L",
          },
        ],
        match_loo_record_count: undefined,
        match_loo_impacts: undefined,
      })
    );

    expect(
      screen.queryByRole("tab", { name: "Strongest results" })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "History explorer" })
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByText("Midnight Splat").length).toBeGreaterThan(0);
  });

  it("falls back to history when strongest results disappear after a refresh", () => {
    const historyRows = [
      {
        tournament_id: 44,
        tournament_name: "Midnight Splat",
        event_ms: 1_700_000_000_000,
        ranked: true,
        team_name: "Luma",
        result_summary: "4W-1L",
      },
    ];

    const view = renderPage(
      makeProfile({
        history_record_count: historyRows.length,
        tournament_history_ranked: historyRows,
        match_loo_record_count: 1,
        match_loo_impacts: [
          {
            match_id: 501,
            tournament_id: 44,
            tournament_name: "Midnight Splat",
            event_ms: 1_700_000_000_000,
            player_rank: 7,
            player_score: 5.1,
            is_win: false,
            exact_score_delta: 0.42,
            exact_abs_delta: 0.42,
            player_team_name: "Luma",
            opponent_team_name: "Nova",
            player_team_score: 1,
            opponent_team_score: 3,
            player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
            opponent_team_players: ["Ember", "Flint", "Glint", "Halo"],
          },
        ],
      })
    );

    expect(
      screen.getByRole("tab", { name: "Strongest results" })
    ).toHaveAttribute("aria-selected", "true");

    view.rerender(
      <MemoryRouter>
        <CompetitionPlayerPageContent
          error={null}
          loading={false}
          playerId="p1"
          profile={makeProfile({
            history_record_count: historyRows.length,
            tournament_history_ranked: historyRows,
            match_loo_record_count: undefined,
            match_loo_impacts: undefined,
          })}
          refresh={jest.fn()}
          top500Href="/"
        />
      </MemoryRouter>
    );

    expect(
      screen.queryByRole("tab", { name: "Strongest results" })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "History explorer" })
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByText("Midnight Splat").length).toBeGreaterThan(0);
  });

  it("copies the profile link", async () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    renderPage(makeProfile({ display_score: 101.2 }));

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Share" }));
    });

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(1);
    });
    expect(writeText.mock.calls[0][0]).toBe("http://localhost/u/p1");
    await screen.findByText("Profile link copied.");
  });

  it("targets the next grade threshold in the path tracker", () => {
    renderPage(makeProfile({ display_score: -10 }));

    const path = screen.getByLabelText("Path to XS-");
    const scoreStat = path.closest(".comp-player-header-stat");

    expect(path).toBeInTheDocument();
    expect(scoreStat).toHaveTextContent("140.00 / 150");
  });

  it("uses the XX+ threshold for path to XX+", () => {
    renderPage(makeProfile({ display_score: 90 }));

    const path = screen.getByLabelText("Path to XX+");
    const scoreStat = path.closest(".comp-player-header-stat");

    expect(path).toBeInTheDocument();
    expect(scoreStat).toHaveTextContent("240.00 / 250");
  });

  it("shows admin-visible rank and score before the public unlock threshold", () => {
    renderPage(
      makeProfile({
        eligible: false,
        ineligible_reason: "insufficient_lifetime_tournaments",
        lifetime_ranked_tournaments: 1,
        progress_to_minimum: { current: 1, required: 3, remaining: 2 },
        stable_rank: 21,
        display_score: 43.75,
      })
    );

    const scoreStat = screen
      .getByText("Score")
      .closest(".comp-player-header-stat");

    expect(screen.getByText("#21")).toBeInTheDocument();
    expect(scoreStat).toHaveTextContent("193.75");
    expect(screen.queryByText("Locked")).not.toBeInTheDocument();
    expect(
      screen.getByText(
        "Public profile keeps rank and score locked until 2 more lifetime ranked tournaments."
      )
    ).toBeInTheDocument();
  });

  it("defaults to most harmful when helpful rows are empty", () => {
    renderPage(
      makeProfile({
        match_loo_record_count: 2,
        match_loo_impacts: [
          {
            match_id: 601,
            tournament_id: 71,
            tournament_name: "Hazard Cup",
            event_ms: 1_700_000_000_000,
            is_win: false,
            exact_score_delta: 0.42,
            exact_abs_delta: 0.42,
            player_team_name: "Luma",
            opponent_team_name: "Nova",
            player_team_score: 1,
            opponent_team_score: 3,
            player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
            opponent_team_players: ["Ember", "Flint", "Glint", "Halo"],
          },
          {
            match_id: 602,
            tournament_id: 72,
            tournament_name: "Risk Open",
            event_ms: 1_699_000_000_000,
            is_win: false,
            exact_score_delta: 0.18,
            exact_abs_delta: 0.18,
            player_team_name: "Luma",
            opponent_team_name: "Orbit",
            player_team_score: 2,
            opponent_team_score: 3,
            player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
            opponent_team_players: ["Mica", "Nova", "Onyx", "Pyre"],
          },
        ],
      })
    );

    expect(
      screen.getByRole("button", { name: "Most harmful" })
    ).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: "Most helpful" })
    ).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("Hazard Cup")).toBeInTheDocument();
  });

  it("defaults to biggest swings when only neutral rows exist", () => {
    renderPage(
      makeProfile({
        match_loo_record_count: 1,
        match_loo_impacts: [
          {
            match_id: 701,
            tournament_id: 81,
            tournament_name: "Even Split",
            event_ms: 1_700_000_000_000,
            is_win: true,
            exact_score_delta: 0,
            exact_abs_delta: 0.27,
            player_team_name: "Luma",
            opponent_team_name: "Nova",
            player_team_score: 3,
            opponent_team_score: 2,
            player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
            opponent_team_players: ["Ember", "Flint", "Glint", "Halo"],
          },
        ],
      })
    );

    expect(
      screen.getByRole("button", { name: "Biggest swings" })
    ).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: "Most helpful" })
    ).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("Even Split")).toBeInTheDocument();
  });

  it("renders expandable strongest results rows and opens sendou links", () => {
    const openSpy = jest.spyOn(window, "open").mockImplementation(() => null);

    renderPage(
      makeProfile({
        display_name: "Aster",
        match_loo_record_count: 3,
        match_loo_impacts: [
          {
            match_id: 501,
            tournament_id: 44,
            tournament_name: "Midnight Splat",
            event_ms: 1_700_000_000_000,
            player_rank: 7,
            player_score: 5.1,
            is_win: false,
            exact_score_delta: 0.42,
            exact_abs_delta: 0.42,
            player_team_name: "Luma",
            opponent_team_name: "Nova",
            player_team_score: 1,
            opponent_team_score: 3,
            player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
            opponent_team_players: ["Ember", "Flint", "Glint", "Halo"],
          },
          {
            match_id: 502,
            tournament_id: 45,
            tournament_name: "Dawn Cup",
            event_ms: 1_699_500_000_000,
            player_rank: 7,
            player_score: 5.1,
            is_win: true,
            exact_score_delta: -0.33,
            exact_abs_delta: 0.33,
            player_team_name: "Luma",
            opponent_team_name: "Mistral",
            player_team_score: 3,
            opponent_team_score: 2,
            player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
            opponent_team_players: ["Iris", "Jade", "Kite", "Lumen"],
          },
          {
            match_id: 503,
            tournament_id: 46,
            tournament_name: "Twilight Clash",
            event_ms: 1_699_000_000_000,
            player_rank: 7,
            player_score: 5.1,
            is_win: false,
            exact_score_delta: 0.18,
            exact_abs_delta: 0.18,
            player_team_name: "Luma",
            opponent_team_name: "Orbit",
            player_team_score: 2,
            opponent_team_score: 3,
            player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
            opponent_team_players: ["Mica", "Nova", "Onyx", "Pyre"],
          },
        ],
      })
    );

    const resultsTab = screen.getByRole("tab", {
      name: "Strongest results",
    });
    const helpfulButton = screen.getByRole("button", {
      name: "Most helpful",
    });
    const harmfulButton = screen.getByRole("button", {
      name: "Most harmful",
    });

    expect(resultsTab).toHaveAttribute("aria-selected", "true");
    expect(helpfulButton).toHaveAttribute("aria-pressed", "true");
    expect(harmfulButton).toHaveAttribute("aria-pressed", "false");
    expect(
      screen.getByRole("button", { name: "Biggest swings" })
    ).toBeInTheDocument();
    expect(screen.getByText(/Results updated /)).toBeInTheDocument();
    expect(screen.getByText("Dawn Cup")).toBeInTheDocument();
    expect(screen.getByText("Luma vs Mistral")).toBeInTheDocument();
    expect(screen.getByText("3-2")).toBeInTheDocument();
    expect(screen.getAllByText("+8.25").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Show lineups" }));

    expect(screen.getByText("Luma:")).toBeInTheDocument();
    expect(screen.getByText("Mistral:")).toBeInTheDocument();
    expect(screen.getAllByText("Aster", { selector: "strong" }).length).toBe(1);
    expect(screen.getByText("Beryl")).toBeInTheDocument();

    fireEvent.click(harmfulButton);

    expect(harmfulButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Midnight Splat")).toBeInTheDocument();
    expect(screen.getByText("Luma vs Nova")).toBeInTheDocument();
    expect(screen.getByText("1-3")).toBeInTheDocument();
    expect(screen.getAllByText("-10.50").length).toBeGreaterThan(0);
    expect(screen.queryByText(/Removal effect/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Magnitude/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Snapshot #/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Match 501/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Tournament 44/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Showing page/)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name:
          /Technical note: leave-one-out shortlist from this ranking run/i,
      })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByText("Midnight Splat"));

    expect(openSpy).toHaveBeenCalledWith(
      "https://sendou.ink/to/44/matches/501",
      "_blank",
      "noopener,noreferrer"
    );

    openSpy.mockRestore();
  });

  it("switches between strongest results and history tabs", () => {
    const helpfulRows = Array.from({ length: 5 }, (_, index) => ({
      match_id: 700 + index,
      tournament_id: 80 + index,
      tournament_name: `Helpful ${index + 1}`,
      event_ms: 1_700_000_000_000 - index,
      player_rank: 7,
      player_score: 5.1,
      is_win: true,
      exact_score_delta: -0.1 * (index + 1),
      exact_abs_delta: 0.1 * (index + 1),
      player_team_name: "Luma",
      opponent_team_name: "Nova",
      player_team_score: 3,
      opponent_team_score: 2,
      player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
      opponent_team_players: ["Ember", "Flint", "Glint", "Halo"],
    }));
    const harmfulRows = Array.from({ length: 5 }, (_, index) => ({
      match_id: 800 + index,
      tournament_id: 90 + index,
      tournament_name: `Harmful ${index + 1}`,
      event_ms: 1_699_000_000_000 - index,
      player_rank: 7,
      player_score: 5.1,
      is_win: false,
      exact_score_delta: 0.1 * (index + 1),
      exact_abs_delta: 0.1 * (index + 1),
      player_team_name: "Luma",
      opponent_team_name: "Orbit",
      player_team_score: 2,
      opponent_team_score: 3,
      player_team_players: ["Aster", "Beryl", "Cinder", "Drift"],
      opponent_team_players: ["Mica", "Nova", "Onyx", "Pyre"],
    }));

    renderPage(
      makeProfile({
        display_name: "Aster",
        match_loo_record_count: 10,
        match_loo_impacts: [...helpfulRows, ...harmfulRows],
        tournament_history_ranked: [
          {
            tournament_id: 999,
            tournament_name: "Archive Cup",
            event_ms: 1_700_000_000_000,
            ranked: true,
            team_name: "Archive Team",
            result_summary: "4W-1L",
          },
        ],
      })
    );

    const resultsTab = screen.getByRole("tab", {
      name: "Strongest results",
    });
    const historyTab = screen.getByRole("tab", {
      name: "History explorer",
    });
    const helpfulButton = screen.getByRole("button", {
      name: "Most helpful",
    });
    const harmfulButton = screen.getByRole("button", {
      name: "Most harmful",
    });
    const swingsButton = screen.getByRole("button", {
      name: "Biggest swings",
    });

    expect(resultsTab).toHaveAttribute("aria-selected", "true");
    expect(helpfulButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Helpful 5")).toBeInTheDocument();
    expect(screen.queryByText("Harmful 5")).not.toBeInTheDocument();

    fireEvent.click(harmfulButton);

    expect(harmfulButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Harmful 5")).toBeInTheDocument();
    expect(screen.queryByText("Helpful 5")).not.toBeInTheDocument();

    fireEvent.click(swingsButton);

    expect(swingsButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Helpful 5")).toBeInTheDocument();
    expect(screen.getByText("Harmful 5")).toBeInTheDocument();
    expect(screen.queryByText(/Showing page/)).not.toBeInTheDocument();

    fireEvent.click(historyTab);

    expect(historyTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByText("Archive Cup").length).toBeGreaterThan(0);
    expect(
      screen.getByPlaceholderText("Search tournaments or teams")
    ).toBeInTheDocument();

    fireEvent.click(resultsTab);

    expect(resultsTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Helpful 5")).toBeInTheDocument();
  });
});
