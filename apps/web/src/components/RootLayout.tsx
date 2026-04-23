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
  { to: "/coupled", key: "nav.coupled" },
  { to: "/compare", key: "nav.compare" },
  { to: "/about", key: "nav.about" },
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

      <nav className="topbar" role="banner">
        <div className="logo">
          <img
            src={fcfmLogo}
            alt="Facultad de Ciencias Físicas y Matemáticas · Universidad de Chile"
          />
          <span>{t("app_name")}</span>
        </div>
        <div className="sub">{t("app_tagline")}</div>
        <div className="spacer" />
        <div className="nav" aria-label={t("nav.label")}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => cn(isActive && "active")}
            >
              {t(item.key)}
            </NavLink>
          ))}
        </div>
        <ScenarioToolbar />
        <ThemeSwitcher />
        <LanguageSwitcher />
      </nav>

      <main id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto overflow-x-hidden">
        <Outlet />
      </main>

      <footer className="foot" role="contentinfo">
        {t("footer.authors")} · {t("footer.web_by")} · {t("footer.license")}
      </footer>
    </div>
  );
}
