import { useEffect } from "react";
import { NavLink, Outlet, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import fcfmLogo from "@/assets/fcfm.png";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ScenarioToolbar } from "@/components/ScenarioToolbar";
import { ThemeSwitcher } from "@/components/ThemeSwitcher";
import { cn } from "@/lib/cn";
import { configFromUrlParam } from "@/lib/serialization";
import { useSimulationStore } from "@/store/simulationStore";

interface NavItem {
  to: string;
  key: string;
  end?: boolean;
}

const navItems: readonly NavItem[] = [
  { to: "/", key: "nav.tutorial", end: true },
  { to: "/sandbox", key: "nav.sandbox" },
  { to: "/land-use", key: "nav.land_use" },
  { to: "/compare", key: "nav.compare" },
];

export function RootLayout() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const replaceConfig = useSimulationStore((s) => s.replaceConfig);

  useEffect(() => {
    const stateParam = searchParams.get("s");
    if (!stateParam) return;
    try {
      const cfg = configFromUrlParam(stateParam);
      replaceConfig(cfg);
      searchParams.delete("s");
      setSearchParams(searchParams, { replace: true });
    } catch {
      // ignore malformed state
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-full flex-col">
      <a href="#main-content" className="skip-link">
        {t("skip_to_main")}
      </a>
      <header
        className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950"
        role="banner"
      >
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-6 px-4 py-3">
          <div className="flex min-w-0 items-center gap-6">
            <div className="flex shrink-0 items-center gap-3">
              <img
                src={fcfmLogo}
                alt="Facultad de Ciencias Físicas y Matemáticas · Universidad de Chile"
                className="h-9 w-auto shrink-0"
              />
              <div className="hidden border-l border-slate-300 pl-3 dark:border-slate-700 md:block">
                <h1 className="whitespace-nowrap text-base font-semibold tracking-tight">
                  {t("app_name")}
                </h1>
                <p className="whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                  {t("app_tagline")}
                </p>
              </div>
            </div>
            <nav
              aria-label={t("nav.label")}
              className="flex shrink-0 items-center gap-1"
            >
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    cn(
                      "whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                        : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                    )
                  }
                >
                  {t(item.key)}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <ScenarioToolbar />
            <ThemeSwitcher />
            <LanguageSwitcher />
          </div>
        </div>
      </header>

      <main id="main-content" className="flex-1 overflow-auto" tabIndex={-1}>
        <div className="mx-auto max-w-7xl px-4 py-6">
          <Outlet />
        </div>
      </main>

      <footer
        role="contentinfo"
        className="border-t border-slate-200 py-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400"
      >
        <div className="mx-auto max-w-7xl px-4">
          {t("footer.authors")} · {t("footer.license")}
        </div>
      </footer>
    </div>
  );
}
