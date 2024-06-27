import { useState, useEffect } from "react";
import axios from "axios";
import LZString from "lz-string";
import { setCache, getCache } from "../utils/cache_utils";

const MAX_CACHE_ITEMS = 100;
const MAX_BACKOFF_TIME = 60000; // 1 minute in milliseconds

const useFetchWithCache = (endpoint, cacheAge = 10, cacheOffset = 6) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearLocalCache = () => {
    localStorage.removeItem("endpoints");
  };

  useEffect(() => {
    const deleteHttpCacheKeys = () => {
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith("http")) {
          localStorage.removeItem(key);
        }
      });
    };

    const fetchData = async (retryCount = 0) => {
      setIsLoading(true);
      deleteHttpCacheKeys();
      const endpointsCache = getCache("endpoints") || {};
      const cachedData = endpointsCache[endpoint];
      if (cachedData) {
        try {
          const decompressedData = LZString.decompressFromUTF16(cachedData);
          const parsedData = JSON.parse(decompressedData);
          const cacheTimestamp = new Date(parsedData.timestamp);
          const now = new Date();
          const minutesElapsedSinceCache = (now - cacheTimestamp) / 60000;

          if (minutesElapsedSinceCache < cacheAge) {
            setData(parsedData.data);
            setError(null);
            setIsLoading(false);
            return;
          } else {
            delete endpointsCache[endpoint];
            setCache("endpoints", endpointsCache);
          }
        } catch (error) {
          console.error(
            "Invalid JSON data in localStorage. Clearing the key:",
            endpoint
          );
          delete endpointsCache[endpoint];
          setCache("endpoints", endpointsCache);
        }
      }

      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        setError(null);

        const compressedData = LZString.compressToUTF16(
          JSON.stringify({ data: response.data, timestamp: Date.now() })
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
        console.error("Error fetching data:", fetchError);
        setError(fetchError);

        const backoffTime = Math.min(2 ** retryCount * 1000, MAX_BACKOFF_TIME);
        setTimeout(() => fetchData(retryCount + 1), backoffTime);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [endpoint, cacheAge, cacheOffset]);

  return { data, error, isLoading, clearLocalCache };
};

export default useFetchWithCache;
