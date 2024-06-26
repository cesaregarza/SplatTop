const getBaseApiUrl = () => {
  const isDevelopment = process.env.NODE_ENV === "development";
  return isDevelopment ? "http://localhost:5000" : "";
};

const getBaseWebsocketUrl = () => {
  const isDevelopment = process.env.NODE_ENV === "development";
  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
  return isDevelopment
    ? "ws://localhost:5000"
    : `${wsProtocol}://${window.location.host}`;
};

const buildEndpointWithQueryParams = (baseUrl, endpoint, params) => {
  let url;
  if (baseUrl.startsWith("http")) {
    url = new URL(endpoint, baseUrl);
  } else {
    url = new URL(endpoint, window.location.origin + baseUrl);
  }
  Object.keys(params).forEach((key) =>
    url.searchParams.append(key, params[key])
  );
  return baseUrl.startsWith("http") ? url.href : url.pathname + url.search;
};

export { getBaseApiUrl, getBaseWebsocketUrl, buildEndpointWithQueryParams };
