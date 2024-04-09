import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import Loading from "./loading";
import XChart from "./player_components/xchart";

const PlayerTest = () => {
  const location = useLocation();
  const player_id = location.pathname.split("/")[2];
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      const apiUrl = "http://localhost:5000";
      const endpoint = `${apiUrl}/player_test/${player_id}`;
      try {
        const response = await axios.get(endpoint);
        setData(response.data);
      } catch (error) {
        setError(error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [player_id]);

  return (
    <div className="container mx-auto px-4 py-8 bg-gray-900 text-white min-h-screen">
      <h1 className="text-3xl font-bold mb-4 text-center">Player Test Chart</h1>
      {isLoading ? (
        <div className="text-center py-4">
          <Loading />
        </div>
      ) : error ? (
        <div className="text-red-500 text-center py-4">{error.message}</div>
      ) : (
        <div>
            <XChart data={data} />
        </div>
      )}
    </div>
  );
};

export default PlayerTest;
