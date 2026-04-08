import { getBaseApiUrl } from "../utils";

const COMP_AUTH_BASE_PATH = "/api/comp-auth";
let cachedCompetitionAuthState = null;

const buildCompetitionAuthUrl = (path) => {
  const baseApiUrl = getBaseApiUrl();
  const endpoint = `${COMP_AUTH_BASE_PATH}${path}`;

  if (!baseApiUrl) {
    return endpoint;
  }

  return new URL(endpoint, baseApiUrl).href;
};

const cloneCompetitionAuthState = (state) => {
  if (!state || typeof state !== "object") {
    return null;
  }
  return { ...state };
};

const normalizeCompetitionAuthPayload = (payload) => ({
  available: payload?.available !== false,
  authenticated: Boolean(payload?.authenticated),
  isAdmin: Boolean(payload?.is_admin ?? payload?.isAdmin),
  discordId:
    typeof (payload?.discord_id ?? payload?.discordId) === "string" &&
    String(payload?.discord_id ?? payload?.discordId).trim()
      ? String(payload?.discord_id ?? payload?.discordId)
      : null,
});

export const readCachedCompetitionAuthState = () => cloneCompetitionAuthState(
  cachedCompetitionAuthState
);

export const writeCachedCompetitionAuthState = (payload) => {
  cachedCompetitionAuthState = normalizeCompetitionAuthPayload(payload);
  return readCachedCompetitionAuthState();
};

export const resetCachedCompetitionAuthState = () => {
  cachedCompetitionAuthState = null;
};

const readCompetitionAuthError = async (response) => {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  } catch {}

  return `Competition auth request failed (${response.status})`;
};

export const fetchCompetitionAuthState = async (signal) => {
  const response = await fetch(buildCompetitionAuthUrl("/me"), {
    credentials: "include",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    const error = new Error(await readCompetitionAuthError(response));
    error.status = response.status;
    throw error;
  }

  return writeCachedCompetitionAuthState(await response.json());
};

export const logoutCompetitionAuth = async () => {
  const response = await fetch(buildCompetitionAuthUrl("/logout"), {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const error = new Error(await readCompetitionAuthError(response));
    error.status = response.status;
    throw error;
  }

  return writeCachedCompetitionAuthState(await response.json());
};

export const resolveCompetitionDiscordLoginUrl = () => {
  const loginUrl = buildCompetitionAuthUrl("/discord/login");
  const currentUrl =
    typeof window === "undefined" ? "/" : window.location.href;

  if (!loginUrl.startsWith("http")) {
    const url = new URL(
      loginUrl,
      typeof window === "undefined"
        ? "http://localhost"
        : window.location.origin
    );
    url.searchParams.set("next", currentUrl);
    return url.toString();
  }

  const url = new URL(loginUrl);
  url.searchParams.set("next", currentUrl);
  return url.toString();
};
