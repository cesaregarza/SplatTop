import { act, renderHook, waitFor } from "@testing-library/react";
import axios from "axios";

import useCompetitionPlayer from "./useCompetitionPlayer";

jest.mock("axios");

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

describe("useCompetitionPlayer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("ignores stale success responses after playerId changes", async () => {
    const firstRequest = deferred();
    const secondRequest = deferred();

    axios.get.mockImplementation((url) => {
      if (url.endsWith("/a")) return firstRequest.promise;
      if (url.endsWith("/b")) return secondRequest.promise;
      throw new Error(`Unexpected url: ${url}`);
    });

    const { result, rerender } = renderHook(
      ({ playerId }) => useCompetitionPlayer(playerId),
      { initialProps: { playerId: "a" } }
    );

    rerender({ playerId: "b" });

    await act(async () => {
      secondRequest.resolve({
        data: { player_id: "b", display_name: "Player B" },
      });
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.profile?.player_id).toBe("b");
    });

    await act(async () => {
      firstRequest.resolve({
        data: { player_id: "a", display_name: "Player A" },
      });
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.profile?.player_id).toBe("b");
  });

  it("ignores stale errors after a newer profile succeeds", async () => {
    const firstRequest = deferred();
    const secondRequest = deferred();

    axios.get.mockImplementation((url) => {
      if (url.endsWith("/a")) return firstRequest.promise;
      if (url.endsWith("/b")) return secondRequest.promise;
      throw new Error(`Unexpected url: ${url}`);
    });

    const { result, rerender } = renderHook(
      ({ playerId }) => useCompetitionPlayer(playerId),
      { initialProps: { playerId: "a" } }
    );

    rerender({ playerId: "b" });

    await act(async () => {
      secondRequest.resolve({
        data: { player_id: "b", display_name: "Player B" },
      });
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.profile?.player_id).toBe("b");
    });

    await act(async () => {
      firstRequest.reject({
        response: { data: { detail: "Player A not found" } },
      });
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.profile?.player_id).toBe("b");
  });
});
