import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import CompetitionApp from "./CompetitionApp";
import { loadCompetitionSnapshot } from "./competitionSnapshotApi";
import useCompetitionSnapshot from "../../hooks/useCompetitionSnapshot";

jest.mock("../../hooks/useCompetitionSnapshot");

jest.mock("../utils", () => ({
  getBaseApiUrl: jest.fn(() => ""),
}));

jest.mock("./StableLeaderboardView", () => ({
  __esModule: true,
  default: ({ rows, loading, error }) => (
    <div>
      <div>rows:{rows.length}</div>
      <div>loading:{loading ? "yes" : "no"}</div>
      {error && <div>error:{error}</div>}
    </div>
  ),
}));

jest.mock("./CompetitionFaq", () => ({
  __esModule: true,
  default: ({ percentiles }) => (
    <div>faq-count:{percentiles?.score_population?.count ?? 0}</div>
  ),
}));

jest.mock("./CompetitionViz", () => ({
  __esModule: true,
  default: () => <div>viz</div>,
}));

jest.mock("./CompetitionErrorBoundary", () => ({
  __esModule: true,
  default: ({ children }) => children,
}));

jest.mock("./CompetitionAuth", () => ({
  useCompetitionAuth: () => ({
    available: false,
    authenticated: false,
    isAdmin: false,
    discordId: null,
    error: null,
    loading: false,
    logout: jest.fn(),
    logoutPending: false,
  }),
}));

import { getBaseApiUrl } from "../utils";

const makeJsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: jest.fn().mockResolvedValue(data),
});

const makeStablePayload = (overrides = {}) => ({
  generated_at_ms: 1_700_000_010_000,
  query_params: { tournament_window_days: 120 },
  deltas: null,
  data: [
    {
      player_id: "p1",
      display_name: "Player One",
      stable_rank: 1,
      display_score: 235.11,
      score: 3.4044,
      last_tournament_ms: 1_700_000_000_000,
      window_tournament_count: 13,
    },
  ],
  ...overrides,
});

const makeDangerPayload = (overrides = {}) => ({
  generated_at_ms: 1_700_000_010_000,
  data: [
    {
      player_id: "p1",
      days_left: 5,
      window_tournament_count: 13,
    },
  ],
  ...overrides,
});

const makePercentilesPayload = (overrides = {}) => ({
  score_population: { count: 250 },
  ...overrides,
});

const makeSnapshot = (overrides = {}) => ({
  loading: false,
  error: null,
  disabled: false,
  stable: makeStablePayload(),
  danger: makeDangerPayload(),
  meta: { build_version: "v1" },
  percentiles: makePercentilesPayload(),
  refresh: jest.fn(),
  ...overrides,
});

const renderCompetitionApp = (entry, snapshot) => {
  window.history.pushState({}, "", entry);
  useCompetitionSnapshot.mockReturnValue(snapshot);
  return render(<CompetitionApp />);
};

describe("CompetitionApp snapshot loader", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getBaseApiUrl.mockReturnValue("");
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    delete global.fetch;
  });

  it("returns a disabled snapshot state when the public leaderboard is unavailable", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse(
        { detail: "Competition snapshot unavailable" },
        404
      )
    );

    const result = await loadCompetitionSnapshot({
      request: new Request("http://localhost/"),
    });

    expect(result).toEqual({
      disabled: true,
      error: null,
      stable: null,
      danger: null,
      meta: null,
      percentiles: null,
    });
  });

  it("renders leaderboard rows and refreshes the current snapshot", async () => {
    const refresh = jest.fn().mockResolvedValue(undefined);
    renderCompetitionApp("/", makeSnapshot({ refresh }));

    await screen.findByText("rows:1");

    fireEvent.click(screen.getByRole("button", { name: /refresh snapshot/i }));

    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  });

  it("renders faq content from loader data", async () => {
    renderCompetitionApp(
      "/faq",
      makeSnapshot({
        percentiles: makePercentilesPayload({
          score_population: { count: 512 },
        }),
      })
    );

    await screen.findByText("faq-count:512");
  });

  it("renders the leaderboard error state without throwing a route error", async () => {
    renderCompetitionApp(
      "/",
      makeSnapshot({
        error: "Snapshot fetch failed",
        stable: null,
        danger: null,
      })
    );

    await screen.findByText(/^Snapshot fetch failed$/);
    expect(screen.getByText("rows:0")).toBeInTheDocument();
  });

  it("uses the configured API base URL for snapshot fetches", async () => {
    getBaseApiUrl.mockReturnValue("http://localhost:5000");
    global.fetch = jest.fn()
      .mockResolvedValueOnce(makeJsonResponse(makeStablePayload()))
      .mockResolvedValueOnce(makeJsonResponse(makeDangerPayload()))
      .mockResolvedValueOnce(makeJsonResponse({ build_version: "v1" }))
      .mockResolvedValueOnce(makeJsonResponse(makePercentilesPayload()));

    const request = new Request("http://localhost/");
    await loadCompetitionSnapshot({ request });

    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      "http://localhost:5000/api/ripple/public/leaderboard",
      expect.objectContaining({
        headers: { Accept: "application/json" },
        signal: request.signal,
      })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      "http://localhost:5000/api/ripple/public/leaderboard/danger",
      expect.objectContaining({
        headers: { Accept: "application/json" },
        signal: request.signal,
      })
    );
  });
});
