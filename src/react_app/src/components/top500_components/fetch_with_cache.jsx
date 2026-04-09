import { useState, useEffect } from "react";
import LZString from "lz-string";
import { setCache, getCache } from "../utils/cache_utils";
import { fetchJson } from "../utils/fetchJson";

const MAX_CACHE_ITEMS = 100;
const MAX_BACKOFF_TIME = 60000; // 1 minute in milliseconds

const useFetchWithCache = (endpoint, cacheAge = 10) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!endpoint) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    let isCancelled = false;
    let retryTimeoutId = null;

    const readCachedResponse = (endpointsCache) => {
      const cachedData = endpointsCache[endpoint];
      if (!cachedData) {
        return null;
      }

      try {
        const decompressedData = LZString.decompressFromUTF16(cachedData);
        const parsedData = JSON.parse(decompressedData);
        const cacheTimestamp = new Date(parsedData.timestamp);
        const now = new Date();
        const minutesElapsedSinceCache = (now - cacheTimestamp) / 60000;

        if (minutesElapsedSinceCache < cacheAge) {
          return parsedData.data;
        }
      } catch (cacheError) {
        console.error(
          "Invalid JSON data in localStorage. Clearing the key:",
          endpoint
        );
      }

      delete endpointsCache[endpoint];
      setCache("endpoints", endpointsCache);
      return null;
    };

    const fetchData = async (retryCount = 0) => {
      const endpointsCache = getCache("endpoints") || {};
      const cachedResponse = readCachedResponse(endpointsCache);
      if (cachedResponse !== null) {
        if (!isCancelled) {
          setData(cachedResponse);
          setError(null);
          setIsLoading(false);
        }
        return;
      }

      if (!isCancelled) {
        setIsLoading(true);
      }

      try {
        const responseData = await fetchJson(endpoint);
        if (isCancelled) {
          return;
        }

        setData(responseData);
        setError(null);

        const compressedData = LZString.compressToUTF16(
          JSON.stringify({ data: responseData, timestamp: Date.now() })
        );
        endpointsCache[endpoint] = compressedData;
        setCache("endpoints", endpointsCache);

        // Implement cache eviction strategy
        const cacheKeys = Object.keys(endpointsCache);
        if (cacheKeys.length > MAX_CACHE_ITEMS) {
          const sortedKeys = cacheKeys.sort((a, b) => {
            const timeA = JSON.parse(
              LZString.decompressFromUTF16(endpointsCache[a])
            ).timestamp;
            const timeB = JSON.parse(
              LZString.decompressFromUTF16(endpointsCache[b])
            ).timestamp;
            return timeA - timeB;
          });
          delete endpointsCache[sortedKeys[0]];
          setCache("endpoints", endpointsCache);
        }
      } catch (fetchError) {
        if (isCancelled) {
          return;
        }

        console.error("Error fetching data:", fetchError);
        setError(fetchError);

        const backoffTime = Math.min(2 ** retryCount * 1000, MAX_BACKOFF_TIME);
        retryTimeoutId = window.setTimeout(
          () => fetchData(retryCount + 1),
          backoffTime
        );
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      isCancelled = true;
      if (retryTimeoutId !== null) {
        window.clearTimeout(retryTimeoutId);
      }
    };
  }, [endpoint, cacheAge]);

  return { data, error, isLoading };
};

export default useFetchWithCache;
