import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import LZString from "lz-string";
import useFetchWithCache from "./fetch_with_cache";
import { setCache } from "../utils/cache_utils";

const TestComponent = ({ endpoint }) => {
  const { data, error, isLoading } = useFetchWithCache(endpoint);

  return (
    <div>
      <div>loading:{isLoading ? "yes" : "no"}</div>
      <div>data:{data ? JSON.stringify(data) : "none"}</div>
      <div>error:{error ? error.message : "none"}</div>
    </div>
  );
};

const makeJsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: jest.fn().mockResolvedValue(data),
});

describe("useFetchWithCache", () => {
  const endpoint = "/api/top500";
  const originalVersion = process.env.REACT_APP_VERSION;
  let consoleErrorSpy;

  beforeEach(() => {
    process.env.REACT_APP_VERSION = "test-version";
    localStorage.clear();
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    process.env.REACT_APP_VERSION = originalVersion;
    localStorage.clear();
    delete global.fetch;
    consoleErrorSpy.mockRestore();
    jest.useRealTimers();
  });

  it("uses fresh cached data without fetching again", async () => {
    const cachedPayload = { rows: ["cached"] };
    const compressedData = LZString.compressToUTF16(
      JSON.stringify({ data: cachedPayload, timestamp: Date.now() })
    );

    setCache("endpoints", { [endpoint]: compressedData }, 60);
    global.fetch = jest.fn();

    render(<TestComponent endpoint={endpoint} />);

    await waitFor(() => {
      expect(screen.getByText('data:{"rows":["cached"]}')).toBeInTheDocument();
      expect(screen.getByText("loading:no")).toBeInTheDocument();
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("fetches and caches data when the endpoint is missing from local cache", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse({ rows: ["fresh"] })
    );

    render(<TestComponent endpoint={endpoint} />);

    await waitFor(() => {
      expect(screen.getByText('data:{"rows":["fresh"]}')).toBeInTheDocument();
      expect(screen.getByText("error:none")).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith(endpoint, {});

    const cache = JSON.parse(localStorage.getItem("endpoints"));
    expect(cache).toHaveProperty(endpoint);
  });

  it("does not fetch when the endpoint is empty", async () => {
    global.fetch = jest.fn();

    render(<TestComponent endpoint={null} />);

    await waitFor(() => {
      expect(screen.getByText("loading:no")).toBeInTheDocument();
      expect(screen.getByText("data:none")).toBeInTheDocument();
      expect(screen.getByText("error:none")).toBeInTheDocument();
    });

    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("retries failed fetches with exponential backoff", async () => {
    jest.useFakeTimers();
    global.fetch = jest.fn()
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce(makeJsonResponse({ rows: ["retry"] }));

    render(<TestComponent endpoint={endpoint} />);

    await waitFor(() => {
      expect(screen.getByText("error:boom")).toBeInTheDocument();
    });
    expect(global.fetch).toHaveBeenCalledTimes(1);

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(screen.getByText('data:{"rows":["retry"]}')).toBeInTheDocument();
      expect(screen.getByText("error:none")).toBeInTheDocument();
    });
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});
