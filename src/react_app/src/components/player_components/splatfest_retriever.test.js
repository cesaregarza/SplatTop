import { fetchFestivalDates } from "./splatfest_retriever";

const makeJsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: jest.fn().mockResolvedValue(data),
});

describe("fetchFestivalDates", () => {
  afterEach(() => {
    localStorage.clear();
    delete global.fetch;
  });

  it("uses the weekly local cache when it is still fresh", async () => {
    const today = new Date().toDateString();
    localStorage.setItem(
      "festivalDates",
      JSON.stringify({
        date: today,
        dates: JSON.stringify([["2024-01-01T00:00:00Z", "2024-01-03T00:00:00Z"]]),
      })
    );
    global.fetch = jest.fn();

    const dates = await fetchFestivalDates();

    expect(dates).toEqual([
      [new Date("2024-01-01T00:00:00Z"), new Date("2024-01-03T00:00:00Z")],
    ]);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("fetches festival dates and caches them when no local cache exists", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse({
        US: {
          data: {
            festRecords: {
              nodes: [
                {
                  startTime: "2024-02-01T00:00:00Z",
                  endTime: "2024-02-03T00:00:00Z",
                },
              ],
            },
          },
        },
      })
    );

    const dates = await fetchFestivalDates();

    expect(global.fetch).toHaveBeenCalledWith(
      "https://splatoon3.ink/data/festivals.json",
      {}
    );
    expect(dates).toEqual([
      [new Date("2024-02-01T00:00:00Z"), new Date("2024-02-03T00:00:00Z")],
    ]);

    const cachedData = JSON.parse(localStorage.getItem("festivalDates"));
    expect(cachedData).toBeTruthy();
    expect(JSON.parse(cachedData.dates)).toEqual([
      ["2024-02-01T00:00:00.000Z", "2024-02-03T00:00:00.000Z"],
    ]);
  });
});
