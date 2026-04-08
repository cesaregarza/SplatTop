const defaultErrorMessage = (status) => `Request failed with status ${status}`;

const readErrorMessage = (data, response, fallbackMessage) => {
  if (typeof data?.detail === "string" && data.detail.trim()) {
    return data.detail;
  }

  return fallbackMessage || defaultErrorMessage(response.status);
};

export const fetchJson = async (url, options = {}) => {
  const { errorMessage, ...fetchOptions } = options;
  const response = await fetch(url, fetchOptions);
  let data = null;

  try {
    data = await response.json();
  } catch {}

  if (!response.ok) {
    const error = new Error(readErrorMessage(data, response, errorMessage));
    error.status = response.status;
    error.detail = data?.detail ?? null;
    throw error;
  }

  return data;
};

export default fetchJson;
