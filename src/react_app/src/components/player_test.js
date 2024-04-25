import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import Loading from "./loading";
import ChartController from "./player_components/chart_controller";
import Aliases from "./player_components/aliases";
import { modes } from "./constants";

import { filterDataAndGroupByWeapon, processGroupedData } from "./player_components/weapon_helper_functions";

const PlayerTest = () => {
  const location = useLocation();
  const player_id = location.pathname.split("/")[2];
  const [data, setData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      document.title = "splat.top - Player Page";
      const apiUrl = "http://localhost:5000";
      const endpoint = `${apiUrl}/player_test/${player_id}`;
      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        if (response.data && response.data.length > 0) {
          document.title = `splat.top - ${response.data[0].splashtag}`;
        }

        const socket = new WebSocket(
          `${apiUrl.replace("http", "ws")}/ws/player/${player_id}`
        );

        socket.onmessage = (event) => {
          console.log("Received data from websocket");
          const newData = JSON.parse(event.data);
          console.log(newData);
          const groupedData = filterDataAndGroupByWeapon(newData, modes[0]);
          console.log(groupedData);
          console.log(processGroupedData(groupedData, [6]));
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

  return (
    <div className="flex flex-col min-h-screen">
      <header className="text-3xl font-bold mb-4 text-center text-white">
        Player Page
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
            {data && data.length > 0 ? (
              <div className="flex flex-col md:flex-row">
                <div className="md:w-1/3 md:pr-8">
                  <Aliases data={data} />
                </div>
                <div className="md:w-2/3 mt-8 md:mt-0">
                  {chartData ? (
                    <ChartController
                      data={chartData}
                      modes={modes}
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
