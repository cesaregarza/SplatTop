const COMPETITION_OVERRIDE_KEY = "splat.top.competitionOverride";
const DEFAULT_FAVICON_HREF = "/favicon.ico?v=1";
const DEFAULT_FAVICON_TYPE = "image/x-icon";
const COMPETITION_FAVICON_HREF = "/favicon-comp.svg?v=1";
const COMPETITION_FAVICON_TYPE = "image/svg+xml";

export const readBoolean = (value) => {
  if (value == null) return null;
  const normalized = String(value).trim().toLowerCase();
  if (normalized === "true" || normalized === "1") return true;
  if (normalized === "false" || normalized === "0") return false;
  return null;
};

export const isCompetitionHostname = () => {
  if (typeof window === "undefined") {
    return false;
  }

  const hostname = window.location.hostname.toLowerCase();
  return hostname === "comp.localhost" || hostname.startsWith("comp.");
};

export const readCompetitionOverrideFromSearch = () => {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const params = new URLSearchParams(window.location.search);
    return readBoolean(params.get("competition"));
  } catch {
    return null;
  }
};

export const persistCompetitionOverride = (override) => {
  if (typeof window === "undefined" || override == null) {
    return;
  }

  try {
    window.localStorage?.setItem(
      COMPETITION_OVERRIDE_KEY,
      override ? "true" : "false"
    );
  } catch {}
};

export const detectCompetitionHost = () => {
  const explicitFlag = readBoolean(process.env.REACT_APP_ENABLE_COMPETITION);
  if (explicitFlag !== null) return explicitFlag;

  const overrideParam = readCompetitionOverrideFromSearch();
  if (overrideParam !== null) return overrideParam;

  if (typeof window !== "undefined") {
    try {
      const stored = readBoolean(
        window.localStorage?.getItem(COMPETITION_OVERRIDE_KEY)
      );
      if (stored !== null) return stored;
    } catch {}
  }

  if (typeof window === "undefined") {
    return false;
  }
  return isCompetitionHostname();
};

export const setFaviconForMode = (isCompetition) => {
  if (typeof document === "undefined") {
    return;
  }

  let favicon = document.querySelector('link[rel="icon"]');
  if (!favicon) {
    favicon = document.createElement("link");
    favicon.setAttribute("rel", "icon");
    document.head.appendChild(favicon);
  }

  favicon.setAttribute(
    "href",
    isCompetition ? COMPETITION_FAVICON_HREF : DEFAULT_FAVICON_HREF
  );
  favicon.setAttribute(
    "type",
    isCompetition ? COMPETITION_FAVICON_TYPE : DEFAULT_FAVICON_TYPE
  );
};

export const resolveCompetitionMainSiteUrl = () => {
  const override = process.env.REACT_APP_MAIN_SITE_URL;
  if (override) return override;

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    if (hostname === "comp.localhost") {
      return `${protocol}//localhost:3000/`;
    }
  }

  return "https://splat.top/";
};
