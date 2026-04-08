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

const fetchCompetitionPlayerProfile = (id, signal, path) => fetch(
  buildCompetitionApiUrl(path.replace(":id", encodeURIComponent(id))),
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
    let accessMode = shouldPreferAdminPlayerPayload() ? "admin" : "public";
    let response = await fetchCompetitionPlayerProfile(
      id,
      request.signal,
      accessMode === "admin"
        ? "/api/ripple/admin/player/:id"
        : "/api/ripple/public/player/:id"
    );

    if (
      accessMode === "admin" &&
      !response.ok &&
      (response.status === 401 || response.status === 403)
    ) {
      accessMode = "public";
      response = await fetchCompetitionPlayerProfile(
        id,
        request.signal,
        "/api/ripple/public/player/:id"
      );
    }

    if (!response.ok) {
      return {
        accessMode,
        error: await readPlayerRouteError(response),
        profile: null,
      };
    }

    return {
      accessMode,
      error: null,
      profile: (await response.json()) || null,
    };
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    return {
      accessMode: "public",
      error: normalizePlayerRouteError(error),
      profile: null,
    };
  }
};
