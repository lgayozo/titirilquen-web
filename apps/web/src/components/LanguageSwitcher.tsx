import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

const LANGS = ["es", "en"] as const;

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const current = i18n.resolvedLanguage ?? "es";

  return (
    <div className="flex items-center gap-1 text-xs" aria-label={t("language.label")}>
      {LANGS.map((lng) => (
        <button
          key={lng}
          type="button"
          onClick={() => void i18n.changeLanguage(lng)}
          className={cn(
            "rounded px-2 py-1 transition-colors",
            current === lng
              ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
              : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
          )}
          aria-pressed={current === lng}
        >
          {lng.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
