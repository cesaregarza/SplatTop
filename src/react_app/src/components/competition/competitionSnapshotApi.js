import { getBaseApiUrl } from "../utils";

const STABLE_ENDPOINT = "/api/ripple/public/leaderboard";
const DANGER_ENDPOINT = "/api/ripple/public/leaderboard/danger";
const META_ENDPOINT = "/api/ripple/public/metadata";
const PERCENTILES_ENDPOINT = "/api/ripple/public/leaderboard/percentiles";
const ADMIN_REFRESH_ENDPOINT = "/api/ripple/admin/refresh";

export const normalizeCompetitionLoaderError = (error) => {
  if (!error) {
    return "Unknown error";
  }
  if (typeof error.detail === "string" && error.detail) {
    return error.detail;
  }
  return error.message || "Unexpected error";
};

const buildCompetitionSnapshotUrl = (path) => {
  const baseApiUrl = getBaseApiUrl();
  if (!baseApiUrl) {
    return path;
  }
  return new URL(path, baseApiUrl).href;
};

export const fetchCompetitionJson = async (url, signal) => {
  const response = await fetch(buildCompetitionSnapshotUrl(url), {
    headers: { Accept: "application/json" },
    signal,
  });
  let data = null;

  try {
    data = await response.json();
  } catch {}

  if (!response.ok) {
    const error = new Error(
      typeof data?.detail === "string" && data.detail
        ? data.detail
        : `Request failed with status ${response.status}`
    );
    error.status = response.status;
    error.detail = data?.detail ?? null;
    throw error;
  }

  return data;
};

export const queueCompetitionSnapshotRefresh = async ({ wait = false } = {}) => {
  const url = wait
    ? `${ADMIN_REFRESH_ENDPOINT}?wait=true`
    : ADMIN_REFRESH_ENDPOINT;
  const response = await fetch(buildCompetitionSnapshotUrl(url), {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  let data = null;
  try {
    data = await response.json();
  } catch {}

  if (!response.ok) {
    const error = new Error(
      typeof data?.detail === "string" && data.detail
        ? data.detail
        : `Request failed with status ${response.status}`
    );
    error.status = response.status;
    error.detail = data?.detail ?? null;
    throw error;
  }

  return data;
};

export const loadCompetitionSnapshot = async ({ request }) => {
  try {
    const [stable, danger, meta, percentiles] = await Promise.all([
      fetchCompetitionJson(STABLE_ENDPOINT, request.signal),
      fetchCompetitionJson(DANGER_ENDPOINT, request.signal),
      fetchCompetitionJson(META_ENDPOINT, request.signal),
      fetchCompetitionJson(PERCENTILES_ENDPOINT, request.signal),
    ]);

    return {
      disabled: false,
      error: null,
      stable,
      danger,
      meta,
      percentiles,
    };
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }

    if (error?.status === 404) {
      return {
        disabled: true,
        error: null,
        stable: null,
        danger: null,
        meta: null,
        percentiles: null,
      };
    }

    return {
      disabled: false,
      error: normalizeCompetitionLoaderError(error),
      stable: null,
      danger: null,
      meta: null,
      percentiles: null,
    };
  }
};
