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

export { getBaseApiUrl, getBaseWebsocketUrl };
