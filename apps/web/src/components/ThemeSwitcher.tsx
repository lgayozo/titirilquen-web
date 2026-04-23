import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { BookOpen, Moon, Newspaper } from "lucide-react";

import { cn } from "@/lib/cn";
import { watchSystemTheme, type Theme } from "@/lib/theme";
import { useThemeStore } from "@/store/themeStore";

type Option = { value: Theme; icon: typeof Moon; labelKey: string };

const OPTIONS: ReadonlyArray<Option> = [
  { value: "paper", icon: Newspaper, labelKey: "theme.paper" },
  { value: "journal", icon: BookOpen, labelKey: "theme.journal" },
  { value: "dark", icon: Moon, labelKey: "theme.dark" },
];

export function ThemeSwitcher() {
  const { t } = useTranslation("common");
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const syncSystem = useThemeStore((s) => s.syncSystem);

  useEffect(() => {
    const cancel = watchSystemTheme(() => {
      if (useThemeStore.getState().theme === "system") syncSystem();
    });
    return cancel;
  }, [syncSystem]);

  return (
    <div role="radiogroup" aria-label={t("theme.label")} className="seg">
      {OPTIONS.map(({ value, icon: Icon, labelKey }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={theme === value}
          onClick={() => setTheme(value)}
          title={t(labelKey)}
          className={cn(theme === value && "active")}
        >
          <Icon className="h-3 w-3" aria-hidden />
          <span className="sr-only">{t(labelKey)}</span>
        </button>
      ))}
    </div>
  );
}
