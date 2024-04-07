import React, { useEffect, useState } from "react";
import axios from "axios";
import Loading from "./loading";
import PlayerTable from "./top500_components/player_table";
import ColumnSelector from "./top500_components/selectors/column_selector";
import columnsConfig from "./top500_components/columns_config";
import RegionSelector from "./top500_components/selectors/region_selector";
import ModeSelector from "./top500_components/selectors/mode_selector";

const Top500 = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 100;
  const maxCacheAge = 10;
  const cacheOffset = 6;
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRegion, setSelectedRegion] = useState("Tentatek");
  const [selectedMode, setSelectedMode] = useState("Splat Zones");

  const [columnVisibility, setColumnVisibility] = useState(
    columnsConfig.reduce((acc, column) => {
      acc[column.id] = column.isVisible;
      return acc;
    }, {})
  );

  const fetchData = async () => {
    setIsLoading(true);

    const apiUrl = process.env.REACT_APP_API_URL || "";
    const endpoint = `${apiUrl}/api/leaderboard?mode=${selectedMode}&region=${selectedRegion}`;

    const cachedData = localStorage.getItem(endpoint);
    if (cachedData) {
      const parsedData = JSON.parse(cachedData);
      const cacheTimestamp = new Date(parsedData.timestamp);
      const cacheMinute = cacheTimestamp.getMinutes();
      const now = new Date();
      const nowMinute = now.getMinutes();
      const minutesElapsedSinceCache = (now - cacheTimestamp) / 60000;
      const cacheMinuteMod = cacheMinute % maxCacheAge;
      const nowMinuteMod = nowMinute % maxCacheAge;
      var shouldRegenerateCache = false;

      if (
        minutesElapsedSinceCache >= maxCacheAge ||
        (nowMinuteMod > cacheMinuteMod &&
          nowMinuteMod >= cacheOffset &&
          cacheMinuteMod < cacheOffset) ||
        (nowMinuteMod < cacheMinuteMod && nowMinuteMod >= cacheOffset) ||
        (nowMinuteMod < cacheMinuteMod && cacheMinuteMod < cacheOffset)
      ) {
        localStorage.removeItem(endpoint);
        shouldRegenerateCache = true;
      }

      if (!shouldRegenerateCache) {
        setData(parsedData.data);
        setError(null);
        setIsLoading(false);
        return;
      }
    }

    const attemptFetch = async (retryAfter = 5) => {
      try {
        const response = await axios.get(endpoint);
        setData(response.data);
        setError(null);
        setIsLoading(false);

        localStorage.setItem(
          endpoint,
          JSON.stringify({
            data: response.data,
            timestamp: Date.now(),
          })
        );
      } catch (error) {
        if (error.response && error.response.status === 503) {
          console.log(
            `Received 503 error, retrying after ${retryAfter} seconds.`
          );
          setError(
            `Service temporarily unavailable. Retrying in ${retryAfter} seconds...`
          );
          setIsLoading(true); // Keep loading state true to indicate retrying
          setTimeout(() => {
            fetchData();
            setIsLoading(false); // Reset loading state after retry
          }, retryAfter * 1000);
        } else {
          console.error("Error fetching leaderboard data:", error);
          setError(error);
          setIsLoading(false);
        }
      }
    };

    attemptFetch();
  };

  useEffect(() => {
    fetchData();
  }, [selectedRegion, selectedMode, currentPage]);

  const { players } = data || { players: [] };

  const filteredPlayers = players.filter((player) =>
    player.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredPlayers.slice(indexOfFirstItem, indexOfLastItem);

  const paginate = (pageNumber) => setCurrentPage(pageNumber);

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
            <Loading />
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
      <div className="flex justify-center mt-4 flex-wrap">
        {Array.from(
          { length: Math.ceil(filteredPlayers.length / itemsPerPage) },
          (_, i) => (
            <button
              key={i}
              onClick={() => paginate(i + 1)}
              className={`mx-1 px-4 py-2 rounded-md ${
                currentPage === i + 1
                  ? "bg-purpledark text-white hover:bg-purple"
                  : "bg-gray-700 hover:bg-purple"
              }`}
            >
              {i + 1}
            </button>
          )
        )}
      </div>
    </div>
  );
};

export default Top500;
