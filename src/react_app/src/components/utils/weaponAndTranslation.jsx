import React, { createContext, useContext, useState, useEffect } from "react";
import { getBaseApiUrl } from "../utils";
import { setCache, getCache, deleteCache } from "./cache_utils";
import { fetchJson } from "../../http";

const WeaponAndTranslationContext = createContext();

export const useWeaponAndTranslation = () =>
  useContext(WeaponAndTranslationContext);

export const WeaponAndTranslationProvider = ({ children }) => {
  const [weaponTranslations, setWeaponTranslations] = useState(null);
  const [weaponReferenceData, setWeaponReferenceData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      const apiUrl = getBaseApiUrl();
      const translationEndpoint = `${apiUrl}/api/game-translation`;
      const weaponInfoEndpoint = `${apiUrl}/api/weapon-info`;

      try {
        // Fetch translations
        let translationsData = getCache("weaponTranslations");
        if (!translationsData) {
          translationsData = await fetchJson(translationEndpoint);
          setCache("weaponTranslations", translationsData);
        }
        setWeaponTranslations(translationsData);

        // Fetch weapon reference data
        let referenceData = getCache("weaponReferenceData");
        if (!referenceData) {
          referenceData = await fetchJson(weaponInfoEndpoint);
          setCache("weaponReferenceData", referenceData);
        }
        setWeaponReferenceData(referenceData);
      } catch (error) {
        setError(error);
        console.error("Error fetching weapon and translation data:", error);
        // If there's an error, we might want to delete the cache to ensure
        // fresh data on next load
        deleteCache("weaponTranslations");
        deleteCache("weaponReferenceData");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const value = {
    weaponTranslations,
    weaponReferenceData,
    isLoading,
    error,
  };

  return (
    <WeaponAndTranslationContext.Provider value={value}>
      {children}
    </WeaponAndTranslationContext.Provider>
  );
};
