const normalizePlayerRouteError = (value) => {
  if (!value) return "Unknown error";
  if (typeof value === "string") return value;
  if (typeof value.message === "string" && value.message) return value.message;
  return "Unexpected error";
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

export const loadCompetitionPlayer = async ({ params, request }) => {
  const id = String(params?.playerId || "").trim();
  if (!id) {
    return {
      error: "Missing player id",
      profile: null,
    };
  }

  try {
    const response = await fetch(
      `/api/ripple/public/player/${encodeURIComponent(id)}`,
      {
        headers: { Accept: "application/json" },
        signal: request.signal,
      }
    );

    if (!response.ok) {
      return {
        error: await readPlayerRouteError(response),
        profile: null,
      };
    }

    return {
      error: null,
      profile: (await response.json()) || null,
    };
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    return {
      error: normalizePlayerRouteError(error),
      profile: null,
    };
  }
};
