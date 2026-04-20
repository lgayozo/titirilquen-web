import { useState } from "react";
import { useTranslation } from "react-i18next";

import { CityStrip } from "@/components/CityStrip";
import { CityBuilder } from "@/components/modules/CityBuilder";
import { DemandInspector } from "@/components/modules/DemandInspector";
import { SupplyBuilder } from "@/components/modules/SupplyBuilder";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { Section } from "@/components/ui/Section";
import { ConvergenceTrace } from "@/components/viz/ConvergenceTrace";
import { FlowProfile } from "@/components/viz/FlowProfile";
import { ModeShareByLocation } from "@/components/viz/ModeShareByLocation";
import { runSimulation, runSimulationStream } from "@/lib/api";
import { pyodideEngine } from "@/lib/pyodide-engine";
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
    car: result && lastIter
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
        const final = await pyodideEngine.simulateStream(config, (snap) => pushIteration(snap));
        finishRun(final);
      }
    } catch (e) {
      failRun(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="grid grid-cols-[340px_1fr] gap-6">
      <aside className="space-y-4">
        <CityBuilder config={config} onChange={setConfig} />
        <SupplyBuilder config={config} onChange={setConfig} operatingRatios={operatingRatios} />

        <Section title={t("sections.equilibrium")} defaultOpen={false}>
          <label className="block text-xs">
            <div className="flex items-baseline justify-between">
              <span className="text-slate-600 dark:text-slate-300">
                {t("equilibrium.max_iter")}
              </span>
              <span className="font-mono text-sm font-medium tabular-nums">
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
              className="mt-1 w-full accent-slate-900 dark:accent-slate-200"
            />
          </label>
        </Section>

        <Section title={tCommon("engine.label")} defaultOpen>
          <div className="flex gap-2">
            <EngineButton active={engine === "api"} onClick={() => setEngine("api")}>
              FastAPI
            </EngineButton>
            <EngineButton active={engine === "local"} onClick={() => setEngine("local")}>
              Pyodide
            </EngineButton>
          </div>
          <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
            {engine === "api" ? tCommon("engine.info_api") : tCommon("engine.info_local")}
          </p>
        </Section>

        <button
          type="button"
          onClick={handleRun}
          disabled={running}
          className="w-full rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900"
        >
          {running ? "…" : `▶ ${tCommon("actions.run")}`}
        </button>

        {error && (
          <div className="rounded border border-red-300 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}
      </aside>

      <section className="space-y-4">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              {t("sandbox.city_heading")}
            </h3>
            <div className="flex items-center gap-1 text-[11px]">
              {(["auto", "metro", "bici"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setHeatMode(m)}
                  className={
                    heatMode === m
                      ? "rounded bg-slate-900 px-2 py-1 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "rounded px-2 py-1 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
                  }
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
            />
          </ExportableFigure>
        </div>

        {stage === "booting" && engine === "local" && (
          <div
            role="status"
            aria-live="polite"
            className="rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200"
          >
            {t("equilibrium.booting_pyodide")}
          </div>
        )}

        {progress && stage === "running" && (
          <div
            role="status"
            aria-live="polite"
            aria-busy="true"
            className="rounded border border-slate-200 p-3 text-xs dark:border-slate-800"
          >
            <div className="mb-2 flex items-center justify-between">
              <span>{t("equilibrium.iteration", { n: progress.current, total: progress.total })}</span>
              {lastIter?.residuo != null && (
                <span className="font-mono tabular-nums text-slate-500">
                  {t("equilibrium.residual")}: {lastIter.residuo.toFixed(3)}
                </span>
              )}
            </div>
            <div
              role="progressbar"
              aria-valuenow={progress.current}
              aria-valuemin={0}
              aria-valuemax={progress.total}
              aria-label={t("equilibrium.iteration", { n: progress.current, total: progress.total })}
              className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
            >
              <div
                className="h-full bg-slate-900 transition-all dark:bg-slate-100"
                style={{ width: `${(progress.current / progress.total) * 100}%` }}
              />
            </div>
          </div>
        )}

        {liveIterations.length > 0 && (
          <ConvergenceTrace iterations={liveIterations} />
        )}

        {lastIter && (
          <div className="rounded border border-slate-200 p-4 dark:border-slate-800">
            <h4 className="mb-2 text-sm font-semibold">{t("sandbox.modal_split_last")}</h4>
            <div className="flex flex-wrap gap-3 text-xs">
              {Object.entries(lastIter.modal_split).map(([mode, count]) => (
                <div
                  key={mode}
                  className="rounded bg-slate-100 px-3 py-1 dark:bg-slate-800"
                >
                  <span className="font-medium">{t(`modes.${mode.toLowerCase()}`, mode)}:</span>{" "}
                  {count}
                </div>
              ))}
            </div>
          </div>
        )}

        {lastIter && result && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <ExportableFigure
              name="flujo-auto"
              title={t("sandbox.flow_per_cell", { mode: t("modes.auto") })}
              exportSize={{ width: 600, height: 200 }}
            >
              <FlowProfile
                flows={lastIter.demanda_auto}
                largoKm={config.city.largo_ciudad_km}
                label={t("sandbox.flow_per_cell", { mode: t("modes.auto") })}
                color="#FF8C00"
                capacity={result.capacidad_auto}
              />
            </ExportableFigure>
            <ExportableFigure
              name="flujo-bici"
              title={t("sandbox.flow_per_cell", { mode: t("modes.bici") })}
              exportSize={{ width: 600, height: 200 }}
            >
              <FlowProfile
                flows={lastIter.demanda_bici}
                largoKm={config.city.largo_ciudad_km}
                label={t("sandbox.flow_per_cell", { mode: t("modes.bici") })}
                color="#228B22"
                capacity={config.supply.bike.capacidad_pista}
              />
            </ExportableFigure>
            <ExportableFigure
              name="flujo-metro"
              title={t("sandbox.flow_per_cell", { mode: t("modes.metro") })}
              exportSize={{ width: 600, height: 200 }}
            >
              <FlowProfile
                flows={lastIter.demanda_metro}
                largoKm={config.city.largo_ciudad_km}
                label={t("sandbox.flow_per_cell", { mode: t("modes.metro") })}
                color="#FF0000"
              />
            </ExportableFigure>
          </div>
        )}

        <DemandInspector config={config} lastIter={lastIter} />

        {result && result.agentes.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
              {t("sandbox.mode_share_by_location")}
            </h3>
            <ExportableFigure
              name="reparto-modal-por-ubicacion"
              title={t("sandbox.mode_share_by_location")}
              exportSize={{ width: 1200, height: 280 }}
            >
              <ModeShareByLocation
                agents={result.agentes}
                nCeldas={config.city.n_celdas}
                largoKm={config.city.largo_ciudad_km}
              />
            </ExportableFigure>
          </div>
        )}
      </section>
    </div>
  );
}

function EngineButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        active
          ? "flex-1 rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-slate-100 dark:text-slate-900"
          : "flex-1 rounded border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
      }
    >
      {children}
    </button>
  );
}
