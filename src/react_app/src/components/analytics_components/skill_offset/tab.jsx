import React, { useState, useEffect, Suspense } from "react";
import Loading from "../../misc_components/loading";
import { getBaseApiUrl } from "../../utils";
import { useTranslation } from "react-i18next";
import SkillOffsetGraph from "./graph";
import SkillOffsetChartController from "./chart_controller";
import { fetchJson } from "../../../http";

const ALL_SLICE_KEY = "all";

const buildSkillOffsetEndpoint = (apiUrl, selectedMode, selectedRegion) => {
  const params = new URLSearchParams();

  if (selectedMode !== ALL_SLICE_KEY) {
    params.set("mode", selectedMode);
  }

  if (selectedRegion !== ALL_SLICE_KEY) {
    params.set("region", selectedRegion);
  }

  const queryString = params.toString();
  return queryString
    ? `${apiUrl}/api/skill-offset?${queryString}`
    : `${apiUrl}/api/skill-offset`;
};

const getSkillOffsetSampleSize = (selectedMode, selectedRegion) => {
  if (
    selectedMode === ALL_SLICE_KEY &&
    selectedRegion === ALL_SLICE_KEY
  ) {
    return 4000;
  }

  if (selectedMode === ALL_SLICE_KEY) {
    return 2000;
  }

  if (selectedRegion === ALL_SLICE_KEY) {
    return 1000;
  }

  return 500;
};

const SkillOffsetTab = () => {
  const { t } = useTranslation("analytics");
  const { t: p } = useTranslation("player");
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weaponTranslations, setWeaponTranslations] = useState(null);
  const [logarithmic, setLogarithmic] = useState(false);
  const [selectedMode, setSelectedMode] = useState(ALL_SLICE_KEY);
  const [selectedRegion, setSelectedRegion] = useState(ALL_SLICE_KEY);
  const sampleSize = getSkillOffsetSampleSize(
    selectedMode,
    selectedRegion
  );

  useEffect(() => {
    document.title = t("document_title");
  }, [t]);

  useEffect(() => {
    let ignore = false;

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      const apiUrl = getBaseApiUrl();
      const endpoint = buildSkillOffsetEndpoint(
        apiUrl,
        selectedMode,
        selectedRegion
      );
      const translationEndpoint = `${apiUrl}/api/game-translation`;

      try {
        const [skillOffsetData, translationsData] = await Promise.all([
          fetchJson(endpoint),
          fetchJson(translationEndpoint),
        ]);
        if (!ignore) {
          setData(skillOffsetData);
          setWeaponTranslations(translationsData);
        }
      } catch (error) {
        if (!ignore) {
          setError(error);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      ignore = true;
    };
  }, [selectedMode, selectedRegion]);

  const toggleLogarithmic = () => {
    setLogarithmic((prevLogarithmic) => !prevLogarithmic);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <main className="grow container mx-auto px-4 py-8 bg-gray-900 text-white overflow-auto">
        {isLoading ? (
          <div className="flex justify-center items-center h-full">
            <Loading text={t("load_page")} />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center">{error.message}</div>
        ) : (
          <Suspense fallback={<Loading text={t("load_component")} />}>
            {data && data.length > 0 ? (
              <>
                <SkillOffsetGraph
                  data={data}
                  weaponTranslations={weaponTranslations[p("data_lang_key")]}
                  logarithmic={logarithmic}
                  sampleSize={sampleSize}
                />
                <SkillOffsetChartController
                  logarithmic={logarithmic}
                  toggleLogarithmic={toggleLogarithmic}
                  selectedMode={selectedMode}
                  setSelectedMode={setSelectedMode}
                  selectedRegion={selectedRegion}
                  setSelectedRegion={setSelectedRegion}
                  sampleSize={sampleSize}
                />
              </>
            ) : (
              <div className="text-center">{t("no_data")}</div>
            )}
          </Suspense>
        )}
      </main>
    </div>
  );
};

export default SkillOffsetTab;
