import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { CityStrip } from "@/components/CityStrip";
import { CityBuilder } from "@/components/modules/CityBuilder";
import { EconomyBuilder } from "@/components/modules/EconomyBuilder";
import { SupplyBuilder } from "@/components/modules/SupplyBuilder";
import { RunStatus } from "@/components/RunStatus";
import { SimulationSkeleton } from "@/components/SimulationSkeleton";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { Panel } from "@/components/ui/Panel";
import { SidebarSection } from "@/components/ui/SidebarSection";
import { CityPreview } from "@/components/viz/CityPreview";
import { ConvergenceTrace } from "@/components/viz/ConvergenceTrace";
import { FlowProfile } from "@/components/viz/FlowProfile";
import { ModeShareBars, type AgentGroup } from "@/components/viz/ModeShareBars";
import { ModeShareByLocation } from "@/components/viz/ModeShareByLocation";
import { NetworkDiagram } from "@/components/viz/NetworkDiagram";
import { StatBars, type StatBar } from "@/components/viz/StatBars";
import { UtilityScatter } from "@/components/viz/UtilityScatter";
import { pyodideEngine } from "@/lib/pyodide-engine";
import type { Modo } from "@/lib/types";
import { isResultStale, useSimulationStore } from "@/store/simulationStore";

type HeatMode =
  | "auto"
  | "metro"
  | "bici"
  | "caminata"
  | "todos"
  | "espera"
  | "plano";

/** Opciones del toggle de la Figura 1, en orden. "plano" vuelve a la vista de
 *  infraestructura (CityPreview) sin perder los resultados. */
const VIEW_OPTIONS: readonly HeatMode[] = [
  "auto",
  "metro",
  "bici",
  "caminata",
  "todos",
  "espera",
  "plano",
];

/** Umbral de factibilidad por modo (min): sobre él el modo deja de ser
 *  elegible. Ver demand/utility.py — caminata > 30, bici > 45. */
const MODE_CUTOFF: Partial<Record<HeatMode, number>> = {
  caminata: 30,
  bici: 45,
};

export function SandboxPage() {
  const { t } = useTranslation("simulator");
  const { t: tCommon } = useTranslation("common");
  const config = useSimulationStore((s) => s.config);
  const running = useSimulationStore((s) => s.running);
  const stage = useSimulationStore((s) => s.stage);
  const progress = useSimulationStore((s) => s.progress);
  const result = useSimulationStore((s) => s.result);
  const liveIterations = useSimulationStore((s) => s.liveIterations);
  const error = useSimulationStore((s) => s.error);
  const setConfig = useSimulationStore((s) => s.setConfig);
  const startRun = useSimulationStore((s) => s.startRun);
  const finishRun = useSimulationStore((s) => s.finishRun);
  const failRun = useSimulationStore((s) => s.failRun);
  const pushIteration = useSimulationStore((s) => s.pushIteration);
  const reset = useSimulationStore((s) => s.reset);
  const configUsed = useSimulationStore((s) => s.configUsed);
  const cancelRun = useSimulationStore((s) => s.cancelRun);

  // Config de la corrida visible: el snapshot usado por el resultado, no la
  // viva — así las figuras no mezclan geometrías si el usuario mueve sliders.
  const cfgRes = configUsed ?? config;
  const stale = useMemo(
    () => isResultStale({ stage, config, configUsed }),
    [stage, config, configUsed],
  );

  const [heatMode, setHeatMode] = useState<HeatMode>("auto");

  const viewLabel = (m: HeatMode) =>
    m === "todos"
      ? t("sandbox.view_all")
      : m === "espera"
        ? t("sandbox.view_wait")
        : m === "plano"
          ? t("preview.tab")
          : t(`modes.${m}`);

  const lastIter = liveIterations.at(-1) ?? result?.iteraciones.at(-1);
  // Antes de la primera iteración no hay perfil de tiempos: el hero muestra el
  // "plano" (CityPreview) en vez de la cinta de tiempos (CityStrip). Con
  // resultados, la pestaña "plano" del toggle vuelve a esa misma vista.
  const hasData = lastIter != null;
  const showPreview = !hasData || heatMode === "plano";
  const cellKm = cfgRes.city.largo_ciudad_km / cfgRes.city.n_celdas;
  const cbdIdx = Math.floor(cfgRes.city.n_celdas / 2);
  const vCaminata = cfgRes.demand.globales.v_caminata || 4.8;
  const profile = lastIter
    ? lastIter.t_auto.map((t_auto, i) => ({
        t_auto,
        t_metro:
          lastIter.t_tren_viaje[i]! +
          lastIter.t_tren_acceso[i]! +
          lastIter.t_tren_espera[i]!,
        t_bici: lastIter.t_bici[i]!,
        // Caminata: tiempo puramente geométrico (sin congestión), mismo
        // criterio que demand/utility.py → dist/v_caminata · 60.
        t_caminata: ((Math.abs(cbdIdx - i) * cellKm) / vCaminata) * 60,
        // Espera del metro (escalonada por estación; centro ≈ 0).
        t_espera: lastIter.t_tren_espera[i]!,
      }))
    : undefined;

  const operatingRatios = {
    car:
      result && lastIter
        ? Math.max(...lastIter.demanda_auto) / result.capacidad_auto
        : null,
    bike: lastIter
      ? Math.max(...lastIter.demanda_bici) / cfgRes.supply.bike.capacidad_pista
      : null,
  };

  const abortRef = useRef<AbortController | null>(null);

  const handleRun = async () => {
    // Si el toggle quedó en "plano", volver a una vista de resultados para no
    // tapar la convergencia en vivo con la infraestructura estática.
    if (heatMode === "plano") setHeatMode("auto");
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    startRun(config.max_iter);
    try {
      const final = await pyodideEngine.simulateStream(
        config,
        (snap) => pushIteration(snap),
        ctrl.signal,
      );
      finishRun(final);
    } catch (e) {
      if (ctrl.signal.aborted) return; // cancelado por el usuario
      failRun(e instanceof Error ? e.message : String(e));
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    cancelRun();
  };

  const totalAgents = lastIter
    ? (Object.values(lastIter.modal_split) as number[]).reduce(
        (s, n) => s + n,
        0,
      )
    : 0;

  const kpis = useMemo<KPI[]>(() => {
    if (!result || !lastIter) {
      return [
        { label: t("kpi.trips"), value: "—" },
        { label: t("kpi.auto_pct"), value: "—" },
        { label: t("kpi.metro_pct"), value: "—" },
        { label: t("kpi.bici_pct"), value: "—" },
        { label: t("kpi.walk_pct"), value: "—" },
        { label: t("kpi.tele_pct"), value: "—" },
        { label: t("kpi.frequency"), value: "—" },
        { label: t("kpi.residual"), value: "—" },
        { label: t("kpi.co2"), value: "—" },
      ];
    }
    const modal = lastIter.modal_split;
    const total = (Object.values(modal) as number[]).reduce((s, n) => s + n, 0);
    const tot = total > 0 ? total : 1;
    const pct = (m: Modo) => `${(((modal[m] ?? 0) / tot) * 100).toFixed(1)}%`;
    const count = (m: Modo) =>
      t("kpi.trips_subline", { n: Math.round(modal[m] ?? 0).toLocaleString() });
    return [
      {
        label: t("kpi.trips"),
        value: Math.round(total - (modal.Teletrabajo ?? 0)).toLocaleString(),
      },
      {
        label: t("kpi.auto_pct"),
        value: pct("Auto"),
        color: "var(--auto)",
        delta: count("Auto"),
      },
      {
        label: t("kpi.metro_pct"),
        value: pct("Metro"),
        color: "var(--metro)",
        delta: count("Metro"),
      },
      {
        label: t("kpi.bici_pct"),
        value: pct("Bici"),
        color: "var(--bici)",
        delta: count("Bici"),
      },
      {
        label: t("kpi.walk_pct"),
        value: pct("Caminata"),
        color: "var(--walk)",
        delta: count("Caminata"),
      },
      {
        label: t("kpi.tele_pct"),
        value: pct("Teletrabajo"),
        color: "var(--tele)",
        delta: t("kpi.tele_subline", {
          n: Math.round(modal.Teletrabajo ?? 0).toLocaleString(),
        }),
      },
      {
        label: t("kpi.frequency"),
        value: lastIter.frecuencia_metro.toFixed(1),
        unit: "tph",
      },
      {
        label: t("kpi.residual"),
        value:
          lastIter.residuo == null || !isFinite(lastIter.residuo)
            ? "—"
            : lastIter.residuo.toFixed(3),
        unit: "min",
      },
      {
        label: t("kpi.co2"),
        value:
          result.emisiones_total_kg >= 100
            ? Math.round(result.emisiones_total_kg).toLocaleString()
            : result.emisiones_total_kg.toFixed(1),
        unit: "kg/h",
        color: "var(--ink)",
        delta: t("kpi.co2_split", {
          auto: Math.round(result.emisiones_auto_kg).toLocaleString(),
          metro: Math.round(result.emisiones_metro_kg).toLocaleString(),
        }),
      },
    ];
  }, [result, lastIter, t]);

  const kpiCaption = useMemo(() => {
    if (!result || !lastIter) return null;
    const totalIters = result.iteraciones.length;
    const base = t("kpi.last_iteration", {
      n: lastIter.iter + 1,
      total: totalIters,
    });
    const status = result.converged ? t("kpi.converged") : t("kpi.maxiter");
    return `${base} · ${status}`;
  }, [result, lastIter, t]);

  // Grupos de agentes para las figuras de reparto por estrato y tenencia.
  const STRATUM_KEY = ["alto", "medio", "bajo"] as const;
  const stratumGroups = useMemo<AgentGroup[]>(() => {
    const agents = result?.agentes;
    if (!agents) return [];
    return [1, 2, 3].map((s) => ({
      label: t(`sandbox.stratum_${STRATUM_KEY[s - 1]}`),
      agents: agents.filter((a) => a.estrato === s),
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, t]);

  const carGroups = useMemo<AgentGroup[]>(() => {
    const agents = result?.agentes;
    if (!agents) return [];
    const groups: AgentGroup[] = [];
    for (const s of [1, 2, 3]) {
      const label = t(`sandbox.stratum_${STRATUM_KEY[s - 1]}`);
      groups.push({
        label,
        tag: t("sandbox.with_car"),
        agents: agents.filter((a) => a.estrato === s && a.tiene_auto),
      });
      groups.push({
        label,
        tag: t("sandbox.without_car"),
        agents: agents.filter((a) => a.estrato === s && !a.tiene_auto),
      });
    }
    return groups;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, t]);

  // Estadísticas agregadas: el tiempo de viaje no está por agente, así que se
  // reconstruye combinando el snapshot final (tiempos por celda y modo) con la
  // celda/modo de cada agente. Teletrabajo se excluye (no viaja).
  const avgStats = useMemo(() => {
    const agents = result?.agentes;
    if (!agents || !lastIter) return null;
    const MODE_C: Record<string, string> = {
      Auto: "var(--auto)",
      Metro: "var(--metro)",
      Bici: "var(--bici)",
      Caminata: "var(--walk)",
    };
    const STR_C: Record<number, string> = {
      1: "var(--s1)",
      2: "var(--s2)",
      3: "var(--s3)",
    };
    const timeOf = (a: (typeof agents)[number]): number | null => {
      const c = a.celda_origen;
      switch (a.modo_elegido) {
        case "Auto":
          return lastIter.t_auto[c] ?? 0;
        case "Bici":
          return lastIter.t_bici[c] ?? 0;
        case "Metro":
          return (
            (lastIter.t_tren_acceso[c] ?? 0) +
            (lastIter.t_tren_espera[c] ?? 0) +
            (lastIter.t_tren_viaje[c] ?? 0)
          );
        case "Caminata":
          return ((Math.abs(cbdIdx - c) * cellKm) / vCaminata) * 60;
        default:
          return null; // Teletrabajo / sin modo
      }
    };
    const modeAgg: Record<string, [number, number]> = {
      Auto: [0, 0],
      Metro: [0, 0],
      Bici: [0, 0],
      Caminata: [0, 0],
    };
    const strTime: Record<number, [number, number]> = {
      1: [0, 0],
      2: [0, 0],
      3: [0, 0],
    };
    const strUtil: Record<number, [number, number]> = {
      1: [0, 0],
      2: [0, 0],
      3: [0, 0],
    };
    for (const a of agents) {
      const tt = timeOf(a);
      if (tt != null) {
        const e = a.modo_elegido ? modeAgg[a.modo_elegido] : undefined;
        if (e) {
          e[0] += tt;
          e[1] += 1;
        }
        const st = strTime[a.estrato];
        if (st) {
          st[0] += tt;
          st[1] += 1;
        }
      }
      if (a.modo_elegido && a.modo_elegido !== "Teletrabajo") {
        const su = strUtil[a.estrato];
        if (su) {
          su[0] += a.utilidad_elegida;
          su[1] += 1;
        }
      }
    }
    const mean = (p: [number, number]) => (p[1] > 0 ? p[0] / p[1] : 0);
    const strLabel = (s: number) => t(`sandbox.stratum_${STRATUM_KEY[s - 1]}`);
    const timeByMode: StatBar[] = (
      ["Auto", "Metro", "Bici", "Caminata"] as const
    ).map((m) => ({
      label: t(`modes.${m.toLowerCase()}`),
      value: mean(modeAgg[m]!),
      color: MODE_C[m]!,
    }));
    const timeByStratum: StatBar[] = [1, 2, 3].map((s) => ({
      label: strLabel(s),
      value: mean(strTime[s]!),
      color: STR_C[s]!,
    }));
    const utilByStratum: StatBar[] = [1, 2, 3].map((s) => ({
      label: strLabel(s),
      value: mean(strUtil[s]!),
      color: STR_C[s]!,
    }));
    return { timeByMode, timeByStratum, utilByStratum };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, lastIter, t]);

  return (
    <div className="page">
      <aside className="sidebar">
        <CityBuilder config={config} onChange={setConfig} />
        <SupplyBuilder
          config={config}
          onChange={setConfig}
          operatingRatios={operatingRatios}
        />
        <EconomyBuilder config={config} onChange={setConfig} />

        <SidebarSection
          title={t("sections.equilibrium")}
          meta={`${config.max_iter} iter`}
          defaultOpen={false}
        >
          <label className="slider-row block">
            <div className="srow-top">
              <span className="srow-label">{t("equilibrium.max_iter")}</span>
              <span className="srow-val" aria-hidden>
                {config.max_iter}
              </span>
            </div>
            <input
              type="range"
              min={3}
              max={50}
              step={1}
              value={config.max_iter}
              onChange={(e) =>
                setConfig((c) => ({ ...c, max_iter: Number(e.target.value) }))
              }
              aria-label={t("equilibrium.max_iter")}
            />
          </label>

          <label className="slider-row block">
            <div className="srow-top">
              <span className="srow-label">{t("equilibrium.tolerance")}</span>
              <span className="srow-val" aria-hidden>
                {config.tolerance > 0
                  ? `${config.tolerance.toFixed(2)} min`
                  : t("equilibrium.tol_off")}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={config.tolerance}
              onChange={(e) =>
                setConfig((c) => ({ ...c, tolerance: Number(e.target.value) }))
              }
              aria-label={t("equilibrium.tolerance")}
            />
          </label>

          <div className="mt-2">
            <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
              {t("equilibrium.assignment")}
            </div>
            <div className="seg" style={{ width: "100%" }}>
              {(["montecarlo", "expected"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={config.assignment === m ? "active" : ""}
                  onClick={() => setConfig((c) => ({ ...c, assignment: m }))}
                  style={{ flex: 1 }}
                >
                  {m === "montecarlo"
                    ? t("equilibrium.assignment_mc")
                    : t("equilibrium.assignment_expected")}
                </button>
              ))}
            </div>
            <p className="mt-1 text-[11px] text-muted">
              {t(`equilibrium.assignment_hint_${config.assignment}`)}
            </p>
          </div>

          <div className="mt-3">
            <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
              {t("equilibrium.modos")}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(["Auto", "Metro", "Bici", "Caminata"] as const).map((m) => {
                const on = config.modos_habilitados.includes(m);
                const last = on && config.modos_habilitados.length === 1;
                return (
                  <button
                    key={m}
                    type="button"
                    disabled={last}
                    className={`chip-toggle${on ? " active" : ""}`}
                    onClick={() =>
                      setConfig((c) => ({
                        ...c,
                        modos_habilitados: on
                          ? c.modos_habilitados.filter((x) => x !== m)
                          : [...c.modos_habilitados, m],
                      }))
                    }
                    title={last ? t("equilibrium.modos_min") : undefined}
                  >
                    {t(`equilibrium.modo_${m.toLowerCase()}`)}
                  </button>
                );
              })}
            </div>
            <p className="mt-1 text-[11px] text-muted">
              {t("equilibrium.modos_hint")}
            </p>
          </div>
        </SidebarSection>

        {(stage === "done" || stage === "error") && (
          <button
            type="button"
            className="reset-btn"
            onClick={reset}
            title={tCommon("actions.new_run")}
          >
            {`↺ ${tCommon("actions.new_run")}`}
          </button>
        )}

        <button
          type="button"
          className="run-btn"
          disabled={running}
          onClick={handleRun}
        >
          {running
            ? `◜ ${t("equilibrium.iteration", {
                n: progress?.current ?? 0,
                total: progress?.total ?? 0,
              })}`
            : `▶ ${tCommon("actions.run")}`}
        </button>

        {running && (
          <button type="button" className="reset-btn" onClick={handleCancel}>
            {`✕ ${tCommon("actions.cancel")}`}
          </button>
        )}

        {error && (
          <div
            className="callout"
            style={{ borderLeftColor: "var(--metro)", marginTop: 12 }}
          >
            {error}
          </div>
        )}
      </aside>

      <section className="main">
        {stale && (
          <div className="stale-banner" role="status">
            <span>{t("stale.banner")}</span>
            <button type="button" onClick={() => void handleRun()}>
              {`▶ ${t("stale.rerun")}`}
            </button>
          </div>
        )}

        {/* HERO */}
        <div className="hero">
          <div className="hero-head">
            <h1 className="hero-title">{t("hero.title")}</h1>
            <div className="hero-sub">
              <span className="dot">●</span>{" "}
              {stage === "running" || stage === "booting"
                ? t("hero.status_running")
                : stage === "done"
                  ? t("hero.status_done")
                  : t("hero.status_ready")}
            </div>
          </div>

          <div className="ribbon-wrap">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
                {showPreview ? t("preview.heading") : t("sandbox.city_heading")}
              </span>
              {hasData ? (
                <div className="seg">
                  {VIEW_OPTIONS.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setHeatMode(m)}
                      className={heatMode === m ? "active" : ""}
                    >
                      {viewLabel(m)}
                    </button>
                  ))}
                </div>
              ) : (
                <span className="font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
                  {t("preview.meta")}
                </span>
              )}
            </div>

            {showPreview ? (
              <ExportableFigure
                name="plano-ciudad"
                title={t("preview.heading")}
                description={t("preview.export_desc")}
                exportSize={{ width: 1200, height: 360 }}
              >
                <CityPreview config={config} />
              </ExportableFigure>
            ) : (
              <ExportableFigure
                name={`ciudad-${heatMode}`}
                title={`${t("sandbox.city_heading")} — ${viewLabel(heatMode)}`}
                description={t("sandbox.city_figure_desc", {
                  length: cfgRes.city.largo_ciudad_km,
                  cells: cfgRes.city.n_celdas,
                  mode: viewLabel(heatMode),
                })}
                exportSize={{ width: 1200, height: 200 }}
              >
                <CityStrip
                  nCeldas={cfgRes.city.n_celdas}
                  largoKm={cfgRes.city.largo_ciudad_km}
                  pendientePct={cfgRes.city.pendiente_porcentaje}
                  modeProfile={profile}
                  heatMode={heatMode}
                  cutoffMin={MODE_CUTOFF[heatMode]}
                  cutoffLabel={
                    MODE_CUTOFF[heatMode] != null
                      ? t("sandbox.cutoff_label", {
                          min: MODE_CUTOFF[heatMode],
                        })
                      : undefined
                  }
                  estacionesKm={result?.estaciones_km ?? undefined}
                  shareEstratos={cfgRes.city.share_estratos}
                  iterationToken={lastIter?.iter ?? -1}
                />
              </ExportableFigure>
            )}

            <div className="ribbon-legend">
              {(
                [
                  { m: "auto", c: "var(--auto)" },
                  { m: "metro", c: "var(--metro)" },
                  { m: "bici", c: "var(--bici)" },
                  { m: "caminata", c: "var(--walk)" },
                ] as const
              ).map(({ m, c }) => (
                <span
                  key={m}
                  className="sw"
                  style={
                    {
                      "--c": c,
                      opacity:
                        heatMode === "todos" ||
                        heatMode === m ||
                        (heatMode === "espera" && m === "metro")
                          ? 1
                          : 0.4,
                    } as React.CSSProperties
                  }
                >
                  {t(`modes.${m}`)}
                </span>
              ))}
              <span style={{ marginLeft: "auto", textTransform: "none" }}>
                {t("hero.stats_line", {
                  total: totalAgents > 0 ? totalAgents.toLocaleString() : "—",
                  length: cfgRes.city.largo_ciudad_km,
                  stations: cfgRes.supply.train.num_estaciones,
                  lanes: cfgRes.supply.car.num_pistas,
                })}
              </span>
            </div>
          </div>
        </div>

        {/* KPIs */}
        {kpiCaption && <div className="kpi-caption">{kpiCaption}</div>}
        <KPIStrip items={kpis} />

        {/* Hint row — guía pedagógica */}
        <div className="hint-row">
          <div className="hint">
            <strong>{t("hints.demand_title")}</strong>
            {t("hints.demand_body")}
          </div>
          <div className="hint">
            <strong>{t("hints.supply_title")}</strong>
            {t("hints.supply_body")}
          </div>
          <div className="hint">
            <strong>{t("hints.equilibrium_title")}</strong>
            {t("hints.equilibrium_body")}
          </div>
        </div>

        {/* Estado de corrida (mantiene animaciones) */}
        {(stage === "booting" || stage === "running") && progress && (
          <div style={{ marginBottom: "var(--gap)" }}>
            <RunStatus
              current={progress.current}
              total={progress.total}
              lastIter={lastIter}
              stage={stage}
              engine="local"
            />
          </div>
        )}

        {(stage === "booting" ||
          (stage === "running" && liveIterations.length === 0)) && (
          <div style={{ marginBottom: "var(--gap)" }}>
            <SimulationSkeleton nCeldas={cfgRes.city.n_celdas} />
          </div>
        )}

        {/* Grid de paneles FIG. NN */}
        {liveIterations.length > 0 && (
          <div className="panel-grid">
            {lastIter && result && (
              <Panel
                n="00"
                title={t("network.title")}
                meta={t("panel_meta.modes_all")}
                cls="col-12"
              >
                <NetworkDiagram
                  snapshot={lastIter}
                  result={result}
                  config={config}
                />
              </Panel>
            )}

            <Panel
              n="01"
              title={t("equilibrium.converged")}
              meta="MSA"
              cls="col-12"
            >
              <ConvergenceTrace iterations={liveIterations} />
            </Panel>

            {lastIter &&
              result &&
              (() => {
                // Escala Y compartida: el máximo global entre los 3 modos.
                // Permite comparar la magnitud relativa visualmente sin engañar
                // con el auto-scale por panel.
                const globalMax = Math.max(
                  ...lastIter.demanda_auto,
                  ...lastIter.demanda_bici,
                  ...lastIter.demanda_metro,
                  ...lastIter.demanda_caminata,
                  1,
                );
                const flowPanels = [
                  {
                    n: "02",
                    mode: "auto",
                    flows: lastIter.demanda_auto,
                    color: "var(--auto)",
                    cap: `${Math.round(result.capacidad_auto)} veh/h corredor`,
                  },
                  {
                    n: "03",
                    mode: "bici",
                    flows: lastIter.demanda_bici,
                    color: "var(--bici)",
                    cap: `${cfgRes.supply.bike.capacidad_pista} bici/h`,
                  },
                  {
                    n: "04",
                    mode: "metro",
                    flows: lastIter.demanda_metro,
                    color: "var(--metro)",
                    cap: `${cfgRes.supply.train.capacidad_tren} pax/tren`,
                  },
                  {
                    n: "4b",
                    mode: "caminata",
                    flows: lastIter.demanda_caminata,
                    color: "var(--walk)",
                    cap: undefined as string | undefined,
                  },
                ] as const;
                return (
                  <>
                    {flowPanels.map((fp) => (
                      <Panel
                        key={fp.n}
                        n={fp.n}
                        title={t(`modes.${fp.mode}`)}
                        meta={t("sandbox.flow_per_cell", {
                          mode: t(`modes.${fp.mode}`),
                        })}
                        cls="col-6"
                      >
                        <ExportableFigure
                          name={`flujo-${fp.mode}`}
                          title={t("sandbox.flow_per_cell", {
                            mode: t(`modes.${fp.mode}`),
                          })}
                          exportSize={{ width: 600, height: 200 }}
                        >
                          <FlowProfile
                            flows={fp.flows}
                            largoKm={cfgRes.city.largo_ciudad_km}
                            color={fp.color}
                            yMax={globalMax}
                            capacityHint={fp.cap}
                          />
                        </ExportableFigure>
                      </Panel>
                    ))}
                  </>
                );
              })()}

            {result && result.emisiones_perfil_kg && (
              <Panel
                n="4c"
                title={t("sandbox.co2_profile")}
                meta={t("panel_meta.co2")}
                cls="col-12"
              >
                <ExportableFigure
                  name="co2-por-ubicacion"
                  title={t("sandbox.co2_profile")}
                  exportSize={{ width: 1000, height: 200 }}
                >
                  <FlowProfile
                    flows={result.emisiones_perfil_kg}
                    largoKm={cfgRes.city.largo_ciudad_km}
                    color="var(--accent)"
                    label="kg/h"
                    valueFmt={(v) => v.toFixed(1)}
                    height={130}
                  />
                </ExportableFigure>
              </Panel>
            )}

            {result && result.agentes.length > 0 && (
              <>
                <Panel
                  n="05"
                  title={t("sandbox.trips_by_stratum")}
                  meta={t("panel_meta.share_stratum")}
                  cls="col-6"
                >
                  <ExportableFigure
                    name="reparto-por-estrato"
                    title={t("sandbox.trips_by_stratum")}
                    exportSize={{ width: 700, height: 240 }}
                  >
                    <ModeShareBars groups={stratumGroups} />
                  </ExportableFigure>
                </Panel>

                <Panel
                  n="06"
                  title={t("sandbox.trips_by_car_ownership")}
                  meta={t("panel_meta.ownership_stratum")}
                  cls="col-6"
                >
                  <ExportableFigure
                    name="reparto-tenencia-auto"
                    title={t("sandbox.trips_by_car_ownership")}
                    exportSize={{ width: 700, height: 340 }}
                  >
                    <ModeShareBars groups={carGroups} />
                  </ExportableFigure>
                </Panel>

                <Panel
                  n="07"
                  title={t("sandbox.utility_scatter")}
                  meta={t("panel_meta.utility_position")}
                  cls="col-7"
                >
                  <ExportableFigure
                    name="dispersion-utilidades"
                    title={t("sandbox.utility_scatter")}
                    exportSize={{ width: 800, height: 280 }}
                  >
                    <UtilityScatter
                      agents={result.agentes}
                      nCeldas={cfgRes.city.n_celdas}
                      largoKm={cfgRes.city.largo_ciudad_km}
                    />
                  </ExportableFigure>
                </Panel>

                <Panel
                  n="08"
                  title={t("sandbox.mode_share_by_location")}
                  meta="stacked · 100%"
                  cls="col-5"
                >
                  <ExportableFigure
                    name="reparto-modal-por-ubicacion"
                    title={t("sandbox.mode_share_by_location")}
                    exportSize={{ width: 800, height: 280 }}
                  >
                    <ModeShareByLocation
                      agents={result.agentes}
                      nCeldas={cfgRes.city.n_celdas}
                      largoKm={cfgRes.city.largo_ciudad_km}
                    />
                  </ExportableFigure>
                </Panel>

                {avgStats && (
                  <>
                    <Panel
                      n="09"
                      title={t("sandbox.avg_time_by_mode")}
                      meta={t("panel_meta.avg_min")}
                      cls="col-4"
                    >
                      <ExportableFigure
                        name="tiempo-medio-por-modo"
                        title={t("sandbox.avg_time_by_mode")}
                        exportSize={{ width: 500, height: 240 }}
                      >
                        <StatBars bars={avgStats.timeByMode} unit="min" />
                      </ExportableFigure>
                    </Panel>

                    <Panel
                      n="10"
                      title={t("sandbox.avg_time_by_stratum")}
                      meta={t("panel_meta.avg_min")}
                      cls="col-4"
                    >
                      <ExportableFigure
                        name="tiempo-medio-por-estrato"
                        title={t("sandbox.avg_time_by_stratum")}
                        exportSize={{ width: 500, height: 240 }}
                      >
                        <StatBars bars={avgStats.timeByStratum} unit="min" />
                      </ExportableFigure>
                    </Panel>

                    <Panel
                      n="11"
                      title={t("sandbox.avg_utility_by_stratum")}
                      meta={t("panel_meta.avg_util")}
                      cls="col-4"
                    >
                      <ExportableFigure
                        name="utilidad-media-por-estrato"
                        title={t("sandbox.avg_utility_by_stratum")}
                        exportSize={{ width: 500, height: 240 }}
                      >
                        <StatBars bars={avgStats.utilByStratum} decimals={2} />
                      </ExportableFigure>
                    </Panel>
                  </>
                )}
              </>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
