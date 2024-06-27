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
  finalResults = false
) => {
  const apiUrl = getBaseApiUrl();
  const pathUrl = `/api/weapon_leaderboard/${weaponId}`;
  const queryParams = {
    mode: selectedMode,
    region: selectedRegion,
    min_threshold: threshold,
    final_results: finalResults,
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
  finalResults = false
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
  playersArray.forEach((player, index) => {
    player.rank = index + 1;
  });

  return playersArray.slice(0, 500);
};

const useWeaponLeaderboardData = (
  selectedRegion,
  selectedMode,
  weaponId,
  additionalWeaponId,
  weaponReferenceData,
  threshold,
  finalResults = false
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
    finalResults
  );

  const players = useMemo(
    () =>
      processWeaponLeaderboardData(
        data,
        weaponId,
        additionalWeaponId,
        weaponReferenceData,
        finalResults
      ),
    [data, weaponSetKey, weaponReferenceData, finalResults] // eslint-disable-line react-hooks/exhaustive-deps
  );

  return { players, error, isLoading };
};

const TopWeaponsContent = () => {
  const { t } = useTranslation("main_page");
  const {
    weaponReferenceData,
    weaponTranslations,
    isLoading: isWeaponDataLoading,
    error: weaponDataError,
  } = useWeaponAndTranslation();

  const [selectedRegion, setSelectedRegion] = useState(
    () => getCache("selectedRegion") || "Tentatek"
  );
  const [selectedMode, setSelectedMode] = useState(
    () => getCache("selectedMode") || "Splat Zones"
  );
  const [weaponId, setWeaponId] = useState(
    () => parseInt(getCache("weaponId")) || 40
  );
  const [additionalWeaponId, setAdditionalWeaponId] = useState(() => {
    const cached = getCache("additionalWeaponId");
    return cached ? parseInt(cached) : null;
  });
  const [threshold, setThreshold] = useState(
    () => parseInt(getCache("threshold")) || 0
  );
  const [currentPage, setCurrentPage] = useState(
    () => parseInt(getCache("currentPage")) || 1
  );
  const [finalResults, setFinalResults] = useState(false);
  const itemsPerPage = 100;

  useEffect(() => {
    document.title = `splat.top - ${selectedRegion} ${selectedMode}`;
    setCache("selectedRegion", selectedRegion);
    setCache("selectedMode", selectedMode);
    setCache("weaponId", weaponId.toString());
    setCache("additionalWeaponId", additionalWeaponId?.toString());
    setCache("threshold", threshold.toString());
    setCache("currentPage", currentPage.toString());
  }, [
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    threshold,
    currentPage,
  ]);

  const { players, error, isLoading } = useWeaponLeaderboardData(
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    weaponReferenceData,
    threshold,
    finalResults
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
          <div className="text-red-500 text-center py-4">{error.message}</div>
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
