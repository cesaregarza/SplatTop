import React, { useState, useEffect, Suspense } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import Loading from "./misc_components/loading";
import { modes } from "./constants";
import { getBaseApiUrl, getBaseWebsocketUrl } from "./utils";
import pako from "pako";
import { useTranslation } from "react-i18next";
import {
  WeaponAndTranslationProvider,
  useWeaponAndTranslation,
} from "./utils/weaponAndTranslation";

const ChartController = React.lazy(() =>
  import("./player_components/chart_controller")
);
const Aliases = React.lazy(() => import("./player_components/aliases"));
const SeasonResults = React.lazy(() =>
  import("./player_components/season_results")
);
const Achievements = React.lazy(() =>
  import("./player_components/achievements")
);

const PlayerDetailContent = () => {
  const { t } = useTranslation("player");
  const location = useLocation();
  const player_id = location.pathname.split("/")[2];
  const [data, setData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [socket, setSocket] = useState(null);

  const {
    weaponTranslations,
    weaponReferenceData,
    isLoading: isWeaponDataLoading,
    error: weaponDataError,
  } = useWeaponAndTranslation();

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      document.title = t("document_title_loading");
      const apiUrl = getBaseApiUrl();
      const endpoint = `${apiUrl}/api/player/${player_id}`;
      const baseWebsocketUrl = getBaseWebsocketUrl();
      const websocketEndpoint = `${baseWebsocketUrl}/ws/player/${player_id}`;

      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        if (response.data && response.data.length > 0) {
          document.title = t("document_title_loaded").replace(
            "%PLAYER%",
            response.data[0].splashtag
          );
        }

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
          console.error("Websocket error", event);
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
  }, [player_id, t]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading || isWeaponDataLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <Loading text={t("load_page")} />
      </div>
    );
  }

  if (error || weaponDataError) {
    return (
      <div className="text-red-500 text-center">
        {(error || weaponDataError).message}
      </div>
    );
  }

  return (
    <Suspense fallback={<Loading text={t("load_component")} />}>
      {data && data.length > 0 ? (
        <div className="flex flex-col md:flex-row">
          <div className="md:w-2/5 md:pr-8">
            <Aliases data={data} />
            {chartData ? (
              <>
                <SeasonResults
                  data={chartData}
                  weaponReferenceData={weaponReferenceData}
                />
                <Achievements data={chartData} />
              </>
            ) : (
              <Loading text={t("load_results")} />
            )}
          </div>
          <div className="md:w-3/5 mt-8 md:mt-0">
            {chartData ? (
              <ChartController
                data={chartData}
                modes={modes}
                weaponTranslations={weaponTranslations[t("data_lang_key")]}
                weaponReferenceData={weaponReferenceData}
              />
            ) : (
              <Loading text={t("load_chart")} />
            )}
          </div>
        </div>
      ) : (
        <div className="text-center">{t("no_data")}</div>
      )}
    </Suspense>
  );
};

const PlayerDetail = () => {
  const { t } = useTranslation("player");

  return (
    <WeaponAndTranslationProvider>
      <div className="flex flex-col min-h-screen">
        <header className="text-3xl font-bold mb-4 text-center text-white">
          {t("page_title")}
        </header>
        <main className="grow container mx-auto px-4 py-8 bg-gray-900 text-white overflow-auto">
          <PlayerDetailContent />
        </main>
      </div>
    </WeaponAndTranslationProvider>
  );
};

export default PlayerDetail;
