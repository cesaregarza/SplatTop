import React, { act } from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import CompetitionPlayerPage from "./CompetitionPlayerPage";
import useCompetitionPlayer from "../../hooks/useCompetitionPlayer";

jest.mock("../../hooks/useCompetitionPlayer");
jest.mock("../../hooks/useCrackleEffect", () => jest.fn());

const mockedUseCompetitionPlayer = useCompetitionPlayer;

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
  ...overrides,
});

const renderPage = (profile) => {
  mockedUseCompetitionPlayer.mockReturnValue({
    loading: false,
    error: null,
    profile,
    refresh: jest.fn(),
  });

  return render(
    <MemoryRouter initialEntries={["/u/p1"]}>
      <Routes>
        <Route
          path="/u/:playerId"
          element={<CompetitionPlayerPage top500Href="/" />}
        />
      </Routes>
    </MemoryRouter>
  );
};

describe("CompetitionPlayerPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("supports filtering and pagination in the history explorer", () => {
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

    expect(screen.getByText("Ranked history explorer")).toBeInTheDocument();
    expect(screen.getByText("Cup 14")).toBeInTheDocument();
    expect(screen.queryByText("Cup 1")).not.toBeInTheDocument();
    expect(screen.getByText("Showing page 1 of 2")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Search tournaments or teams"),
      { target: { value: "Cup 3" } }
    );

    expect(screen.getByText("Cup 3")).toBeInTheDocument();
    expect(screen.queryByText("Cup 14")).not.toBeInTheDocument();
    expect(screen.getByText("Showing page 1 of 1")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Search tournaments or teams"),
      { target: { value: "" } }
    );
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Cup 1")).toBeInTheDocument();
    expect(screen.getByText("Showing page 2 of 2")).toBeInTheDocument();
  });

  it("copies profile snapshot text", async () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    renderPage(makeProfile({ display_score: 101.2 }));

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "Copy profile snapshot" })
      );
    });

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(1);
    });
    expect(writeText.mock.calls[0][0]).toContain("Rank score: 251.20 / 250");
    await screen.findByText("Profile snapshot text copied.");
  });

  it("targets the next grade threshold in the path tracker", () => {
    renderPage(makeProfile({ display_score: -10 }));

    expect(screen.getByText("Path to XS-")).toBeInTheDocument();
    expect(screen.getByText("140.00 / 150.00")).toBeInTheDocument();
  });

  it("uses the XX+ threshold for path to XX+", () => {
    renderPage(makeProfile({ display_score: 90 }));

    expect(screen.getByText("Path to XX+")).toBeInTheDocument();
    expect(screen.getByText("240.00 / 250.00")).toBeInTheDocument();
  });
});
