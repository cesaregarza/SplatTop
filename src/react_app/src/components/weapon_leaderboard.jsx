import React, {
  useEffect,
  useState,
  Suspense,
  useMemo,
  useCallback,
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
const RegionSelector = React.lazy(() =>
  import("./top500_components/selectors/region_selector")
);
const ModeSelector = React.lazy(() =>
  import("./top500_components/selectors/mode_selector")
);
const WeaponSelector = React.lazy(() =>
  import("./leaderboards_components/weapon_selector")
);
const ThresholdSelector = React.lazy(() =>
  import("./leaderboards_components/threshold_selector")
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

  return useFetchWithCache(endpoint);
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

  return playersArray;
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
  const { data, error, isLoading } = useFetchWeaponLeaderboardData(
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    threshold,
    finalResults
  );

  const players = processWeaponLeaderboardData(
    data,
    weaponId,
    additionalWeaponId,
    weaponReferenceData
  );

  return { players, error, isLoading };
};

const TopWeaponsContent = () => {
  const { t } = useTranslation("main_page");
  const { t: pl } = useTranslation("player");
  const {
    weaponTranslations,
    weaponReferenceData,
    isLoading: isWeaponDataLoading,
    error: weaponDataError,
  } = useWeaponAndTranslation();

  const weaponReferenceDataById = useMemo(() => {
    if (!weaponReferenceData) return {};
    return Object.entries(weaponReferenceData).reduce((acc, [key, value]) => {
      if (key === value.reference_id.toString()) {
        acc[key] = value;
      }
      return acc;
    }, {});
  }, [weaponReferenceData]);

  const [selectedRegion, setSelectedRegion] = useState(() => {
    const cached = getCache("selectedRegion");
    return cached || "Tentatek";
  });
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
  const currentItems = players.slice(indexOfFirstItem, indexOfLastItem);

  const paginate = useCallback((pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const toggleFinalResults = useCallback(() => {
    setFinalResults((prev) => !prev);
  }, []);

  if (isWeaponDataLoading) {
    return (
      <div className="text-center py-4">
        <Loading text={t("loading")} />
      </div>
    );
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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col items-center">
            <RegionSelector
              selectedRegion={selectedRegion}
              setSelectedRegion={setSelectedRegion}
            />
          </div>
          <div className="flex flex-col items-center">
            <ModeSelector
              selectedMode={selectedMode}
              setSelectedMode={setSelectedMode}
            />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {weaponReferenceDataById && weaponTranslations && (
            <>
              <div className="flex flex-col items-center">
                <span className="mb-2 text-center text-lg font-semibold text-purple-400">
                  {t("weapon_select_main")}
                </span>
                <WeaponSelector
                  onWeaponSelect={setWeaponId}
                  weaponReferenceData={weaponReferenceDataById}
                  weaponTranslations={weaponTranslations[pl("data_lang_key")]}
                  initialWeaponId={weaponId}
                />
              </div>
              <div className="flex flex-col items-center">
                <span className="mb-2 text-center text-lg font-semibold text-purple-400">
                  {t("weapon_select_alt")}
                </span>
                <WeaponSelector
                  onWeaponSelect={setAdditionalWeaponId}
                  weaponReferenceData={weaponReferenceDataById}
                  weaponTranslations={weaponTranslations[pl("data_lang_key")]}
                  initialWeaponId={additionalWeaponId}
                  allowNull={true}
                />
              </div>
            </>
          )}
        </div>
        <ThresholdSelector threshold={threshold} setThreshold={setThreshold} />
        <div className="flex flex-col justify-center items-center mb-6">
          <label
            htmlFor="toggleFinalResults"
            className="inline-flex items-center cursor-pointer flex-col"
          >
            <div className="flex items-center">
              <span
                className={`text-sm font-medium mr-2 ${
                  !finalResults ? "highlighted-option" : ""
                }`}
              >
                {t("weapon_leaderboard.peak_x_power")}
              </span>
              <div className="relative" title="Change the scale type">
                <input
                  type="checkbox"
                  id="toggleFinalResults"
                  className="sr-only peer"
                  checked={finalResults}
                  onChange={toggleFinalResults}
                />
                <div
                  className={`w-11 h-6 rounded-full peer peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5 ${
                    finalResults ? "bg-purple" : "bg-gray-600"
                  }`}
                ></div>
              </div>
              <span
                className={`text-sm font-medium ml-2 ${
                  finalResults ? "highlighted-option" : ""
                }`}
              >
                {t("weapon_leaderboard.final_x_power")}
              </span>
            </div>
          </label>
        </div>
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
          <WeaponLeaderboardTable
            players={currentItems}
            isFinal={finalResults}
          />
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
