const getBaseApiUrl = () => {
  const isDevelopment = process.env.NODE_ENV === "development";
  return isDevelopment ? "http://localhost:5000" : "";
};

const getBaseWebsocketUrl = () => {
  const isDevelopment = process.env.NODE_ENV === "development";
  return isDevelopment
    ? "ws://localhost:5000"
    : `wss://${window.location.host}`;
};

export { getBaseApiUrl, getBaseWebsocketUrl };
