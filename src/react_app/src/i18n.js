import i18n from "i18next";
import { initReactI18next } from "react-i18next";

// Import translation files
import mainPageEN from "./locales/en/main_page.json";

const resources = {
  en: {
    main_page: mainPageEN,
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  ns: ["main_page"],
  defaultNS: "main_page",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
