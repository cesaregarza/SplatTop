import { useState, useEffect } from "react";
import axios from "axios";
import LZString from "lz-string";

const MAX_CACHE_ITEMS = 100;

const useFetchWithCache = (endpoint, cacheAge = 10, cacheOffset = 6) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearLocalCache = () => {
    localStorage.clear();
  };

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      const cachedData = localStorage.getItem(endpoint);
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
            localStorage.removeItem(endpoint);
          }
        } catch (error) {
          console.error(
            "Invalid JSON data in localStorage. Clearing the key:",
            endpoint
          );
          localStorage.removeItem(endpoint);
        }
      }

      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        setError(null);

        const compressedData = LZString.compressToUTF16(
          JSON.stringify({ data: response.data, timestamp: Date.now() })
        );
        localStorage.setItem(endpoint, compressedData);

        // Implement cache eviction strategy
        const cacheKeys = Object.keys(localStorage);
        if (cacheKeys.length > MAX_CACHE_ITEMS) {
          cacheKeys.sort((a, b) => {
            const timeA = JSON.parse(
              LZString.decompressFromUTF16(localStorage.getItem(a))
            ).timestamp;
            const timeB = JSON.parse(
              LZString.decompressFromUTF16(localStorage.getItem(b))
            ).timestamp;
            return timeA - timeB;
          });
          localStorage.removeItem(cacheKeys[0]);
        }
      } catch (fetchError) {
        console.error("Error fetching data:", fetchError);
        setError(fetchError);

        clearLocalCache();
        fetchData();
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [endpoint, cacheAge, cacheOffset]);

  return { data, error, isLoading, clearLocalCache };
};

export default useFetchWithCache;