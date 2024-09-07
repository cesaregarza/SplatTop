import React, {
  useEffect,
  useState,
  Suspense,
  useCallback,
  useMemo,
} from "react";
import Loading from "./misc_components/loading";
import { getBaseApiUrl, buildEndpointWithQueryParams } from "./utils";
import { useTranslation } from "react-i18next";
import useFetchWithCache from "./top500_components/fetch_with_cache";
import { setCache, getCache } from "./utils/cache_utils";
import {
  WeaponAndTranslationProvider,
  useWeaponAndTranslation,
} from "./utils/weaponAndTranslation";
import { getImageFromId } from "./player_components/weapon_helper_functions";

const WeaponLeaderboardTable = React.lazy(() =>
  import("./leaderboards_components/weapon_leaderboard_table")
);
const Pagination = React.lazy(() => import("./top500_components/pagination"));
const WeaponLeaderboardControls = React.lazy(() =>
  import("./leaderboards_components/weapon_controls")
);

const useFetchWeaponLeaderboardData = (
  selectedRegion,
  selectedMode,
  weaponId,
  additionalWeaponId,
  threshold,
  finalResults = false,
  selectedSeason
) => {
  const apiUrl = getBaseApiUrl();
  const pathUrl = `/api/weapon_leaderboard/${weaponId}`;
  const queryParams = {
    mode: selectedMode,
    region: selectedRegion,
    min_threshold: threshold,
    final_results: finalResults,
    season: selectedSeason,
  };

  if (additionalWeaponId !== null) {
    queryParams.additional_weapon_id = additionalWeaponId;
  }

  const endpoint = buildEndpointWithQueryParams(apiUrl, pathUrl, queryParams);

  const weaponSetKey = useMemo(() => {
    const weaponSet = new Set([weaponId, additionalWeaponId]);
    return Array.from(weaponSet).sort().join(",");
  }, [weaponId, additionalWeaponId]);

  return useFetchWithCache(endpoint, weaponSetKey);
};

const processWeaponLeaderboardData = (
  data,
  weaponId,
  additionalWeaponId,
  weaponReferenceData,
  finalResults = false,
  dedupePlayers = false
) => {
  if (!data) return [];
  const playersArray = Object.keys(data.players).reduce((acc, key) => {
    data.players[key].forEach((value, index) => {
      if (!acc[index]) acc[index] = {};
      acc[index][key] = value;
    });
    return acc;
  }, []);

  const additionalWeaponImage =
    additionalWeaponId !== null &&
    (data.additional_weapon_image === null ||
      data.additional_weapon_image === undefined)
      ? getImageFromId(additionalWeaponId, weaponReferenceData)
      : data.additional_weapon_image;

  playersArray.forEach((player) => {
    player.weapon_image =
      player.weapon_id === weaponId ? data.weapon_image : additionalWeaponImage;
    if (finalResults) {
      player.season_number -= 1;
    }
  });

  playersArray.sort((a, b) => b.max_x_power - a.max_x_power);

  let processedPlayers = playersArray;
  if (dedupePlayers) {
    const seenPlayerIds = new Set();
    processedPlayers = playersArray.filter((player) => {
      if (seenPlayerIds.has(player.player_id)) {
        return false;
      }
      seenPlayerIds.add(player.player_id);
      return true;
    });
  }

  processedPlayers.forEach((player, index) => {
    player.rank = index + 1;
  });

  return processedPlayers.slice(0, 500);
};

const useWeaponLeaderboardData = (
  selectedRegion,
  selectedMode,
  weaponId,
  additionalWeaponId,
  weaponReferenceData,
  threshold,
  finalResults = false,
  dedupePlayers = false,
  selectedSeason
) => {
  const weaponSetKey = useMemo(() => {
    const weaponSet = new Set([weaponId, additionalWeaponId]);
    return Array.from(weaponSet).sort().join(",");
  }, [weaponId, additionalWeaponId]);

  const { data, error, isLoading } = useFetchWeaponLeaderboardData(
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    threshold,
    finalResults,
    selectedSeason
  );

  const players = useMemo(
    () =>
      processWeaponLeaderboardData(
        data,
        weaponId,
        additionalWeaponId,
        weaponReferenceData,
        finalResults,
        dedupePlayers
      ),
    [data, weaponSetKey, weaponReferenceData, finalResults, dedupePlayers] // eslint-disable-line react-hooks/exhaustive-deps
  );

  return { players, error, isLoading };
};

const TopWeaponsContent = () => {
  const { t } = useTranslation("weapon_leaderboard");
  const {
    weaponReferenceData,
    weaponTranslations,
    isLoading: isWeaponDataLoading,
    error: weaponDataError,
  } = useWeaponAndTranslation();

  const [selectedRegion, setSelectedRegion] = useState(() => {
    return getCache("weapons.selectedRegion") || "Tentatek";
  });
  const [selectedMode, setSelectedMode] = useState(() => {
    return getCache("weapons.selectedMode") || "Splat Zones";
  });
  const [weaponId, setWeaponId] = useState(() => {
    const cachedWeaponId = getCache("weapons.weaponId");
    return cachedWeaponId !== null ? parseInt(cachedWeaponId) : 40;
  });
  const [additionalWeaponId, setAdditionalWeaponId] = useState(() => {
    const cachedWeaponId = getCache("weapons.additionalWeaponId");
    return cachedWeaponId !== null ? parseInt(cachedWeaponId) : null;
  });
  const [threshold, setThreshold] = useState(() => {
    return parseInt(getCache("weapons.threshold")) || 0;
  });
  const [currentPage, setCurrentPage] = useState(() => {
    return parseInt(getCache("weapons.currentPage")) || 1;
  });
  const [finalResults, setFinalResults] = useState(() => {
    return getCache("weapons.finalResults") === "true";
  });
  const [dedupePlayers, setDedupePlayers] = useState(() => {
    return getCache("weapons.dedupePlayers") === "true";
  });
  const [selectedSeason, setSelectedSeason] = useState(() => {
    const cachedSeason = getCache("weapons.selectedSeason");
    return cachedSeason !== null ? parseInt(cachedSeason) : null;
  });
  const itemsPerPage = 100;

  useEffect(() => {
    document.title = `splat.top - ${selectedRegion} ${selectedMode}`;
    setCache("weapons.selectedRegion", selectedRegion);
    setCache("weapons.selectedMode", selectedMode);
    setCache("weapons.weaponId", weaponId.toString());
    setCache("weapons.additionalWeaponId", additionalWeaponId?.toString());
    setCache("weapons.threshold", threshold.toString());
    setCache("weapons.currentPage", currentPage.toString());
    setCache("weapons.finalResults", finalResults.toString());
    setCache("weapons.dedupePlayers", dedupePlayers.toString());
    setCache("weapons.selectedSeason", selectedSeason?.toString());
  }, [
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    threshold,
    currentPage,
    finalResults,
    dedupePlayers,
    selectedSeason,
  ]);

  const { players, error, isLoading } = useWeaponLeaderboardData(
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    weaponReferenceData,
    threshold,
    finalResults,
    dedupePlayers,
    selectedSeason
  );

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = useMemo(() => {
    return players.slice(indexOfFirstItem, indexOfLastItem);
  }, [players, indexOfFirstItem, indexOfLastItem]);

  const paginate = useCallback((pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const toggleFinalResults = useCallback(() => {
    setFinalResults((prev) => !prev);
  }, []);

  const toggleDedupePlayers = useCallback(() => {
    setDedupePlayers((prev) => !prev);
  }, []);

  const handleSwapWeapons = () => {
    const tempWeaponId = weaponId;
    setWeaponId(additionalWeaponId);
    setAdditionalWeaponId(tempWeaponId);
  };

  if (isWeaponDataLoading) {
    return <Loading text={t("loading")} />;
  }

  if (weaponDataError) {
    return (
      <div className="text-red-500 text-center py-4">
        {weaponDataError.message}
      </div>
    );
  }

  return (
    <>
      <h1 className="text-3xl font-bold mb-6 text-center text-purple-300">
        {t("weapon_title")}
      </h1>
      <Suspense fallback={<Loading text={t("loading")} />}>
        <WeaponLeaderboardControls
          selectedRegion={selectedRegion}
          setSelectedRegion={setSelectedRegion}
          selectedMode={selectedMode}
          setSelectedMode={setSelectedMode}
          weaponId={weaponId}
          setWeaponId={setWeaponId}
          additionalWeaponId={additionalWeaponId}
          setAdditionalWeaponId={setAdditionalWeaponId}
          threshold={threshold}
          setThreshold={setThreshold}
          finalResults={finalResults}
          toggleFinalResults={toggleFinalResults}
          weaponReferenceData={weaponReferenceData}
          weaponTranslations={weaponTranslations}
          handleSwapWeapons={handleSwapWeapons}
          dedupePlayers={dedupePlayers}
          toggleDedupePlayers={toggleDedupePlayers}
          selectedSeason={selectedSeason}
          setSelectedSeason={setSelectedSeason}
        />
        <Pagination
          totalItems={players.length}
          itemsPerPage={itemsPerPage}
          currentPage={currentPage}
          onPageChange={paginate}
          isTopOfPage={true}
        />
        {isLoading ? (
          <div className="text-center py-4">
            <Loading text={t("loading")} />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center py-4">
            {error.response.status === 503 ? t("errors.503") : error.message}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <WeaponLeaderboardTable
              players={currentItems}
              isFinal={finalResults}
            />
          </div>
        )}
        <Pagination
          totalItems={players.length}
          itemsPerPage={itemsPerPage}
          currentPage={currentPage}
          onPageChange={paginate}
          isTopOfPage={false}
        />
      </Suspense>
    </>
  );
};

const TopWeapons = () => {
  return (
    <WeaponAndTranslationProvider>
      <div className="container mx-auto px-4 py-8 bg-gray-900 text-white min-h-screen">
        <TopWeaponsContent />
      </div>
    </WeaponAndTranslationProvider>
  );
};

export default TopWeapons;
