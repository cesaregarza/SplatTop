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
  const url = new URL(endpoint, baseUrl);
  Object.keys(params).forEach((key) =>
    url.searchParams.append(key, params[key])
  );
  return url.toString();
};

export { getBaseApiUrl, getBaseWebsocketUrl, buildEndpointWithQueryParams };
