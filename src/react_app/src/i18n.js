import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import Backend from "i18next-http-backend";
import LanguageDetector from "i18next-browser-languagedetector";

// DON'T FORGET TO ADD THE LANGUAGE HERE AND IN src/components/supported_languages.js
i18n
  .use(LanguageDetector)
  .use(Backend)
  .use(initReactI18next)
  .init({
    supportedLngs: ["USen","EUen","USes"],
    backend: {
      loadPath: "../locales/{{lng}}/{{ns}}.json",
    },
    fallbackLng: "USen",
    defaultNS: "main_page",
    ns: ["main_page", "faq", "game", "navigation", "player"],
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
