import React, { useState, useEffect, Suspense } from "react";
import axios from "axios";
import Loading from "../../misc_components/loading";
import { getBaseApiUrl } from "../../utils";
import { useTranslation } from "react-i18next";
import LorenzGraph from "./graph";

const LorenzTab = () => {
  const { t } = useTranslation("analytics");
  const { t: p } = useTranslation("player");
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weaponTranslations, setWeaponTranslations] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      document.title = t("document_title");
      const apiUrl = getBaseApiUrl();
      const endpoint = `${apiUrl}/api/lorenz`;
      const translationEndpoint = `${apiUrl}/api/game_translation`;

      try {
        const response = await axios.get(endpoint);
        setData(response.data);

        const translationsResponse = await axios.get(translationEndpoint);
        setWeaponTranslations(translationsResponse.data);
      } catch (error) {
        setError(error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col min-h-screen">
      <main className="flex-grow container mx-auto px-4 py-8 bg-gray-900 text-white overflow-auto">
        {isLoading ? (
          <div className="flex justify-center items-center h-full">
            <Loading text={t("load_page")} />
          </div>
        ) : error ? (
          <div className="text-red-500 text-center">{error.message}</div>
        ) : (
          <Suspense fallback={<Loading text={t("load_component")} />}>
            {data && data.lorenz ? (
              <>
                <LorenzGraph
                  data={data}
                  weaponTranslations={weaponTranslations[p("data_lang_key")]}
                />
                {/* <LorenzChartController
                /> */}
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

export default LorenzTab;
