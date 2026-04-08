import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import {
  RouterProvider,
  createMemoryRouter,
} from "react-router-dom";

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

jest.mock("./CompetitionPlayerPage", () => ({
  __esModule: true,
  default: () => <div>player</div>,
  loadCompetitionPlayer: jest.fn(),
}));

import {
  CompetitionFaqPage,
  CompetitionLeaderboardPage,
  CompetitionRouteShell,
  loadCompetitionSnapshot,
} from "./CompetitionApp";
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

const makeSnapshotRouter = (entry) => createMemoryRouter(
  [
    {
      loader: loadCompetitionSnapshot,
      element: <CompetitionRouteShell />,
      children: [
        { path: "/", element: <CompetitionLeaderboardPage /> },
        { path: "/faq", element: <CompetitionFaqPage /> },
      ],
    },
  ],
  { initialEntries: [entry] }
);

describe("CompetitionApp snapshot loader", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getBaseApiUrl.mockReturnValue("");
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

  it("renders leaderboard rows from loader data and refreshes via revalidation", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(makeJsonResponse(makeStablePayload()))
      .mockResolvedValueOnce(makeJsonResponse(makeDangerPayload()))
      .mockResolvedValueOnce(makeJsonResponse({ build_version: "v1" }))
      .mockResolvedValueOnce(makeJsonResponse(makePercentilesPayload()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeStablePayload({
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
              {
                player_id: "p2",
                display_name: "Player Two",
                stable_rank: 2,
                display_score: 229.0,
                score: 3.16,
                last_tournament_ms: 1_700_000_000_000,
                window_tournament_count: 12,
              },
            ],
          })
        )
      )
      .mockResolvedValueOnce(makeJsonResponse(makeDangerPayload({
        data: [
          {
            player_id: "p1",
            days_left: 5,
            window_tournament_count: 13,
          },
          {
            player_id: "p2",
            days_left: 11,
            window_tournament_count: 12,
          },
        ],
      })))
      .mockResolvedValueOnce(makeJsonResponse({ build_version: "v2" }))
      .mockResolvedValueOnce(makeJsonResponse(makePercentilesPayload()));

    const router = makeSnapshotRouter("/");
    render(<RouterProvider router={router} />);

    await screen.findByText("rows:1");

    fireEvent.click(screen.getByRole("button", { name: /refresh snapshot/i }));

    await screen.findByText("rows:2");
    expect(global.fetch).toHaveBeenCalledTimes(8);
  });

  it("renders faq content from loader data", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(makeJsonResponse(makeStablePayload()))
      .mockResolvedValueOnce(makeJsonResponse(makeDangerPayload()))
      .mockResolvedValueOnce(makeJsonResponse({ build_version: "v1" }))
      .mockResolvedValueOnce(
        makeJsonResponse(
          makePercentilesPayload({
            score_population: { count: 512 },
          })
        )
      );

    const router = makeSnapshotRouter("/faq");
    render(<RouterProvider router={router} />);

    await screen.findByText("faq-count:512");
  });

  it("renders the leaderboard error state without throwing a route error", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse(
        { detail: "Snapshot fetch failed" },
        500
      )
    );

    const router = makeSnapshotRouter("/");
    render(<RouterProvider router={router} />);

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
