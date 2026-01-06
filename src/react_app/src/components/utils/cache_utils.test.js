import { clearInvalidVersionCache, deleteCache, getCache, setCache } from "./cache_utils";

describe("cache_utils", () => {
  const originalVersion = process.env.REACT_APP_VERSION;

  beforeEach(() => {
    localStorage.clear();
    process.env.REACT_APP_VERSION = "1.0.0";
  });

  afterEach(() => {
    localStorage.clear();
    process.env.REACT_APP_VERSION = originalVersion;
  });

  it("stores and retrieves cached data with future expiration", () => {
    const payload = { a: 1 };
    setCache("key", payload, 60);

    expect(getCache("key")).toEqual(payload);
  });

  it("returns null for expired cache entries", () => {
    setCache("key", { a: 1 }, -1);

    expect(getCache("key")).toBeNull();
  });

  it("cleans up invalid JSON entries", () => {
    localStorage.setItem("bad", "{");
    localStorage.setItem(
      "badExpiration",
      new Date(Date.now() + 60 * 1000).toISOString()
    );
    localStorage.setItem("badVersion", "1.0.0");

    expect(getCache("bad")).toBeNull();
    expect(localStorage.getItem("bad")).toBeNull();
    expect(localStorage.getItem("badExpiration")).toBeNull();
    expect(localStorage.getItem("badVersion")).toBeNull();
  });

  it("clears entries with mismatched versions", () => {
    localStorage.setItem("key", JSON.stringify({ a: 1 }));
    localStorage.setItem(
      "keyExpiration",
      new Date(Date.now() + 60 * 1000).toISOString()
    );
    localStorage.setItem("keyVersion", "0.9.0");
    process.env.REACT_APP_VERSION = "2.0.0";

    expect(getCache("key")).toBeNull();
    expect(localStorage.getItem("key")).toBeNull();
    expect(localStorage.getItem("keyExpiration")).toBeNull();
    expect(localStorage.getItem("keyVersion")).toBeNull();
  });

  it("deletes cache entries explicitly", () => {
    setCache("key", { a: 1 }, 60);
    deleteCache("key");

    expect(getCache("key")).toBeNull();
  });

  it("clears invalid version keys directly", () => {
    localStorage.setItem("key", JSON.stringify({ a: 1 }));
    localStorage.setItem("keyExpiration", "2025-01-01T00:00:00.000Z");
    localStorage.setItem("keyVersion", "0.9.0");
    process.env.REACT_APP_VERSION = "2.0.0";

    clearInvalidVersionCache();

    expect(localStorage.getItem("key")).toBeNull();
    expect(localStorage.getItem("keyExpiration")).toBeNull();
    expect(localStorage.getItem("keyVersion")).toBeNull();
  });
});
