import React, { useEffect, useState, Suspense } from "react";
import useFetchWithCache from "./top500_components/fetch_with_cache";
import Loading from "./loading";
import columnsConfig from "./top500_components/columns_config";
import { getBaseApiUrl } from "./utils";
import { useTranslation } from "react-i18next";

const PlayerTable = React.lazy(() =>
  import("./top500_components/player_table")
);
const ColumnSelector = React.lazy(() =>
  import("./top500_components/selectors/column_selector")
);
const RegionSelector = React.lazy(() =>
  import("./top500_components/selectors/region_selector")
);
const ModeSelector = React.lazy(() =>
  import("./top500_components/selectors/mode_selector")
);
const Pagination = React.lazy(() => import("./top500_components/pagination"));

const modeNameMap = {
  "Splat Zones": "SZ",
  "Tower Control": "TC",
  Rainmaker: "RM",
  "Clam Blitz": "CB",
};

const Top500 = () => {
  const { t } = useTranslation("main_page");

  const [searchQuery, setSearchQuery] = useState(
    localStorage.getItem("searchQuery") || ""
  );
  const [currentPage, setCurrentPage] = useState(
    parseInt(localStorage.getItem("currentPage"), 10) || 1
  );
  const itemsPerPage = 100;
  const [selectedRegion, setSelectedRegion] = useState(
    localStorage.getItem("selectedRegion") || "Tentatek"
  );
  const [selectedMode, setSelectedMode] = useState(
    localStorage.getItem("selectedMode") || "Splat Zones"
  );

  const [columnVisibility, setColumnVisibility] = useState(
    JSON.parse(localStorage.getItem("columnVisibility")) ||
      columnsConfig.reduce((acc, column) => {
        acc[column.id] = column.isVisible;
        return acc;
      }, {})
  );

  useEffect(() => {
    document.title = `splat.top - ${selectedRegion} ${modeNameMap[selectedMode]}`;
    localStorage.setItem("searchQuery", searchQuery);
    localStorage.setItem("currentPage", currentPage.toString());
    localStorage.setItem("selectedRegion", selectedRegion);
    localStorage.setItem("selectedMode", selectedMode);
    localStorage.setItem("columnVisibility", JSON.stringify(columnVisibility));
  }, [
    searchQuery,
    currentPage,
    selectedRegion,
    selectedMode,
    columnVisibility,
  ]);

  const apiUrl = getBaseApiUrl();
  const endpoint = `${apiUrl}/api/leaderboard?mode=${selectedMode}&region=${selectedRegion}`;
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
    player.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredPlayers.slice(indexOfFirstItem, indexOfLastItem);

  const paginate = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="container mx-auto px-4 py-8 bg-gray-900 text-white min-h-screen sm:px-2 lg:px-8">
      <h1 className="text-3xl font-bold mb-4 text-center sm:text-2xl">
        {t("title")}
      </h1>
      <div className="flex flex-col sm:flex-row justify-between mb-4">
        <Suspense fallback={<div>{t("loading")}</div>}>
          <RegionSelector
            selectedRegion={selectedRegion}
            setSelectedRegion={setSelectedRegion}
          />
          <ModeSelector
            selectedMode={selectedMode}
            setSelectedMode={setSelectedMode}
          />
        </Suspense>
      </div>
      <Suspense fallback={<div>{t("loading")}</div>}>
        <ColumnSelector
          columnVisibility={columnVisibility}
          setColumnVisibility={setColumnVisibility}
          columnsConfig={columnsConfig}
        />
        <Pagination
          totalItems={filteredPlayers.length}
          itemsPerPage={itemsPerPage}
          currentPage={currentPage}
          onPageChange={paginate}
          isTopOfPage={true}
        />
      </Suspense>
      <input
        type="text"
        placeholder={t("search_placeholder")}
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="border border-gray-700 bg-gray-800 rounded-md px-4 py-2 mb-4 w-full focus:outline-none focus:ring-2 focus:ring-purple"
      />
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="text-center py-4">
            <Loading text={t("loading_top500")} />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center py-4">{error.message}</div>
        ) : (
          <Suspense fallback={<div>{t("loading")}</div>}>
            <PlayerTable
              players={currentItems}
              columnVisibility={columnVisibility}
            />
          </Suspense>
        )}
      </div>
      <Suspense fallback={<div>{t("loading")}</div>}>
        <Pagination
          totalItems={filteredPlayers.length}
          itemsPerPage={itemsPerPage}
          currentPage={currentPage}
          onPageChange={paginate}
          isTopOfPage={false}
        />
      </Suspense>
    </div>
  );
};

export default Top500;
