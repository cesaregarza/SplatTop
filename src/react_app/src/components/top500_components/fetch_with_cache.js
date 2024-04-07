import { useState, useEffect } from "react";
import axios from "axios";

const useFetchWithCache = (endpoint, cacheAge = 10, cacheOffset = 6) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      const cachedData = localStorage.getItem(endpoint);
      if (cachedData) {
        const parsedData = JSON.parse(cachedData);
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
      }

      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        setError(null);
        localStorage.setItem(
          endpoint,
          JSON.stringify({ data: response.data, timestamp: Date.now() })
        );
      } catch (fetchError) {
        console.error("Error fetching data:", fetchError);
        setError(fetchError);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [endpoint, cacheAge, cacheOffset]);

  return { data, error, isLoading };
};

export default useFetchWithCache;
