import React from "react";
import { act, render, screen } from "@testing-library/react";
import {
  RouterProvider,
  createMemoryRouter,
} from "react-router-dom";

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
    global.fetch = jest.fn().mockResolvedValue(
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
      error: "Player not found in competition index",
      profile: null,
    });
  });

  it("scrolls to the top when a player page opens and when the route changes", async () => {
    global.fetch = jest.fn()
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
});
