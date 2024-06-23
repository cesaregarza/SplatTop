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

const useWeaponLeaderboardData = (
  selectedRegion,
  selectedMode,
  weaponId,
  additionalWeaponId,
  weaponReferenceData
) => {
  const apiUrl = getBaseApiUrl();
  const pathUrl = `/api/weapon_leaderboard/${weaponId}`;
  const queryParams = {
    mode: selectedMode,
    region: selectedRegion,
  };

  if (additionalWeaponId !== null) {
    queryParams.additional_weapon_id = additionalWeaponId;
  }

  const endpoint = buildEndpointWithQueryParams(apiUrl, pathUrl, queryParams);

  const { data, error, isLoading } = useFetchWithCache(endpoint);


  const players = useMemo(() => {
    if (!data) return [];
    const playersArray = Object.keys(data.players).reduce((acc, key) => {
      data.players[key].forEach((value, index) => {
        if (!acc[index]) acc[index] = {};
        acc[index][key] = value;
      });
      return acc;
    }, []);

    const additionalWeaponImage =
      data.additional_weapon_image === null ||
      data.additional_weapon_image === undefined
        ? getImageFromId(additionalWeaponId, weaponReferenceData)
        : data.additional_weapon_image;

    playersArray.forEach((player) => {
      player.weapon_image =
        player.weapon_id === weaponId
          ? data.weapon_image
          : additionalWeaponImage;
    });

    playersArray.sort((a, b) => b.max_x_power - a.max_x_power);
    playersArray.forEach((player, index) => {
      player.rank = index + 1;
    });

    return playersArray;
  }, [data, weaponId, additionalWeaponId, weaponReferenceData]);

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
  const [currentPage, setCurrentPage] = useState(
    () => parseInt(getCache("currentPage")) || 1
  );
  const itemsPerPage = 100;

  useEffect(() => {
    document.title = `splat.top - ${selectedRegion} ${selectedMode}`;
    setCache("selectedRegion", selectedRegion);
    setCache("selectedMode", selectedMode);
    setCache("weaponId", weaponId.toString());
    setCache("additionalWeaponId", additionalWeaponId?.toString());
    setCache("currentPage", currentPage.toString());
  }, [selectedRegion, selectedMode, weaponId, additionalWeaponId, currentPage]);

  const { players, error, isLoading } = useWeaponLeaderboardData(
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    weaponReferenceData
  );

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = players.slice(indexOfFirstItem, indexOfLastItem);

  const paginate = useCallback((pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
      <h1 className="text-3xl font-bold mb-4 text-center">
        {t("weapon_title")}
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
      <div className="flex flex-col sm:flex-row justify-between mb-4">
        <Suspense fallback={<div>{t("loading")}</div>}>
          {weaponReferenceDataById && weaponTranslations && (
            <>
              <WeaponSelector
                onWeaponSelect={setWeaponId}
                weaponReferenceData={weaponReferenceDataById}
                weaponTranslations={weaponTranslations[pl("data_lang_key")]}
                initialWeaponId={weaponId}
              />
              <WeaponSelector
                onWeaponSelect={setAdditionalWeaponId}
                weaponReferenceData={weaponReferenceDataById}
                weaponTranslations={weaponTranslations[pl("data_lang_key")]}
                initialWeaponId={additionalWeaponId}
              />
            </>
          )}
        </Suspense>
      </div>
      <Suspense fallback={<div>{t("loading")}</div>}>
        <Pagination
          totalItems={players.length}
          itemsPerPage={itemsPerPage}
          currentPage={currentPage}
          onPageChange={paginate}
          isTopOfPage={true}
        />
      </Suspense>
      <Suspense fallback={<div>{t("loading")}</div>}>
        {isLoading ? (
          <div className="text-center py-4">
            <Loading text={t("loading")} />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center py-4">{error.message}</div>
        ) : (
          <WeaponLeaderboardTable players={currentItems} />
        )}
      </Suspense>
      <Suspense fallback={<div>{t("loading")}</div>}>
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
