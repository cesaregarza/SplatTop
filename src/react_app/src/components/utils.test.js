import {
  buildEndpointWithQueryParams,
  getBaseApiUrl,
  getBaseWebsocketUrl,
} from "./utils";

describe("components/utils", () => {
  const originalEnv = process.env.NODE_ENV;

  afterEach(() => {
    process.env.NODE_ENV = originalEnv;
  });

  it("returns the API base URL for development", () => {
    process.env.NODE_ENV = "development";
    expect(getBaseApiUrl()).toBe("http://localhost:5000");
  });

  it("returns empty API base URL for production", () => {
    process.env.NODE_ENV = "production";
    expect(getBaseApiUrl()).toBe("");
  });

  it("builds websocket URLs based on environment and protocol", () => {
    process.env.NODE_ENV = "development";
    expect(getBaseWebsocketUrl()).toBe("ws://localhost:5000");

    process.env.NODE_ENV = "production";
    expect(getBaseWebsocketUrl()).toBe(`ws://${window.location.host}`);
  });

  it("builds endpoints with query params for absolute and relative bases", () => {
    const absolute = buildEndpointWithQueryParams(
      "http://api.example.com",
      "/path",
      { a: "1", b: "two" }
    );
    expect(absolute).toBe("http://api.example.com/path?a=1&b=two");

    const relative = buildEndpointWithQueryParams("/api", "/ping", { q: "test" });
    expect(relative).toBe("/api/ping?q=test");
  });
});
