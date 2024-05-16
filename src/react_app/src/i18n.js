import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import mainPageEN from "./locales/en/main_page.json";
import faqEn from "./locales/en/faq.json";

const resources = {
  en: {
    main_page: mainPageEN,
    faq: faqEn,
  },
};

i18n.use(initReactI18next).init({
  resources,
  fallbackLng: "en",
  defaultNS: "main_page",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
