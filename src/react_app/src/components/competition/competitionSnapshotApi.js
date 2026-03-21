const STABLE_ENDPOINT = "/api/ripple/public/leaderboard";
const DANGER_ENDPOINT = "/api/ripple/public/leaderboard/danger";
const META_ENDPOINT = "/api/ripple/public/metadata";
const PERCENTILES_ENDPOINT = "/api/ripple/public/leaderboard/percentiles";

export const normalizeCompetitionLoaderError = (error) => {
  if (!error) {
    return "Unknown error";
  }
  if (typeof error.detail === "string" && error.detail) {
    return error.detail;
  }
  return error.message || "Unexpected error";
};

export const fetchCompetitionJson = async (url, signal) => {
  const response = await fetch(url, { signal });
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
