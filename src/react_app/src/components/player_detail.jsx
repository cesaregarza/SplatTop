import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import Loading from "./loading";
import ChartController from "./player_components/chart_controller";
import Aliases from "./player_components/aliases";
import SeasonResults from "./player_components/season_results";
import Achievements from "./player_components/achievements";
import { modes } from "./constants";
import { getBaseApiUrl, getBaseWebsocketUrl } from "./utils";
import pako from "pako";

const DEFAULT_LANGUAGE = "USen";

const PlayerDetail = () => {
  const location = useLocation();
  const player_id = location.pathname.split("/")[2];
  const [data, setData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weaponTranslations, setWeaponTranslations] = useState(null);
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      document.title = "splat.top - Player Page";
      const apiUrl = getBaseApiUrl();
      const endpoint = `${apiUrl}/api/player/${player_id}`;
      const translationEndpoint = `${apiUrl}/api/game_translation`;
      const baseWebsocketUrl = getBaseWebsocketUrl();
      const websocketEndpoint = `${baseWebsocketUrl}/ws/player/${player_id}`;

      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        if (response.data && response.data.length > 0) {
          document.title = `splat.top - ${response.data[0].splashtag}`;
        }

        const translationsResponse = await axios.get(translationEndpoint);
        setWeaponTranslations(translationsResponse.data);

        if (socket) {
          socket.close();
        }

        const newSocket = new WebSocket(websocketEndpoint);

        newSocket.onmessage = (event) => {
          if (event.data instanceof Blob) {
            const reader = new FileReader();
            reader.onload = () => {
              const decompressedData = pako.inflate(reader.result, {
                to: "string",
              });
              const newData = JSON.parse(decompressedData);
              setChartData(newData);
            };
            reader.readAsArrayBuffer(event.data);
          } else {
            const newData = JSON.parse(event.data);
            setChartData(newData);
          }
        };

        newSocket.onerror = (event) => {
          setError(new Error("Websocket error"));
        };

        newSocket.onclose = (event) => {
          // Optionally handle the connection close
        };

        setSocket(newSocket);
      } catch (error) {
        setError(error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();

    return () => {
      if (socket) {
        socket.close();
      }
    };
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
                  {chartData ? (
                    <>
                      <SeasonResults data={chartData} />
                      <Achievements data={chartData} />
                    </>
                  ) : (
                    <Loading text="Loading season results..." />
                  )}
                </div>
                <div className="md:w-2/3 mt-8 md:mt-0">
                  {chartData ? (
                    <ChartController
                      data={chartData}
                      modes={modes}
                      weaponTranslations={weaponTranslations[DEFAULT_LANGUAGE]}
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

export default PlayerDetail;
