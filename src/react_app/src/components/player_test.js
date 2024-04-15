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
  const [mode, setMode] = useState("Splat Zones");
  const [removeValuesNotInTop500, setRemoveValuesNotInTop500] = useState(true);

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

  const toggleRemoveValuesNotInTop500 = () => {
    setRemoveValuesNotInTop500(!removeValuesNotInTop500);
  };

  return (
    <div className="flex flex-col flex-grow">
      <header className="text-3xl font-bold mb-4 text-center text-white">
        Player Test Chart
      </header>
      <main className="flex-grow container mx-auto px-4 py-8 bg-gray-900 text-white overflow-auto">
        {isLoading ? (
          <div className="flex justify-center items-center h-full">
            <Loading />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center">{error.message}</div>
        ) : (
          <>
            <div className="controls mb-4">
              <select
                className="mode-selector bg-gray-800 text-white p-2.5 rounded-md border-none"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="Splat Zones">Splat Zones</option>
                <option value="Tower Control">Tower Control</option>
                <option value="Rainmaker">Rainmaker</option>
                <option value="Clam Blitz">Clam Blitz</option>
              </select>
              <div className="flex items-center space-x-2 mt-2">
                <input
                  id="top500Checkbox"
                  type="checkbox"
                  checked={removeValuesNotInTop500}
                  onChange={toggleRemoveValuesNotInTop500}
                  className="w-4 h-4 text-purple-600 bg-gray-800 border-gray-600 rounded focus:ring-purple-500"
                />
                <label htmlFor="top500Checkbox" className="text-white text-sm">
                  Remove Values Not in Top 500
                </label>
              </div>
            </div>
            <XChart
              data={data}
              mode={mode}
              removeValuesNotInTop500={removeValuesNotInTop500}
            />
          </>
        )}
      </main>
    </div>
  );
};

export default PlayerTest;
