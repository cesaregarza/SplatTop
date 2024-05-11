import React, { useEffect, useState } from "react";
import useFetchWithCache from "./top500_components/fetch_with_cache";
import Loading from "./loading";
import PlayerTable from "./top500_components/player_table";
import ColumnSelector from "./top500_components/selectors/column_selector";
import columnsConfig from "./top500_components/columns_config";
import RegionSelector from "./top500_components/selectors/region_selector";
import ModeSelector from "./top500_components/selectors/mode_selector";
import Pagination from "./top500_components/pagination";

const Top500 = () => {
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

  const modeNameMap = {
    "Splat Zones": "SZ",
    "Tower Control": "TC",
    Rainmaker: "RM",
    "Clam Blitz": "CB",
  };

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

  const isDevelopment = process.env.NODE_ENV === "development";
  const apiUrl = isDevelopment
    ? "http://localhost:5000"
    : process.env.REACT_APP_API_URL || "";
  const endpoint = `${apiUrl}/api/leaderboard?mode=${selectedMode}&region=${selectedRegion}`;
  const { data, error, isLoading } = useFetchWithCache(endpoint);

  const { players } = data || { players: [] };

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
        Top 500
      </h1>
      <div className="flex flex-col sm:flex-row justify-between mb-4">
        <RegionSelector
          selectedRegion={selectedRegion}
          setSelectedRegion={setSelectedRegion}
        />
        <ModeSelector
          selectedMode={selectedMode}
          setSelectedMode={setSelectedMode}
        />
      </div>
      <ColumnSelector
        columnVisibility={columnVisibility}
        setColumnVisibility={setColumnVisibility}
      />
      <Pagination
        totalItems={filteredPlayers.length}
        itemsPerPage={itemsPerPage}
        currentPage={currentPage}
        onPageChange={paginate}
        isTopOfPage={true}
      />
      <input
        type="text"
        placeholder="Search"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="border border-gray-700 bg-gray-800 rounded-md px-4 py-2 mb-4 w-full focus:outline-none focus:ring-2 focus:ring-purple"
      />
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="text-center py-4">
            <Loading text="Loading Top 500..." />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center py-4">{error.message}</div>
        ) : (
          <PlayerTable
            players={currentItems}
            columnVisibility={columnVisibility}
          />
        )}
      </div>
      <Pagination
        totalItems={filteredPlayers.length}
        itemsPerPage={itemsPerPage}
        currentPage={currentPage}
        onPageChange={paginate}
        isTopOfPage={false}
      />
    </div>
  );
};

export default Top500;
