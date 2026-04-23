import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { CityStrip } from "@/components/CityStrip";
import { CityBuilder } from "@/components/modules/CityBuilder";
import { DemandInspector } from "@/components/modules/DemandInspector";
import { EconomyBuilder } from "@/components/modules/EconomyBuilder";
import { SupplyBuilder } from "@/components/modules/SupplyBuilder";
import { RunStatus } from "@/components/RunStatus";
import { SimulationSkeleton } from "@/components/SimulationSkeleton";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { Panel } from "@/components/ui/Panel";
import { SidebarSection } from "@/components/ui/SidebarSection";
import { ConvergenceTrace } from "@/components/viz/ConvergenceTrace";
import { FlowProfile } from "@/components/viz/FlowProfile";
import { ModeShareByLocation } from "@/components/viz/ModeShareByLocation";
import { runSimulation, runSimulationStream } from "@/lib/api";
import { pyodideEngine } from "@/lib/pyodide-engine";
import type { Modo } from "@/lib/types";
import { useSimulationStore } from "@/store/simulationStore";

type HeatMode = "auto" | "metro" | "bici";

export function SandboxPage() {
  const { t } = useTranslation("simulator");
  const { t: tCommon } = useTranslation("common");
  const config = useSimulationStore((s) => s.config);
  const engine = useSimulationStore((s) => s.engine);
  const setEngine = useSimulationStore((s) => s.setEngine);
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

  const [heatMode, setHeatMode] = useState<HeatMode>("auto");

  const lastIter = liveIterations.at(-1) ?? result?.iteraciones.at(-1);
  const profile = lastIter
    ? lastIter.t_auto.map((t_auto, i) => ({
        t_auto,
        t_metro:
          lastIter.t_tren_viaje[i]! +
          lastIter.t_tren_acceso[i]! +
          lastIter.t_tren_espera[i]!,
        t_bici: lastIter.t_bici[i]!,
      }))
    : undefined;

  const operatingRatios = {
    car:
      result && lastIter
        ? Math.max(...lastIter.demanda_auto) / result.capacidad_auto
        : null,
    bike: lastIter
      ? Math.max(...lastIter.demanda_bici) / config.supply.bike.capacidad_pista
      : null,
  };

  const handleRun = async () => {
    startRun(config.max_iter);
    try {
      if (engine === "api") {
        await runSimulationStream(config, (snap) => pushIteration(snap));
        const final = await runSimulation(config);
        finishRun(final);
      } else {
        const final = await pyodideEngine.simulateStream(config, (snap) =>
          pushIteration(snap)
        );
        finishRun(final);
      }
    } catch (e) {
      failRun(e instanceof Error ? e.message : String(e));
    }
  };

  const totalAgents = lastIter
    ? (Object.values(lastIter.modal_split) as number[]).reduce((s, n) => s + n, 0)
    : 0;

  const kpis = useMemo<KPI[]>(() => {
    if (!result || !lastIter) {
      return [
        { label: t("kpi.trips"), value: "—" },
        { label: t("kpi.auto_pct"), value: "—" },
        { label: t("kpi.metro_pct"), value: "—" },
        { label: t("kpi.bici_pct"), value: "—" },
        { label: t("kpi.frequency"), value: "—" },
        { label: t("kpi.residual"), value: "—" },
      ];
    }
    const modal = lastIter.modal_split;
    const total = (Object.values(modal) as number[]).reduce((s, n) => s + n, 0);
    const tot = total > 0 ? total : 1;
    const pct = (m: Modo) => `${(((modal[m] ?? 0) / tot) * 100).toFixed(1)}%`;
    const count = (m: Modo) =>
      t("kpi.trips_subline", { n: (modal[m] ?? 0).toLocaleString() });
    return [
      { label: t("kpi.trips"), value: (total - (modal.Teletrabajo ?? 0)).toLocaleString() },
      { label: t("kpi.auto_pct"), value: pct("Auto"), color: "var(--auto)", delta: count("Auto") },
      { label: t("kpi.metro_pct"), value: pct("Metro"), color: "var(--metro)", delta: count("Metro") },
      { label: t("kpi.bici_pct"), value: pct("Bici"), color: "var(--bici)", delta: count("Bici") },
      { label: t("kpi.frequency"), value: lastIter.frecuencia_metro.toFixed(1), unit: "tph" },
      {
        label: t("kpi.residual"),
        value:
          lastIter.residuo == null || !isFinite(lastIter.residuo)
            ? "—"
            : lastIter.residuo.toFixed(3),
        unit: "min",
      },
    ];
  }, [result, lastIter, t]);

  const kpiCaption = useMemo(() => {
    if (!result || !lastIter) return null;
    const totalIters = result.iteraciones.length;
    return t("kpi.last_iteration", { n: lastIter.iter + 1, total: totalIters });
  }, [result, lastIter, t]);

  return (
    <div className="page">
      <aside className="sidebar">
        <CityBuilder config={config} onChange={setConfig} />
        <SupplyBuilder config={config} onChange={setConfig} operatingRatios={operatingRatios} />
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
              max={20}
              step={1}
              value={config.max_iter}
              onChange={(e) => setConfig((c) => ({ ...c, max_iter: Number(e.target.value) }))}
              aria-label={t("equilibrium.max_iter")}
            />
          </label>
        </SidebarSection>

        <SidebarSection
          title={tCommon("engine.label")}
          meta={engine === "api" ? "FastAPI" : "Pyodide"}
          defaultOpen={false}
        >
          <div className="seg" style={{ width: "100%" }}>
            <button
              type="button"
              className={engine === "api" ? "active" : ""}
              onClick={() => setEngine("api")}
              style={{ flex: 1 }}
            >
              FastAPI
            </button>
            <button
              type="button"
              className={engine === "local" ? "active" : ""}
              onClick={() => setEngine("local")}
              style={{ flex: 1 }}
            >
              Pyodide
            </button>
          </div>
          <p className="mt-2 text-[11px] text-muted">
            {engine === "api" ? tCommon("engine.info_api") : tCommon("engine.info_local")}
          </p>
        </SidebarSection>

        <button type="button" className="run-btn" disabled={running} onClick={handleRun}>
          {running
            ? `◜ ${t("equilibrium.iteration", {
                n: progress?.current ?? 0,
                total: progress?.total ?? 0,
              })}`
            : `▶ ${tCommon("actions.run")}`}
        </button>

        {error && (
          <div className="callout" style={{ borderLeftColor: "var(--metro)", marginTop: 12 }}>
            {error}
          </div>
        )}
      </aside>

      <section className="main">
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
                {t("sandbox.city_heading")}
              </span>
              <div className="seg">
                {(["auto", "metro", "bici"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setHeatMode(m)}
                    className={heatMode === m ? "active" : ""}
                  >
                    {t(`modes.${m}`)}
                  </button>
                ))}
              </div>
            </div>

            <ExportableFigure
              name={`ciudad-${heatMode}`}
              title={`${t("sandbox.city_heading")} — ${t(`modes.${heatMode}`)}`}
              description={t("sandbox.city_figure_desc", {
                length: config.city.largo_ciudad_km,
                cells: config.city.n_celdas,
                mode: t(`modes.${heatMode}`),
              })}
              exportSize={{ width: 1200, height: 200 }}
            >
              <CityStrip
                nCeldas={config.city.n_celdas}
                largoKm={config.city.largo_ciudad_km}
                pendientePct={config.city.pendiente_porcentaje}
                modeProfile={profile}
                heatMode={heatMode}
                shareEstratos={config.city.share_estratos}
                iterationToken={lastIter?.iter ?? -1}
              />
            </ExportableFigure>

            <div className="ribbon-legend">
              <span className="sw" style={{ "--c": "var(--auto)" } as React.CSSProperties}>
                {t("modes.auto")}
              </span>
              <span className="sw" style={{ "--c": "var(--metro)" } as React.CSSProperties}>
                {t("modes.metro")}
              </span>
              <span className="sw" style={{ "--c": "var(--bici)" } as React.CSSProperties}>
                {t("modes.bici")}
              </span>
              <span className="sw" style={{ "--c": "var(--walk)" } as React.CSSProperties}>
                {t("modes.caminata")}
              </span>
              <span style={{ marginLeft: "auto", textTransform: "none" }}>
                {t("hero.stats_line", {
                  total: totalAgents > 0 ? totalAgents.toLocaleString() : "—",
                  length: config.city.largo_ciudad_km,
                  stations: config.supply.train.num_estaciones,
                  lanes: config.supply.car.num_pistas,
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
              engine={engine}
            />
          </div>
        )}

        {((stage === "booting" && engine === "api") ||
          (stage === "running" && liveIterations.length === 0)) && (
          <div style={{ marginBottom: "var(--gap)" }}>
            <SimulationSkeleton nCeldas={config.city.n_celdas} />
          </div>
        )}

        {/* Grid de paneles FIG. NN */}
        {liveIterations.length > 0 && (
          <div className="panel-grid">
            <Panel n="01" title={t("equilibrium.converged")} meta="MSA" cls="col-12">
              <ConvergenceTrace iterations={liveIterations} />
            </Panel>

            {lastIter && result && (() => {
              // Escala Y compartida: el máximo global entre los 3 modos.
              // Permite comparar la magnitud relativa visualmente sin engañar
              // con el auto-scale por panel.
              const globalMax = Math.max(
                ...lastIter.demanda_auto,
                ...lastIter.demanda_bici,
                ...lastIter.demanda_metro,
                1
              );
              return (
                <>
                  <Panel
                    n="02"
                    title={t("modes.auto")}
                    meta={t("sandbox.flow_per_cell", { mode: t("modes.auto") })}
                    cls="col-4"
                  >
                    <ExportableFigure
                      name="flujo-auto"
                      title={t("sandbox.flow_per_cell", { mode: t("modes.auto") })}
                      exportSize={{ width: 600, height: 200 }}
                    >
                      <FlowProfile
                        flows={lastIter.demanda_auto}
                        largoKm={config.city.largo_ciudad_km}
                        color="var(--auto)"
                        yMax={globalMax}
                        capacityHint={`${Math.round(result.capacidad_auto)} veh/h corredor`}
                      />
                    </ExportableFigure>
                  </Panel>
                  <Panel
                    n="03"
                    title={t("modes.bici")}
                    meta={t("sandbox.flow_per_cell", { mode: t("modes.bici") })}
                    cls="col-4"
                  >
                    <ExportableFigure
                      name="flujo-bici"
                      title={t("sandbox.flow_per_cell", { mode: t("modes.bici") })}
                      exportSize={{ width: 600, height: 200 }}
                    >
                      <FlowProfile
                        flows={lastIter.demanda_bici}
                        largoKm={config.city.largo_ciudad_km}
                        color="var(--bici)"
                        yMax={globalMax}
                        capacityHint={`${config.supply.bike.capacidad_pista} bici/h`}
                      />
                    </ExportableFigure>
                  </Panel>
                  <Panel
                    n="04"
                    title={t("modes.metro")}
                    meta={t("sandbox.flow_per_cell", { mode: t("modes.metro") })}
                    cls="col-4"
                  >
                    <ExportableFigure
                      name="flujo-metro"
                      title={t("sandbox.flow_per_cell", { mode: t("modes.metro") })}
                      exportSize={{ width: 600, height: 200 }}
                    >
                      <FlowProfile
                        flows={lastIter.demanda_metro}
                        largoKm={config.city.largo_ciudad_km}
                        color="var(--metro)"
                        yMax={globalMax}
                        capacityHint={`${config.supply.train.capacidad_tren} pax/tren`}
                      />
                    </ExportableFigure>
                  </Panel>
                </>
              );
            })()}

            <Panel n="05" title={t("sections.demand")} meta="logit · breakdown" cls="col-7">
              <DemandInspector config={config} lastIter={lastIter} />
            </Panel>

            {result && result.agentes.length > 0 && (
              <Panel
                n="06"
                title={t("sandbox.mode_share_by_location")}
                meta="stacked · normalized 100%"
                cls="col-5"
              >
                <ExportableFigure
                  name="reparto-modal-por-ubicacion"
                  title={t("sandbox.mode_share_by_location")}
                  exportSize={{ width: 800, height: 280 }}
                >
                  <ModeShareByLocation
                    agents={result.agentes}
                    nCeldas={config.city.n_celdas}
                    largoKm={config.city.largo_ciudad_km}
                  />
                </ExportableFigure>
              </Panel>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
