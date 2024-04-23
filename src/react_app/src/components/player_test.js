import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import Loading from "./loading";
import XChart from "./player_components/xchart";
import Aliases from "./player_components/aliases";
import ModeSelector from "./top500_components/selectors/mode_selector";

const PlayerTest = () => {
  const location = useLocation();
  const player_id = location.pathname.split("/")[2];
  const [data, setData] = useState(null);
  const [chartData, setChartData] = useState(null);
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

        const socket = new WebSocket(
          `${apiUrl.replace("http", "ws")}/ws/player/${player_id}`
        );

        socket.onmessage = (event) => {
          console.log("Received data from websocket");
          const newData = JSON.parse(event.data);
          setChartData(newData);
        };

        return () => {
          socket.close();
        };
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
    <div className="flex flex-col min-h-screen">
      <header className="text-3xl font-bold mb-4 text-center text-white">
        Player Test Chart
      </header>
      <main className="flex-grow container mx-auto px-4 py-8 bg-gray-900 text-white overflow-auto">
        {isLoading ? (
          <div className="flex justify-center items-center h-full">
            <Loading text="Loading page..." />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center">{error.message}</div>
        ) : (
          <>
            <div className="controls mb-4">
              <ModeSelector selectedMode={mode} setSelectedMode={setMode} />
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
            {data && data.length > 0 ? (
              <div className="flex flex-col md:flex-row">
                <div className="md:w-1/3 md:pr-8">
                  <Aliases data={data} />
                </div>
                <div className="md:w-2/3 mt-8 md:mt-0">
                  {chartData ? (
                    <XChart
                      data={chartData}
                      mode={mode}
                      removeValuesNotInTop500={removeValuesNotInTop500}
                    />
                  ) : (
                    <Loading text={"Loading chart..."} />
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center">No data available</div>
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default PlayerTest;
