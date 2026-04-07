import React, { Suspense, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import Loading from "./misc_components/loading";
import { modes } from "./constants";
import { getBaseApiUrl, getBaseWebsocketUrl } from "./utils";
import pako from "pako";
import { useTranslation } from "react-i18next";
import {
  WeaponAndTranslationProvider,
  useWeaponAndTranslation,
} from "./utils/weaponAndTranslation";
import { fetchJson } from "./utils/fetchJson";
import { getPlayerSummary } from "./player_components/playerPageUtils";

const ChartController = React.lazy(() =>
  import("./player_components/chart_controller")
);
const Aliases = React.lazy(() => import("./player_components/aliases"));
const Achievements = React.lazy(() =>
  import("./player_components/achievements")
);

const formatSummaryDate = (value) => {
  if (!value) {
    return "--";
  }

  return new Date(value).toLocaleString("default", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
};

const formatSummaryNumber = (value, digits = 0, prefix = "") => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--";
  }

  const formattedValue = digits > 0 ? value.toFixed(digits) : value.toString();
  return `${prefix}${formattedValue}`;
};

const InlineLoadingPanel = ({ text }) => (
  <div className="flex min-h-[14rem] flex-col items-center justify-center rounded-xl border border-gray-800/80 bg-gray-950/35 p-4 text-center">
    <div className="h-9 w-9 animate-spin rounded-full border-2 border-purple border-t-transparent"></div>
    <p className="mt-4 text-sm text-gray-300">{text}</p>
  </div>
);

const CompactPlayerHeader = ({ summary, t }) => {
  const metadataItems = [
    t("summary.last_seen_inline").replace(
      "%DATE%",
      formatSummaryDate(summary.lastSeen)
    ),
    t("summary.aliases_inline").replace("%COUNT%", summary.aliasCount ?? 0),
    t("summary.best_rank_inline").replace(
      "%VALUE%",
      formatSummaryNumber(summary.bestRank, 0, "#")
    ),
    t("summary.best_xp_inline").replace(
      "%VALUE%",
      formatSummaryNumber(summary.bestXp, 1)
    ),
  ];

  return (
    <header className="border-b border-gray-800/60 pb-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">
        {t("summary.dossier_label")}
      </p>
      <h1 className="text-3xl font-black tracking-tight text-white sm:text-4xl">
        {summary.currentAlias || t("page_title")}
      </h1>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-400">
        {metadataItems.map((item, index) => (
          <React.Fragment key={item}>
            {index > 0 ? <span className="text-gray-600">·</span> : null}
            <span className="tabular-nums">{item}</span>
          </React.Fragment>
        ))}
      </div>
    </header>
  );
};

const PlayerDetailContent = () => {
  const { t } = useTranslation("player");
  const location = useLocation();
  const player_id = location.pathname.split("/")[2];
  const [data, setData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const socketRef = useRef(null);

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
      const endpoint = `${apiUrl}/api/players/${player_id}`;
      const baseWebsocketUrl = getBaseWebsocketUrl();
      const websocketEndpoint = `${baseWebsocketUrl}/ws/player/${player_id}`;

      try {
        const playerData = await fetchJson(endpoint);
        setData(playerData);

        if (playerData && playerData.length > 0) {
          document.title = t("document_title_loaded").replace(
            "%PLAYER%",
            playerData[0].splashtag
          );
        }

        if (socketRef.current) {
          socketRef.current.close();
          socketRef.current = null;
        }

        const newSocket = new WebSocket(websocketEndpoint);

        newSocket.onmessage = (event) => {
          if (event.data instanceof Blob) {
            const reader = new FileReader();
            reader.onload = () => {
              const decompressedData = pako.inflate(reader.result, {
                to: "string",
              });
              setChartData(JSON.parse(decompressedData));
            };
            reader.readAsArrayBuffer(event.data);
          } else {
            setChartData(JSON.parse(event.data));
          }
        };

        newSocket.onerror = (event) => {
          console.error("Websocket error", event);
        };

        socketRef.current = newSocket;
      } catch (currentError) {
        setError(currentError);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [player_id, t]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading || isWeaponDataLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loading text={t("load_page")} />
      </div>
    );
  }

  if (error || weaponDataError) {
    return (
      <div className="rounded-xl border border-red-900/60 bg-red-950/20 px-4 py-6 text-center text-red-300">
        {(error || weaponDataError).message}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return <div className="text-center">{t("no_data")}</div>;
  }

  const summary = getPlayerSummary(data, chartData, modes);

  return (
    <Suspense fallback={<InlineLoadingPanel text={t("load_component")} />}>
      <div className="space-y-6">
        <CompactPlayerHeader summary={summary} t={t} />
        <div className="grid gap-6 xl:grid-cols-[minmax(18rem,0.88fr)_minmax(0,1.55fr)]">
          <aside className="order-2 space-y-4 xl:order-1">
            <Aliases data={summary.aliases} />
            {chartData ? (
              <Achievements data={chartData} />
            ) : (
              <InlineLoadingPanel text={t("load_results")} />
            )}
          </aside>
          <section className="order-1 xl:order-2">
            {chartData ? (
              <ChartController
                data={chartData}
                modes={modes}
                weaponTranslations={weaponTranslations[t("data_lang_key")]}
                weaponReferenceData={weaponReferenceData}
              />
            ) : (
              <InlineLoadingPanel text={t("load_chart")} />
            )}
          </section>
        </div>
      </div>
    </Suspense>
  );
};

const PlayerDetail = () => (
  <WeaponAndTranslationProvider>
    <div className="flex min-h-screen flex-col bg-gray-900 text-white">
      <main className="grow">
        <div className="container mx-auto px-4 py-8">
          <PlayerDetailContent />
        </div>
      </main>
    </div>
  </WeaponAndTranslationProvider>
);

export default PlayerDetail;
