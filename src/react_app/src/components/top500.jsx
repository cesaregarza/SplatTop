import React, { useEffect, useRef, useState, Suspense } from "react";
import useFetchWithCache from "./top500_components/fetch_with_cache";
import Loading from "./misc_components/loading";
import { columnsConfig } from "./top500_components/columns_config";
import { getBaseApiUrl } from "./utils";
import { useTranslation } from "react-i18next";
import { setCache, getCache } from "./utils/cache_utils";
import { modeKeyMap } from "./constants";

const PlayerTable = React.lazy(() =>
  import("./top500_components/player_table")
);
const AllModesTable = React.lazy(() =>
  import("./top500_components/all_modes_table")
);
const RegionSelector = React.lazy(() =>
  import("./top500_components/selectors/region_selector")
);
const ModeSelector = React.lazy(() =>
  import("./top500_components/selectors/mode_selector")
);
const Pagination = React.lazy(() => import("./top500_components/pagination"));
const RaceTo5000 = React.lazy(() => import("./race_to_5000"));

const modeNameMap = {
  "Splat Zones": "SZ",
  "Tower Control": "TC",
  Rainmaker: "RM",
  "Clam Blitz": "CB",
  "All Modes": "AM",
};

const defaultColumnVisibility = columnsConfig.reduce((acc, column) => {
  acc[column.id] = column.isVisible;
  return acc;
}, {});

const regionMetaMap = {
  Tentatek: "Tentatek",
  Takoroka: "Takoroka",
};

const Top500 = () => {
  const { t } = useTranslation("main_page");

  const [searchQuery, setSearchQuery] = useState(
    getCache("searchQuery", 60) || ""
  );
  const [currentPage, setCurrentPage] = useState(
    parseInt(getCache("currentPage", 300), 10) || 1
  );
  const itemsPerPage = 100;
  const [selectedRegion, setSelectedRegion] = useState(
    getCache("selectedRegion") || "Tentatek"
  );
  const [selectedMode, setSelectedMode] = useState(
    getCache("selectedMode") || "Splat Zones"
  );
  const [activeTab, setActiveTab] = useState(
    getCache("mainPageTab", 60) || "leaderboard"
  );

  const hasInitializedFilters = useRef(false);

  useEffect(() => {
    if (!hasInitializedFilters.current) {
      hasInitializedFilters.current = true;
      return;
    }
    setCurrentPage(1);
  }, [searchQuery, selectedRegion, selectedMode]);

  useEffect(() => {
    document.title =
      activeTab === "leaderboard"
        ? `splat.top - ${selectedRegion} ${modeNameMap[selectedMode]}`
        : "splat.top - Race to 5000";
    setCache("searchQuery", searchQuery, 60);
    setCache("currentPage", currentPage.toString(), 300);
    setCache("selectedRegion", selectedRegion);
    setCache("selectedMode", selectedMode, 60 * 60 * 24);
    setCache("mainPageTab", activeTab, 60 * 60 * 24);
  }, [searchQuery, currentPage, selectedRegion, selectedMode, activeTab]);

  const apiUrl = getBaseApiUrl();
  const endpoint =
    activeTab === "leaderboard"
      ? `${apiUrl}/api/leaderboard?mode=${selectedMode}&region=${selectedRegion}`
      : null;
  const { data, error, isLoading } = useFetchWithCache(endpoint);

  const players = data
    ? Object.keys(data.players).reduce((acc, key) => {
        data.players[key].forEach((value, index) => {
          if (!acc[index]) acc[index] = {};
          acc[index][key] = value;
        });
        return acc;
      }, [])
    : [];

  const filteredPlayers = players.filter((player) =>
    player.splashtag.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredPlayers.slice(indexOfFirstItem, indexOfLastItem);
  const displayStart = filteredPlayers.length === 0 ? 0 : indexOfFirstItem + 1;
  const displayEnd = Math.min(indexOfLastItem, filteredPlayers.length);

  const paginate = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const isAllModes =
    players.length > 0 && players[0].hasOwnProperty("total_x_power");
  const leaderboardHeaderMetadata = t("header.metadata")
    .replace("%region%", regionMetaMap[selectedRegion] || selectedRegion)
    .replace(
      "%mode%",
      selectedMode === "All Modes"
        ? t("all_modes")
        : t(modeKeyMap[selectedMode], {
            ns: "game",
            defaultValue: selectedMode,
          })
    )
    .replace("%count%", filteredPlayers.length);
  const raceHeaderMetadata = t("race.header_metadata", {
    defaultValue:
      "Current-season contenders over 4000 XP vs historical 5000+ ascents",
  });
  const resultsSummary = t("results.summary")
    .replace("%start%", displayStart)
    .replace("%end%", displayEnd)
    .replace("%total%", filteredPlayers.length);

  return (
    <div className="container mx-auto min-h-screen bg-gray-900 px-4 py-6 text-white sm:px-2 lg:px-8">
      <header className="mb-4 border-b border-gray-800/90 pb-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.28em] text-gray-400">
          {activeTab === "leaderboard"
            ? t("header.kicker")
            : t("header.kicker")}
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight sm:text-2xl">
          {activeTab === "leaderboard"
            ? t("title")
            : t("race.title", { defaultValue: "Race to 5000" })}
        </h1>
        <p className="mt-2 text-sm text-gray-300">
          {activeTab === "leaderboard"
            ? leaderboardHeaderMetadata
            : raceHeaderMetadata}
        </p>
      </header>

      <section className="mb-4 flex flex-wrap gap-2">
        {[
          {
            id: "leaderboard",
            label: t("tabs.leaderboard", { defaultValue: "Top 500" }),
          },
          {
            id: "race_to_5000",
            label: t("tabs.race_to_5000", {
              defaultValue: "Race to 5000",
            }),
          },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-md border px-3 py-2 text-sm font-medium transition ${
              activeTab === tab.id
                ? "border-purple-500/60 bg-purple-950/40 text-purple-100"
                : "border-gray-800 bg-gray-950/55 text-gray-300 hover:border-gray-700 hover:bg-gray-900/70 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </section>

      {activeTab === "leaderboard" ? (
        <>
          <section className="mb-4 rounded-lg border border-gray-800 bg-gray-950/70 p-3 sm:p-4">
            <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(18rem,auto)] xl:items-end">
              <div className="grid gap-3 lg:grid-cols-[auto_minmax(0,1fr)]">
                <div>
                  <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-gray-400">
                    {t("controls.region")}
                  </p>
                  <Suspense fallback={<div>{t("loading")}</div>}>
                    <RegionSelector
                      selectedRegion={selectedRegion}
                      setSelectedRegion={setSelectedRegion}
                      showTitle={false}
                      showLabels={true}
                      buttonVariant="utility"
                      buttonPadding="px-3 py-2"
                      imageWidth="w-8"
                      imageHeight="h-8"
                      baseClass="w-full"
                    />
                  </Suspense>
                </div>
                <div>
                  <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-gray-400">
                    {t("controls.mode")}
                  </p>
                  <Suspense fallback={<div>{t("loading")}</div>}>
                    <ModeSelector
                      selectedMode={selectedMode}
                      setSelectedMode={setSelectedMode}
                      includeAllModes={true}
                      showTitle={false}
                      buttonVariant="utility"
                      buttonPadding="px-3 py-2"
                      imageWidth="w-8"
                      imageHeight="h-8"
                      baseClass="w-full"
                    />
                  </Suspense>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] xl:grid-cols-[minmax(14rem,1fr)_auto] xl:items-end">
                <label className="block">
                  <span className="mb-2 block text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-gray-400">
                    {t("controls.search")}
                  </span>
                  <input
                    type="text"
                    placeholder={t("search_placeholder")}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full rounded-md border border-gray-800 bg-gray-950/70 px-3 py-2.5 text-sm text-white placeholder:text-gray-500 focus:outline-hidden focus:ring-2 focus:ring-purple"
                  />
                </label>

                <div>
                  <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-gray-400">
                    {t("controls.page")}
                  </p>
                  <Suspense fallback={<div>{t("loading")}</div>}>
                    <Pagination
                      totalItems={filteredPlayers.length}
                      itemsPerPage={itemsPerPage}
                      currentPage={currentPage}
                      onPageChange={paginate}
                      isTopOfPage={true}
                      compact={true}
                      align="right"
                      className="mb-0"
                    />
                  </Suspense>
                </div>
              </div>
            </div>
          </section>

          <section className="overflow-hidden rounded-lg border border-gray-800 bg-gray-950/55">
            <div className="flex flex-col gap-1 border-b border-gray-800 bg-gray-950/80 px-4 py-3">
              <h2 className="text-lg font-semibold text-white">{t("results.title")}</h2>
              <p className="text-sm text-gray-400">{resultsSummary}</p>
            </div>

            <div className="overflow-x-auto">
              {isLoading ? (
                <div className="py-8 text-center">
                  <Loading text={t("loading_top500")} />
                </div>
              ) : error ? (
                <div className="py-8 text-center text-red-500">{error.message}</div>
              ) : filteredPlayers.length === 0 ? (
                <div className="py-8 text-center text-gray-300">{t("no_results")}</div>
              ) : (
                <Suspense fallback={<div>{t("loading")}</div>}>
                  {isAllModes ? (
                    <AllModesTable players={currentItems} />
                  ) : (
                    <PlayerTable
                      players={currentItems}
                      columnVisibility={defaultColumnVisibility}
                    />
                  )}
                </Suspense>
              )}
            </div>
          </section>

          <Suspense fallback={<div>{t("loading")}</div>}>
            <Pagination
              totalItems={filteredPlayers.length}
              itemsPerPage={itemsPerPage}
              currentPage={currentPage}
              onPageChange={paginate}
              isTopOfPage={false}
              compact={true}
              align="right"
              className="mt-3"
            />
          </Suspense>
        </>
      ) : (
        <Suspense fallback={<div>{t("loading")}</div>}>
          <RaceTo5000 />
        </Suspense>
      )}
    </div>
  );
};

export default Top500;
