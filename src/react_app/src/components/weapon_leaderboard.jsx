import React, { useEffect, useState, Suspense } from "react";
import Loading from "./misc_components/loading";
import { getBaseApiUrl, buildEndpointWithQueryParams } from "./utils";
import { useTranslation } from "react-i18next";
import useFetchWithCache from "./top500_components/fetch_with_cache";
import { setCache, getCache } from "./utils/cache_utils";
import {
  WeaponAndTranslationProvider,
  useWeaponAndTranslation,
} from "./utils/weaponAndTranslation";

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

const TopWeaponsContent = () => {
  const { t } = useTranslation("main_page");
  const { t: pl } = useTranslation("player");
  const {
    weaponTranslations,
    weaponReferenceData,
    isLoading: isWeaponDataLoading,
    error: weaponDataError,
  } = useWeaponAndTranslation();

  const weaponReferenceDataById = React.useMemo(() => {
    if (!weaponReferenceData) return {};
    return Object.entries(weaponReferenceData).reduce((acc, [key, value]) => {
      if (key === value.reference_id.toString()) {
        acc[key] = value;
      }
      return acc;
    }, {});
  }, [weaponReferenceData]);

  const [selectedRegion, setSelectedRegion] = useState(
    getCache("selectedRegion") || "Tentatek"
  );
  const [selectedMode, setSelectedMode] = useState(
    getCache("selectedMode") || "Splat Zones"
  );
  const [weaponId, setWeaponId] = useState(40);
  const [additionalWeaponId, setAdditionalWeaponId] = useState(null);
  const [currentPage, setCurrentPage] = useState(
    parseInt(getCache("currentPage", 300), 10) || 1
  );
  const itemsPerPage = 100;

  useEffect(() => {
    document.title = `splat.top - ${selectedRegion} ${selectedMode}`;
    setCache("selectedRegion", selectedRegion);
    setCache("selectedMode", selectedMode);
    setCache("currentPage", currentPage.toString(), 300);
  }, [selectedRegion, selectedMode, currentPage]);

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

  const players = React.useMemo(() => {
    if (!data) return [];
    return Object.keys(data.players).reduce((acc, key) => {
      data.players[key].forEach((value, index) => {
        if (!acc[index]) acc[index] = {};
        acc[index][key] = value;
      });
      return acc;
    }, []);
  }, [data]);

  React.useEffect(() => {
    if (data && players.length > 0) {
      players.forEach((player) => {
        player.weapon_image =
          player.weapon_id === weaponId
            ? data.weapon_image
            : data.additional_weapon_image;
      });

      players.sort((a, b) => b.max_x_power - a.max_x_power);
      players.forEach((player, index) => {
        player.rank = index + 1;
      });
    }
  }, [data, players, weaponId]);

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = players.slice(indexOfFirstItem, indexOfLastItem);

  const paginate = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (isLoading || isWeaponDataLoading) {
    return (
      <div className="text-center py-4">
        <Loading text={t("loading")} />
      </div>
    );
  }

  if (error || weaponDataError) {
    return (
      <div className="text-red-500 text-center py-4">
        {(error || weaponDataError).message}
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
              />
              <WeaponSelector
                onWeaponSelect={setAdditionalWeaponId}
                weaponReferenceData={weaponReferenceDataById}
                weaponTranslations={weaponTranslations[pl("data_lang_key")]}
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
        <WeaponLeaderboardTable players={currentItems} />
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
