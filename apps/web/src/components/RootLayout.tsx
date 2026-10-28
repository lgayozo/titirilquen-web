import { useEffect } from "react";
import {
  NavLink,
  Outlet,
  useLocation,
  useSearchParams,
} from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  BookOpen,
  Building2,
  ChartNoAxesColumn,
  GitCompareArrows,
  Info,
  Repeat,
  SlidersHorizontal,
  TrainFront,
  type LucideIcon,
} from "lucide-react";

import fcfmLogo from "@/assets/fcfm.png";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ScenarioToolbar } from "@/components/ScenarioToolbar";
import { pyodideEngine } from "@/lib/pyodide-engine";
import { ThemeSwitcher } from "@/components/ThemeSwitcher";
import { cn } from "@/lib/cn";
import { scenarioFromUrlParam } from "@/lib/serialization";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

interface NavItem {
  to: string;
  key: string;
  icon: LucideIcon;
  end?: boolean;
}

const navItems: readonly NavItem[] = [
  { to: "/", key: "nav.tutorial", icon: BookOpen, end: true },
  // Calibración antes que los módulos: el modelo de comportamiento del hogar
  // (betas, valor del tiempo, λ) es común a Uso de suelo y Transporte.
  { to: "/calibration", key: "nav.calibration", icon: SlidersHorizontal },
  // Uso de suelo va PRIMERO: define las características de la ciudad (forma +
  // estratos + densidad) que alimentan al módulo de transporte (Sandbox).
  { to: "/land-use", key: "nav.land_use", icon: Building2 },
  { to: "/sandbox", key: "nav.sandbox", icon: TrainFront },
  { to: "/coupled", key: "nav.coupled", icon: Repeat },
  { to: "/compare", key: "nav.compare", icon: GitCompareArrows },
  { to: "/about", key: "nav.about", icon: Info },
];

/** La sección activa, para el título de la barra de la página. El tutorial
 *  vive en `/` y en `/tutorial/:slug`. */
function seccionActiva(pathname: string): NavItem {
  return (
    navItems.find((item) => item.to !== "/" && pathname.startsWith(item.to)) ??
    navItems[0]!
  );
}

export function RootLayout() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const replaceConfig = useSimulationStore((s) => s.replaceConfig);
  const { pathname } = useLocation();
  const setLandUseConfig = useLandUseStore((s) => s.setConfig);
  const setCoupledOuterMaxIter = useLandUseStore(
    (s) => s.setCoupledOuterMaxIter,
  );

  useEffect(() => {
    const stateParam = searchParams.get("s");
    if (!stateParam) return;
    try {
      const scenario = scenarioFromUrlParam(stateParam);
      replaceConfig(scenario.config);
      if (scenario.land_use) setLandUseConfig(() => scenario.land_use!);
      if (scenario.coupled)
        setCoupledOuterMaxIter(scenario.coupled.outer_max_iter);
      searchParams.delete("s");
      setSearchParams(searchParams, { replace: true });
    } catch {
      // ignore malformed state
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // F-03: precarga del worker de Pyodide al montar la app, para que el
  // estudiante no pague los ~10-20 s de boot DENTRO de su primera corrida.
  // Con retardo para no competir con el primer render; errores silenciosos
  // (sin red el boot fallará igual al simular, y ahí sí se muestra).
  useEffect(() => {
    const timer = setTimeout(() => {
      void pyodideEngine.init().catch(() => {});
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="shell">
      <a href="#main-content" className="skip-link">
        {t("skip_to_main")}
      </a>

      {/* Menú lateral persistente: logo institucional, marca, páginas, y al
          pie tema e idioma. */}
      <header className="appnav" role="banner">
        <img
          src={fcfmLogo}
          className="appnav-logo"
          alt="Facultad de Ciencias Físicas y Matemáticas · Universidad de Chile"
        />
        <div className="appnav-brand">
          <ChartNoAxesColumn className="appnav-icon" aria-hidden />
          <span className="brand-block">
            <span className="brand">{t("app_name")}</span>
            <span className="brand-sub">{t("app_tagline")}</span>
          </span>
        </div>
        <nav className="appnav-links" aria-label={t("nav.label")}>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                title={t(item.key)}
                className={({ isActive }) =>
                  cn("appnav-link", isActive && "active")
                }
              >
                <Icon className="appnav-icon" aria-hidden />
                <span className="appnav-label">{t(item.key)}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="appnav-foot">
          <ThemeSwitcher />
          <LanguageSwitcher />
        </div>
      </header>

      <div className="shell-main">
        <div className="appbar">
          <span className="appbar-title">{t(seccionActiva(pathname).key)}</span>
          <div className="spacer" />
          <span className="tools-label">{t("scenario_label")}</span>
          <ScenarioToolbar />
        </div>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 overflow-y-auto overflow-x-hidden"
        >
          <Outlet />
        </main>

        <footer className="foot" role="contentinfo">
          {t("footer.authors")} · {t("footer.license")}
        </footer>
      </div>
    </div>
  );
}
