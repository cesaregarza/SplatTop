import React, { useCallback, useEffect, useMemo, useState } from "react";
import PlayerTable from "../top500_components/player_table";
import Pagination from "../top500_components/pagination";
import RegionSelector from "../top500_components/selectors/region_selector";
import ModeSelector from "../top500_components/selectors/mode_selector";
import SeasonSelector from "../leaderboards_components/season_selector";
import { useTranslation } from "react-i18next";
import { buildEndpointWithQueryParams, getBaseApiUrl } from "../utils";
import { getCache, setCache } from "../utils/cache_utils";
import { getSeasonName } from "../utils/season_utils";

const ARCHIVE_COLUMN_VISIBILITY = {
  rank: true,
  weapon: true,
  splashtag: true,
  badges: false,
  xpower: true,
};

const parseCachedSeason = () => {
  const cached = getCache("legacy.selectedSeason");
  if (cached == null || cached === "") {
    return null;
  }

  const parsed = Number.parseInt(cached, 10);
  return Number.isFinite(parsed) ? parsed : null;
};

const toPlayersArray = (data) => {
  if (!data?.players) {
    return [];
  }

  return Object.keys(data.players).reduce((acc, key) => {
    data.players[key].forEach((value, index) => {
      if (!acc[index]) acc[index] = {};
      acc[index][key] = value;
    });
    return acc;
  }, []);
};

const fetchArchiveLeaderboard = async (endpoint, signal) => {
  const response = await fetch(endpoint, { signal });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      payload?.detail || `Request failed with status ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload;
};

const LegacyLeaderboards = () => {
  const { t } = useTranslation("main_page");
  const { t: gameT } = useTranslation("game");
  const [searchQuery, setSearchQuery] = useState(
    getCache("legacy.searchQuery") || ""
  );
  const [currentPage, setCurrentPage] = useState(
    parseInt(getCache("legacy.currentPage"), 10) || 1
  );
  const [selectedRegion, setSelectedRegion] = useState(
    getCache("legacy.selectedRegion") || "Tentatek"
  );
  const [selectedMode, setSelectedMode] = useState(
    getCache("legacy.selectedMode") || "Splat Zones"
  );
  const [selectedSeason, setSelectedSeason] = useState(parseCachedSeason);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const itemsPerPage = 100;

  const formatSeasonLabel = useCallback(
    (season) => `Season ${season} · ${getSeasonName(season, gameT)}`,
    [gameT]
  );

  const endpoint = useMemo(() => {
    const params = {
      mode: selectedMode,
      region: selectedRegion,
    };
    if (selectedSeason !== null) {
      params.season = selectedSeason;
    }
    return buildEndpointWithQueryParams(
      getBaseApiUrl(),
      "/api/leaderboard/archive",
      params
    );
  }, [selectedMode, selectedRegion, selectedSeason]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    setIsLoading(true);
    setError(null);

    fetchArchiveLeaderboard(endpoint, controller.signal)
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch((fetchError) => {
        if (cancelled || fetchError.name === "AbortError") {
          return;
        }
        setData(null);
        setError(fetchError);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [endpoint]);

  useEffect(() => {
    if (data?.season_number == null) {
      return;
    }

    if (
      selectedSeason == null ||
      (data.available_seasons?.length > 0 &&
        !data.available_seasons.includes(selectedSeason))
    ) {
      setSelectedSeason(data.season_number);
    }
  }, [data?.available_seasons, data?.season_number, selectedSeason]);

  useEffect(() => {
    const titleSeason = data?.season_number ?? selectedSeason;
    document.title =
      titleSeason != null
        ? `splat.top - ${formatSeasonLabel(titleSeason)} Archive`
        : "splat.top - Season Archive";
  }, [data?.season_number, formatSeasonLabel, selectedSeason]);

  useEffect(() => {
    setCache("legacy.searchQuery", searchQuery, 60);
    setCache("legacy.currentPage", currentPage.toString(), 300);
    setCache("legacy.selectedRegion", selectedRegion, 60 * 60 * 24);
    setCache("legacy.selectedMode", selectedMode, 60 * 60 * 24);
    if (selectedSeason !== null) {
      setCache("legacy.selectedSeason", selectedSeason.toString(), 60 * 60 * 24);
    }
  }, [
    currentPage,
    searchQuery,
    selectedMode,
    selectedRegion,
    selectedSeason,
  ]);

  const players = useMemo(() => toPlayersArray(data), [data]);
  const filteredPlayers = useMemo(
    () =>
      players.filter((player) =>
        player.splashtag.toLowerCase().includes(searchQuery.toLowerCase())
      ),
    [players, searchQuery]
  );

  const displayedSeason = selectedSeason ?? data?.season_number;
  const availableSeasons = data?.available_seasons ?? [];
  const seasonSelectorOptions =
    availableSeasons.length > 0 ? availableSeasons : null;
  const seasonSelectorDisabled =
    !isLoading && availableSeasons.length === 0;
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredPlayers.slice(indexOfFirstItem, indexOfLastItem);

  const updateSearchQuery = (value) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  const updateRegion = (region) => {
    setSelectedRegion(region);
    setCurrentPage(1);
  };

  const updateMode = (mode) => {
    setSelectedMode(mode);
    setCurrentPage(1);
  };

  const updateSeason = (season) => {
    setSelectedSeason(season);
    setCurrentPage(1);
  };

  const paginate = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="container mx-auto px-4 py-8 bg-gray-900 text-white min-h-screen sm:px-2 lg:px-8">
      <h1 className="text-3xl font-bold mb-4 text-center sm:text-2xl">
        Season Archive
      </h1>
      <p className="mx-auto mb-6 max-w-3xl text-center text-gray-300">
        Final Top 500 standings from completed seasons.
      </p>

      <div className="grid grid-cols-1 gap-4 mb-4 sm:grid-cols-3">
        <div className="flex flex-col items-center">
          <RegionSelector
            selectedRegion={selectedRegion}
            setSelectedRegion={updateRegion}
          />
        </div>
        <div className="flex flex-col items-center">
          <ModeSelector
            selectedMode={selectedMode}
            setSelectedMode={updateMode}
          />
        </div>
        <div className="mb-4 w-full sm:w-auto">
          <h2 className="text-xl font-bold mb-2 text-center">
            {t("column_season_number_title")}
          </h2>
          <div className="flex justify-center">
            <SeasonSelector
              selectedSeason={displayedSeason}
              setSelectedSeason={updateSeason}
              availableSeasons={seasonSelectorOptions}
              allowClear={false}
              disabled={seasonSelectorDisabled}
              emptyLabel={isLoading ? t("loading") : t("no_data")}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {displayedSeason != null && (
        <p className="mb-4 text-center text-sm text-gray-400">
          {formatSeasonLabel(displayedSeason)}
        </p>
      )}

      <Pagination
        totalItems={filteredPlayers.length}
        itemsPerPage={itemsPerPage}
        currentPage={currentPage}
        onPageChange={paginate}
        isTopOfPage={true}
      />

      <input
        type="text"
        placeholder={t("search_placeholder")}
        value={searchQuery}
        onChange={(event) => updateSearchQuery(event.target.value)}
        className="border border-gray-700 bg-gray-800 rounded-md px-4 py-2 mb-4 w-full focus:outline-hidden focus:ring-2 focus:ring-purple"
      />

      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="text-center py-4">{t("loading")}</div>
        ) : error ? (
          <div className="text-red-500 text-center py-4">{error.message}</div>
        ) : currentItems.length > 0 ? (
          <PlayerTable
            players={currentItems}
            columnVisibility={ARCHIVE_COLUMN_VISIBILITY}
          />
        ) : (
          <div className="text-center py-4 text-gray-300">{t("no_data")}</div>
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

export default LegacyLeaderboards;
