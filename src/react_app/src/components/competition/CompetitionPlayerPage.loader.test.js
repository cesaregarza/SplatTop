import React from "react";
import { act, render, screen } from "@testing-library/react";
import {
  RouterProvider,
  createMemoryRouter,
} from "react-router-dom";

import { CompetitionAuthProvider } from "./CompetitionAuth";
import CompetitionPlayerPage, {
  loadCompetitionPlayer,
} from "./CompetitionPlayerPage";

jest.mock("../../hooks/useCrackleEffect", () => jest.fn());

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, reject, resolve };
};

const makeJsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: jest.fn().mockResolvedValue(data),
  clone() {
    return {
      json: jest.fn().mockResolvedValue(data),
    };
  },
});

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

describe("CompetitionPlayerPage loader", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.scrollTo = jest.fn();
  });

  afterEach(() => {
    delete global.fetch;
  });

  it("returns backend error details for failed loads", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(
        makeJsonResponse(
          { detail: "Competition admin authentication is required" },
          401
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          { detail: "Player not found in competition index" },
          404
        )
      );

    const result = await loadCompetitionPlayer({
      params: { playerId: "missing" },
      request: new Request("http://localhost/u/missing"),
    });

    expect(result).toEqual({
      accessMode: "public",
      error: "Player not found in competition index",
      profile: null,
    });
  });

  it("falls back to the public player endpoint when admin auth is unavailable", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(
        makeJsonResponse(
          { detail: "Competition admin authentication is required" },
          401
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeProfile({
            player_id: "public-player",
            display_name: "Public Fallback Player",
            history_record_count: 1,
            tournament_history_ranked: [
              {
                tournament_id: 3288,
                tournament_name: "Champions Cup #9",
                event_ms: 1_774_206_180_000,
                ranked: true,
                result_summary: "0W-1L",
                team_name: "Example Team",
                team_id: 61392,
              },
            ],
          })
        )
      );

    const result = await loadCompetitionPlayer({
      params: { playerId: "public-player" },
      request: new Request("http://localhost/u/public-player"),
    });

    expect(result).toMatchObject({
      accessMode: "public",
      error: null,
    });
    expect(result.profile.display_name).toBe("Public Fallback Player");
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/api/ripple/admin/player/public-player"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/api/ripple/public/player/public-player"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("scrolls to the top when a player page opens and when the route changes", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(
        makeJsonResponse(
          { detail: "Competition admin authentication is required" },
          401
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeProfile({
            player_id: "a",
            display_name: "Player A",
          })
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          { detail: "Competition admin authentication is required" },
          401
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeProfile({
            player_id: "b",
            display_name: "Player B",
          })
        )
      );

    const router = createMemoryRouter(
      [
        {
          path: "/u/:playerId",
          loader: loadCompetitionPlayer,
          element: <CompetitionPlayerPage top500Href="/" />,
        },
      ],
      { initialEntries: ["/u/a"] }
    );

    render(<RouterProvider router={router} />);

    await screen.findByText("Player A");
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);

    await act(async () => {
      await router.navigate("/u/b");
    });

    await screen.findByText("Player B");
    expect(window.scrollTo).toHaveBeenCalledTimes(2);
    expect(window.scrollTo).toHaveBeenLastCalledWith(0, 0);
  });

  it("drops stale param navigations by aborting the older loader request", async () => {
    const firstRequest = deferred();
    const secondRequest = deferred();

    global.fetch = jest.fn((url, options = {}) => {
      const path = String(url);
      if (path.endsWith("/a")) {
        options.signal?.addEventListener(
          "abort",
          () => {
            const abortError = new Error("Aborted");
            abortError.name = "AbortError";
            firstRequest.reject(abortError);
          },
          { once: true }
        );
        return firstRequest.promise;
      }
      if (path.endsWith("/b")) {
        return secondRequest.promise;
      }
      throw new Error(`Unexpected loader url: ${path}`);
    });

    const router = createMemoryRouter(
      [
        {
          path: "/u/:playerId",
          loader: loadCompetitionPlayer,
          element: <CompetitionPlayerPage top500Href="/" />,
        },
      ],
      { initialEntries: ["/u/a"] }
    );

    render(<RouterProvider router={router} />);

    await act(async () => {
      router.navigate("/u/b");
      await Promise.resolve();
    });

    await act(async () => {
      secondRequest.resolve(
        makeJsonResponse(
          makeProfile({
            player_id: "b",
            display_name: "Player B",
          })
        )
      );
      await Promise.resolve();
    });

    await screen.findByText("Player B");
    expect(screen.queryByText("Player A")).not.toBeInTheDocument();
  });

  it("uses the admin player endpoint for admin sessions", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeProfile({
            player_id: "p1",
            display_name: "Admin Visible Player",
            stable_rank: 21,
            display_score: 193.75,
          })
        )
      );

    const result = await loadCompetitionPlayer({
      params: { playerId: "p1" },
      request: new Request("http://localhost/u/p1"),
    });

    expect(result.error).toBeNull();
    expect(result.profile.display_name).toBe("Admin Visible Player");
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/api/ripple/admin/player/p1"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("keeps rendering the admin player payload even when comp auth state fails closed", async () => {
    global.fetch = jest.fn((url) => {
      const path = String(url);

      if (path.includes("/api/comp-auth/me")) {
        return Promise.resolve(
          makeJsonResponse(
            { detail: "Competition auth origin is not allowed" },
            403
          )
        );
      }

      if (path.includes("/api/ripple/admin/player/p1")) {
        return Promise.resolve(
          makeJsonResponse(
            makeProfile({
              player_id: "p1",
              display_name: "Admin Visible Player",
              stable_rank: 21,
              display_score: 193.75,
            })
          )
        );
      }

      throw new Error(`Unexpected fetch url: ${path}`);
    });

    const router = createMemoryRouter(
      [
        {
          path: "/u/:playerId",
          loader: loadCompetitionPlayer,
          element: <CompetitionPlayerPage top500Href="/" />,
        },
      ],
      { initialEntries: ["/u/p1"] }
    );

    render(
      <CompetitionAuthProvider>
        <RouterProvider router={router} />
      </CompetitionAuthProvider>
    );

    await screen.findByText("Admin Visible Player");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ripple/admin/player/p1"),
      expect.objectContaining({ credentials: "include" })
    );
  });

});
