import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

const LANGS = ["es", "en"] as const;

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const current = i18n.resolvedLanguage ?? "es";

  return (
    <div role="radiogroup" aria-label={t("language.label")} className="seg">
      {LANGS.map((lng) => (
        <button
          key={lng}
          type="button"
          role="radio"
          aria-checked={current === lng}
          onClick={() => void i18n.changeLanguage(lng)}
          className={cn(current === lng && "active")}
        >
          {lng.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
