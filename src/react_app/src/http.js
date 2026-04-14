class HttpError extends Error {
  constructor(message, status, data, url) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.url = url;
    this.response = {
      status,
      data,
    };
  }
}

const parseJsonResponse = async (response) => {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
};

const buildErrorMessage = (response, data) => {
  if (data && typeof data === "object" && data.detail) {
    return data.detail;
  }
  return `Request failed with status ${response.status}`;
};

export const isHttpError = (error) => error instanceof HttpError;

export const fetchJson = async (url, options = {}) => {
  let response;

  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(error.message || "Network request failed");
  }

  const data = await parseJsonResponse(response);

  if (!response.ok) {
    throw new HttpError(
      buildErrorMessage(response, data),
      response.status,
      data,
      url
    );
  }

  return data;
};
