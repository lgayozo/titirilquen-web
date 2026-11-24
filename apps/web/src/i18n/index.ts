import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import enCommon from "./locales/en/common.json";
import enSimulator from "./locales/en/simulator.json";
import esCommon from "./locales/es/common.json";
import esSimulator from "./locales/es/simulator.json";

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "es",
    supportedLngs: ["es", "en"],
    defaultNS: "common",
    ns: ["common", "simulator"],
    interpolation: { escapeValue: false },
    resources: {
      es: { common: esCommon, simulator: esSimulator },
      en: { common: enCommon, simulator: enSimulator },
    },
    detection: {
      order: ["querystring", "localStorage", "navigator"],
      lookupQuerystring: "lang",
      caches: ["localStorage"],
    },
  });

// El lang del documento gobierna la silabación (hyphens: auto) de la prosa
// justificada: sincronizarlo al cargar y en cada cambio de idioma.
i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});
if (i18n.resolvedLanguage) {
  document.documentElement.lang = i18n.resolvedLanguage;
}

export default i18n;
