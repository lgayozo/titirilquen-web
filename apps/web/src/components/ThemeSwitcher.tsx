import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { BookOpen, Moon, Newspaper } from "lucide-react";

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

  // Un solo botón que cicla paper → journal → dark: tres targets menos en el
  // topbar. El título anuncia el tema actual y el siguiente.
  const idx = Math.max(
    0,
    OPTIONS.findIndex((o) => o.value === theme),
  );
  const current = OPTIONS[idx]!;
  const next = OPTIONS[(idx + 1) % OPTIONS.length]!;
  const Icon = current.icon;

  return (
    <div className="seg">
      <button
        type="button"
        onClick={() => setTheme(next.value)}
        title={`${t(current.labelKey)} → ${t(next.labelKey)}`}
        aria-label={t("theme.label")}
      >
        <Icon className="h-3 w-3" aria-hidden />
        <span className="sr-only">{t(current.labelKey)}</span>
      </button>
    </div>
  );
}
