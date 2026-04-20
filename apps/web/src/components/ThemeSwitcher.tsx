import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Monitor, Moon, Sun } from "lucide-react";

import { cn } from "@/lib/cn";
import type { Theme } from "@/lib/theme";
import { watchSystemTheme } from "@/lib/theme";
import { useThemeStore } from "@/store/themeStore";

const OPTIONS: Array<{ value: Theme; icon: typeof Sun; tk: string }> = [
  { value: "light", icon: Sun, tk: "theme.light" },
  { value: "system", icon: Monitor, tk: "theme.system" },
  { value: "dark", icon: Moon, tk: "theme.dark" },
];

export function ThemeSwitcher() {
  const { t } = useTranslation("common");
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const syncSystem = useThemeStore((s) => s.syncSystem);

  // Re-sincroniza si el usuario cambia la preferencia del SO mientras theme="system".
  useEffect(() => {
    const cancel = watchSystemTheme(() => {
      if (useThemeStore.getState().theme === "system") syncSystem();
    });
    return cancel;
  }, [syncSystem]);

  return (
    <div
      role="radiogroup"
      aria-label={t("theme.label")}
      className="flex items-center gap-0.5 rounded-full border border-slate-200 bg-white p-0.5 dark:border-slate-700 dark:bg-slate-900"
    >
      {OPTIONS.map(({ value, icon: Icon, tk }) => {
        const active = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => setTheme(value)}
            title={t(tk)}
            aria-label={t(tk)}
            className={cn(
              "rounded-full p-1 transition-colors",
              active
                ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            )}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
          </button>
        );
      })}
    </div>
  );
}
