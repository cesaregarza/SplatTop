import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";

import Loading from "./misc_components/loading";
import useFetchWithCache from "./top500_components/fetch_with_cache";
import Pagination from "./top500_components/pagination";
import {
  buildEndpointWithQueryParams,
  getBaseApiUrl,
} from "./utils";
import {
  deleteCache,
  getCache,
  setCache,
} from "./utils/cache_utils";
import {
  WeaponAndTranslationProvider,
  useWeaponAndTranslation,
} from "./utils/weaponAndTranslation";
import { modeKeyMap } from "./constants";
import {
  createTranslator,
  getImageFromId,
} from "./player_components/weapon_helper_functions";

const WeaponLeaderboardTable = React.lazy(() =>
  import("./leaderboards_components/weapon_leaderboard_table")
);
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
  const pathUrl = `/api/weapon-leaderboard/${weaponId}`;
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
  dedupePlayers = false,
  selectedSeason
) => {
  if (!data) {
    return [];
  }

  const playersArray = Object.keys(data.players).reduce((acc, key) => {
    data.players[key].forEach((value, index) => {
      if (!acc[index]) {
        acc[index] = {};
      }
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

  const filteredPlayers =
    selectedSeason !== null
      ? playersArray.filter((player) => player.season_number === selectedSeason)
      : playersArray;

  filteredPlayers.sort((a, b) => b.max_x_power - a.max_x_power);

  let processedPlayers = filteredPlayers;
  if (dedupePlayers) {
    const seenPlayerIds = new Set();
    processedPlayers = filteredPlayers.filter((player) => {
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
        dedupePlayers,
        selectedSeason
      ),
    [
      data,
      weaponId,
      additionalWeaponId,
      weaponReferenceData,
      weaponSetKey,
      finalResults,
      dedupePlayers,
      selectedSeason,
    ]
  );

  return { players, error, isLoading };
};

const getDefaultCompareWeaponId = (weaponId, weaponReferenceData) => {
  if (!weaponReferenceData) {
    return null;
  }

  const fallbackId = Object.keys(weaponReferenceData)
    .map((value) => parseInt(value, 10))
    .filter((value) => !Number.isNaN(value) && value !== weaponId)
    .sort((a, b) => a - b)[0];

  return fallbackId ?? null;
};

const TopWeaponsContent = () => {
  const { t } = useTranslation("weapon_leaderboard");
  const { t: playerT } = useTranslation("player");
  const {
    weaponReferenceData,
    weaponTranslations,
    isLoading: isWeaponDataLoading,
    error: weaponDataError,
  } = useWeaponAndTranslation();

  const [selectedRegion, setSelectedRegion] = useState(
    () => getCache("weapons.selectedRegion") || "Tentatek"
  );
  const [selectedMode, setSelectedMode] = useState(
    () => getCache("weapons.selectedMode") || "Splat Zones"
  );
  const [weaponId, setWeaponId] = useState(() => {
    const cachedWeaponId = getCache("weapons.weaponId");
    return cachedWeaponId !== null ? parseInt(cachedWeaponId, 10) : 40;
  });
  const [additionalWeaponId, setAdditionalWeaponId] = useState(() => {
    const cachedWeaponId = getCache("weapons.additionalWeaponId");
    return cachedWeaponId !== null ? parseInt(cachedWeaponId, 10) : null;
  });
  const [threshold, setThreshold] = useState(
    () => parseInt(getCache("weapons.threshold"), 10) || 0
  );
  const [currentPage, setCurrentPage] = useState(
    () => parseInt(getCache("weapons.currentPage"), 10) || 1
  );
  const [finalResults, setFinalResults] = useState(
    () => getCache("weapons.finalResults") === "true"
  );
  const [dedupePlayers, setDedupePlayers] = useState(
    () => getCache("weapons.dedupePlayers") === "true"
  );
  const [selectedSeason, setSelectedSeason] = useState(() => {
    const cachedSeason = getCache("weapons.selectedSeason");
    return cachedSeason !== null ? parseInt(cachedSeason, 10) : null;
  });
  const itemsPerPage = 100;
  const hasInitializedFilters = useRef(false);

  const localizedWeaponTranslations =
    weaponTranslations?.[playerT("data_lang_key")] ?? null;

  const weaponTranslator = useMemo(() => {
    if (!weaponReferenceData || !localizedWeaponTranslations) {
      return null;
    }

    return createTranslator(
      weaponReferenceData,
      localizedWeaponTranslations
    );
  }, [weaponReferenceData, localizedWeaponTranslations]);

  const mainWeaponLabel =
    weaponTranslator?.translateWeaponId?.(weaponId) ?? t("weapon_title");
  const additionalWeaponLabel =
    additionalWeaponId !== null && weaponTranslator?.translateWeaponId
      ? weaponTranslator.translateWeaponId(additionalWeaponId)
      : null;
  const compareEnabled = additionalWeaponId !== null;

  useEffect(() => {
    if (!hasInitializedFilters.current) {
      hasInitializedFilters.current = true;
      return;
    }

    setCurrentPage(1);
  }, [
    selectedRegion,
    selectedMode,
    weaponId,
    additionalWeaponId,
    threshold,
    finalResults,
    dedupePlayers,
    selectedSeason,
  ]);

  useEffect(() => {
    const pageTitle =
      compareEnabled && additionalWeaponLabel
        ? `${mainWeaponLabel} vs ${additionalWeaponLabel}`
        : mainWeaponLabel;
    document.title = `splat.top - ${pageTitle}`;

    setCache("weapons.selectedRegion", selectedRegion);
    setCache("weapons.selectedMode", selectedMode);
    setCache("weapons.weaponId", weaponId.toString());
    if (additionalWeaponId !== null) {
      setCache(
        "weapons.additionalWeaponId",
        additionalWeaponId.toString()
      );
    } else {
      deleteCache("weapons.additionalWeaponId");
    }
    setCache("weapons.threshold", threshold.toString());
    setCache("weapons.currentPage", currentPage.toString());
    setCache("weapons.finalResults", finalResults.toString());
    setCache("weapons.dedupePlayers", dedupePlayers.toString());
    if (selectedSeason !== null) {
      setCache("weapons.selectedSeason", selectedSeason.toString());
    } else {
      deleteCache("weapons.selectedSeason");
    }
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
    compareEnabled,
    mainWeaponLabel,
    additionalWeaponLabel,
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
  const leaderboardErrorStatus = error?.status ?? error?.response?.status;
  const leaderboardErrorMessage =
    leaderboardErrorStatus === 503 ? t("errors.503") : error?.message;

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = useMemo(
    () => players.slice(indexOfFirstItem, indexOfLastItem),
    [players, indexOfFirstItem, indexOfLastItem]
  );

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

  const toggleCompare = useCallback(() => {
    setAdditionalWeaponId((prev) => {
      if (prev !== null) {
        return null;
      }

      return getDefaultCompareWeaponId(weaponId, weaponReferenceData);
    });
  }, [weaponId, weaponReferenceData]);

  const displayStart = players.length === 0 ? 0 : indexOfFirstItem + 1;
  const displayEnd = Math.min(indexOfLastItem, players.length);
  const selectedModeLabel = t(modeKeyMap[selectedMode], {
    ns: "game",
    defaultValue: selectedMode,
  });
  const selectedMetricLabel = finalResults
    ? t("final_x_power")
    : t("peak_x_power");
  const headerMetadata = t("header.meta")
    .replace("%region%", selectedRegion)
    .replace("%mode%", selectedModeLabel)
    .replace("%metric%", selectedMetricLabel)
    .replace("%threshold%", (threshold / 10).toFixed(1));
  const resultsSummary = t("results.summary")
    .replace("%start%", displayStart)
    .replace("%end%", displayEnd)
    .replace("%total%", players.length);
  const pageTitle =
    compareEnabled && additionalWeaponLabel
      ? `${mainWeaponLabel} ${t("header.compare_separator")} ${additionalWeaponLabel}`
      : mainWeaponLabel;

  if (isWeaponDataLoading) {
    return <Loading text={t("loading")} />;
  }

  if (weaponDataError) {
    return (
      <div className="py-4 text-center text-red-500">
        {weaponDataError.message}
      </div>
    );
  }

  return (
    <div className="container mx-auto min-h-screen bg-gray-900 px-4 py-6 text-white sm:px-2 lg:px-8">
      <header className="mb-4 border-b border-gray-800/90 pb-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.28em] text-gray-400">
          {t("header.kicker")}
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight sm:text-2xl">
          {pageTitle}
        </h1>
        <p className="mt-2 text-sm text-gray-300">{headerMetadata}</p>
      </header>

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
          dedupePlayers={dedupePlayers}
          toggleDedupePlayers={toggleDedupePlayers}
          selectedSeason={selectedSeason}
          setSelectedSeason={setSelectedSeason}
          compareEnabled={compareEnabled}
          toggleCompare={toggleCompare}
          localizedWeaponTranslations={localizedWeaponTranslations}
          weaponReferenceData={weaponReferenceData}
        />
      </Suspense>

      <section className="mt-4 overflow-hidden rounded-lg border border-gray-800 bg-gray-950/55">
        <div className="flex flex-col gap-3 border-b border-gray-800 bg-gray-950/80 px-4 py-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">
              {t("results.title")}
            </h2>
            <p className="mt-1 text-sm text-gray-400">{resultsSummary}</p>
          </div>
          <Pagination
            totalItems={players.length}
            itemsPerPage={itemsPerPage}
            currentPage={currentPage}
            onPageChange={paginate}
            isTopOfPage={true}
            compact={true}
            align="right"
            className="mb-0 mt-0"
          />
        </div>

        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="py-8 text-center">
              <Loading text={t("loading")} />
            </div>
          ) : error ? (
            <div className="py-8 text-center text-red-500">
              {leaderboardErrorMessage}
            </div>
          ) : (
            <Suspense fallback={<div>{t("loading")}</div>}>
              <WeaponLeaderboardTable
                players={currentItems}
                isFinal={finalResults}
                showWeaponColumn={compareEnabled}
              />
            </Suspense>
          )}
        </div>
      </section>
    </div>
  );
};

const TopWeapons = () => (
  <WeaponAndTranslationProvider>
    <TopWeaponsContent />
  </WeaponAndTranslationProvider>
);

export default TopWeapons;
