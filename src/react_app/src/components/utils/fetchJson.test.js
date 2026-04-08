import { fetchJson } from "./fetchJson";

const makeJsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: jest.fn().mockResolvedValue(data),
});

describe("fetchJson", () => {
  afterEach(() => {
    delete global.fetch;
  });

  it("returns parsed JSON for successful responses", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse({ ok: true })
    );

    await expect(fetchJson("/api/test")).resolves.toEqual({ ok: true });
    expect(global.fetch).toHaveBeenCalledWith("/api/test", {});
  });

  it("throws the response detail for non-ok JSON responses", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      makeJsonResponse({ detail: "Nope" }, 500)
    );

    await expect(fetchJson("/api/test")).rejects.toMatchObject({
      message: "Nope",
      status: 500,
      detail: "Nope",
    });
  });

  it("falls back to a status-based error message when JSON parsing fails", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: jest.fn().mockRejectedValue(new Error("bad json")),
    });

    await expect(fetchJson("/api/test")).rejects.toMatchObject({
      message: "Request failed with status 503",
      status: 503,
      detail: null,
    });
  });
});
