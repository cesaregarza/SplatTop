export const setCache = (key, data, expiration = null) => {
  const now = new Date();
  let expirationDate;
  const version = process.env.REACT_APP_VERSION;

  if (typeof expiration === "number") {
    expirationDate = new Date(now.getTime() + expiration * 1000).toISOString();
  } else if (expiration instanceof Date) {
    expirationDate = expiration.toISOString();
  } else {
    const midnightUTC = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1)
    );
    expirationDate = midnightUTC.toISOString();
  }

  localStorage.setItem(key, JSON.stringify(data));
  localStorage.setItem(`${key}Expiration`, expirationDate);
  localStorage.setItem(`${key}Version`, version);
};

export const getCache = (key) => {
  const localData = localStorage.getItem(key);
  const cacheExpiration = localStorage.getItem(`${key}Expiration`);
  const cacheVersion = localStorage.getItem(`${key}Version`);
  const currentVersion = process.env.REACT_APP_VERSION;

  if (
    localData &&
    cacheExpiration &&
    cacheVersion &&
    new Date(cacheExpiration) > new Date() &&
    cacheVersion === currentVersion
  ) {
    try {
      return JSON.parse(localData);
    } catch (error) {
      // If parsing fails, remove the invalid cache entry
      localStorage.removeItem(key);
      localStorage.removeItem(`${key}Expiration`);
      localStorage.removeItem(`${key}Version`);
      return null;
    }
  } else if (cacheVersion !== null && cacheVersion !== currentVersion) {
    clearInvalidVersionCache();
  }

  return null;
};

export const deleteCache = (key) => {
  localStorage.removeItem(key);
  localStorage.removeItem(`${key}Expiration`);
  localStorage.removeItem(`${key}Version`);
};

export const clearInvalidVersionCache = () => {
  const currentVersion = process.env.REACT_APP_VERSION;
  Object.keys(localStorage).forEach((key) => {
    const cacheVersion = localStorage.getItem(`${key}Version`);
    if (cacheVersion !== currentVersion) {
      localStorage.removeItem(key);
      localStorage.removeItem(`${key}Expiration`);
      localStorage.removeItem(`${key}Version`);
    }
  });
};
