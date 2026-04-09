import { getBaseApiUrl } from "../utils";
import { readCachedCompetitionAuthState } from "./competitionAuthApi";

const normalizePlayerRouteError = (value) => {
  if (!value) return "Unknown error";
  if (typeof value === "string") return value;
  if (typeof value.message === "string" && value.message) return value.message;
  return "Unexpected error";
};

const buildCompetitionApiUrl = (path) => {
  const baseApiUrl = getBaseApiUrl();
  if (!baseApiUrl) {
    return path;
  }
  return new URL(path, baseApiUrl).href;
};

const readPlayerRouteError = async (response) => {
  try {
    const payload = await response.clone().json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  } catch {
    // Fall back to a generic message when the response is not JSON.
  }

  if (response.status === 404) {
    return "Player not found in competition index";
  }
  return `Unable to load player profile (${response.status})`;
};

const fetchCompetitionPlayerJson = (path, signal) => fetch(
  buildCompetitionApiUrl(path),
  {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal,
  }
);

const shouldPreferAdminPlayerPayload = () => {
  const authState = readCachedCompetitionAuthState();
  return Boolean(authState?.authenticated && authState?.isAdmin);
};

const buildCompetitionPlayerPath = (id, accessMode, suffix = "") => {
  const encodedId = encodeURIComponent(id);
  if (accessMode === "admin") {
    return `/api/ripple/admin/player/${encodedId}${suffix}`;
  }
  return `/api/ripple/public/player/${encodedId}${suffix}`;
};

const fetchCompetitionPlayerPayload = async ({
  accessMode: initialAccessMode,
  id,
  signal,
  suffix = "",
}) => {
  let accessMode = initialAccessMode;
  let response = await fetchCompetitionPlayerJson(
    buildCompetitionPlayerPath(id, accessMode, suffix),
    signal
  );

  if (
    accessMode === "admin" &&
    !response.ok &&
    (response.status === 401 || response.status === 403)
  ) {
    accessMode = "public";
    response = await fetchCompetitionPlayerJson(
      buildCompetitionPlayerPath(id, accessMode, suffix),
      signal
    );
  }

  if (!response.ok) {
    const error = new Error(await readPlayerRouteError(response));
    error.status = response.status;
    error.accessMode = accessMode;
    throw error;
  }

  return {
    accessMode,
    payload: (await response.json()) || null,
  };
};

export const fetchCompetitionPlayerHistoryPayload = ({
  accessMode = "public",
  playerId,
  signal,
}) => fetchCompetitionPlayerPayload({
  accessMode,
  id: playerId,
  signal,
  suffix: "/history",
});

export const fetchCompetitionPlayerResultsPayload = ({
  accessMode = "public",
  playerId,
  signal,
}) => fetchCompetitionPlayerPayload({
  accessMode,
  id: playerId,
  signal,
  suffix: "/results",
});
export const loadCompetitionPlayer = async ({ params, request }) => {
  const id = String(params?.playerId || "").trim();
  if (!id) {
    return {
      accessMode: "public",
      error: "Missing player id",
      profile: null,
    };
  }

  try {
    const {
      accessMode,
      payload,
    } = await fetchCompetitionPlayerPayload({
      accessMode: shouldPreferAdminPlayerPayload() ? "admin" : "public",
      id,
      signal: request.signal,
      suffix: "/summary",
    });

    return {
      accessMode,
      error: null,
      profile: payload,
    };
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    return {
      accessMode: error?.accessMode || "public",
      error: normalizePlayerRouteError(error),
      profile: null,
    };
  }
};

export const primeCompetitionPlayerRoute = ({ params, request }) => ({
  playerId: String(params?.playerId || "").trim(),
  summaryRequest: loadCompetitionPlayer({ params, request }),
});
