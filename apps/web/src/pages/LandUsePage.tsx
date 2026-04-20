import { useState } from "react";
import { useTranslation } from "react-i18next";

import { LandUseBuilder } from "@/components/modules/LandUseBuilder";
import { Section } from "@/components/ui/Section";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { BidPriceCurve } from "@/components/viz/BidPriceCurve";
import { OuterTrajectory } from "@/components/viz/OuterTrajectory";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { solveCoupledStream, solveLandUse } from "@/lib/api-v2";
import type { CoupledResult, OuterIteration } from "@/lib/types-v2";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

type Mode = "standalone" | "coupled";

export function LandUsePage() {
  const { t } = useTranslation("common");
  const { t: tS } = useTranslation("simulator");
  const config = useLandUseStore((s) => s.config);
  const setConfig = useLandUseStore((s) => s.setConfig);
  const stage = useLandUseStore((s) => s.stage);
  const result = useLandUseStore((s) => s.result);
  const coupledResult = useLandUseStore((s) => s.coupledResult);
  const error = useLandUseStore((s) => s.error);
  const outerMaxIter = useLandUseStore((s) => s.outerMaxIter);
  const setOuterMaxIter = useLandUseStore((s) => s.setOuterMaxIter);
  const startRun = useLandUseStore((s) => s.startRun);
  const finishStandalone = useLandUseStore((s) => s.finishStandalone);
  const finishCoupled = useLandUseStore((s) => s.finishCoupled);
  const fail = useLandUseStore((s) => s.fail);

  const simConfig = useSimulationStore((s) => s.config);
  const liveOuterIters = useLandUseStore((s) => s.liveOuterIters);
  const pushOuterIter = useLandUseStore((s) => s.pushOuterIter);

  const [mode, setMode] = useState<Mode>("standalone");

  const L = simConfig.city.n_celdas;
  const CBD = Math.floor(L / 2);

  const handleRun = async () => {
    startRun();
    try {
      if (mode === "standalone") {
        const r = await solveLandUse({ L, CBD, land_use: config });
        finishStandalone(r);
      } else {
        const collected: OuterIteration[] = [];
        await solveCoupledStream(
          { sim: simConfig, land_use: config, outer_max_iter: outerMaxIter, outer_tol: 1.0 },
          (it) => {
            collected.push(it);
            pushOuterIter(it);
          }
        );
        // Consolidamos un CoupledResult sintético a partir de las iteraciones recibidas.
        const last = collected[collected.length - 1];
        const result: CoupledResult = {
          converged:
            last != null && last.T_residual != null && last.T_residual < 1.0,
          iterations: collected,
          final_parcelas: [],  // el streaming no incluye la asignación final completa
          S: null,
        };
        finishCoupled(result);
      }
    } catch (e) {
      fail(e instanceof Error ? e.message : String(e));
    }
  };

  const parcelas =
    mode === "standalone" ? result?.parcelas : coupledResult?.final_parcelas;
  const prices = mode === "standalone" ? result?.result.p : null;
  const lastOuter =
    mode === "coupled" && coupledResult && coupledResult.iterations.length > 0
      ? coupledResult.iterations[coupledResult.iterations.length - 1]
      : null;

  return (
    <div className="grid grid-cols-[340px_1fr] gap-6">
      <aside className="space-y-4">
        <Section title={tS("sections.mode")} defaultOpen>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode("standalone")}
              className={
                mode === "standalone"
                  ? "flex-1 rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-slate-100 dark:text-slate-900"
                  : "flex-1 rounded border border-slate-200 px-3 py-1.5 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-400"
              }
            >
              {tS("land_use.mode_standalone")}
            </button>
            <button
              type="button"
              onClick={() => setMode("coupled")}
              className={
                mode === "coupled"
                  ? "flex-1 rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-slate-100 dark:text-slate-900"
                  : "flex-1 rounded border border-slate-200 px-3 py-1.5 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-400"
              }
            >
              {tS("land_use.mode_coupled")}
            </button>
          </div>
          <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
            {mode === "standalone" ? tS("land_use.info_standalone") : tS("land_use.info_coupled")}
          </p>
          {mode === "coupled" && (
            <p className="mt-1 text-[10px] text-amber-600 dark:text-amber-400">
              {tS("land_use.density_ignored_hint", {
                total: config.H_por_estrato.reduce((a, b) => a + b, 0).toLocaleString(),
              })}
            </p>
          )}
        </Section>

        <LandUseBuilder config={config} onChange={setConfig} />

        {mode === "coupled" && (
          <Section title={tS("land_use.outer_iterations")} defaultOpen>
            <label className="block text-xs">
              <div className="flex items-baseline justify-between">
                <span className="text-slate-600 dark:text-slate-300">
                  {tS("land_use.outer_iter_label")}
                </span>
                <span className="font-mono text-sm tabular-nums">{outerMaxIter}</span>
              </div>
              <input
                type="range"
                min={1}
                max={5}
                step={1}
                value={outerMaxIter}
                onChange={(e) => setOuterMaxIter(Number(e.target.value))}
                className="mt-1 w-full accent-slate-900 dark:accent-slate-200"
              />
            </label>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {tS("land_use.outer_iter_hint")}
            </p>
          </Section>
        )}

        <button
          type="button"
          onClick={handleRun}
          disabled={stage === "running"}
          className="w-full rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900"
        >
          {stage === "running" ? "…" : `▶ ${t("actions.run")}`}
        </button>

        {stage === "running" && mode === "coupled" && (
          <div className="rounded border border-slate-200 p-3 text-xs dark:border-slate-800">
            <div className="mb-1 flex items-center justify-between">
              <span>{tS("land_use.outer_iter_progress")}</span>
              <span className="font-mono tabular-nums">
                {liveOuterIters.length} / {outerMaxIter}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
              <div
                className="h-full bg-slate-900 transition-all dark:bg-slate-100"
                style={{
                  width: `${(liveOuterIters.length / outerMaxIter) * 100}%`,
                }}
              />
            </div>
            {liveOuterIters.length > 0 && (
              <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
                {tS("land_use.outer_iter_last_residual")}{" "}
                <strong className="font-mono tabular-nums">
                  {liveOuterIters[liveOuterIters.length - 1]?.T_residual?.toFixed(2) ?? "—"} min
                </strong>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="rounded border border-red-300 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}
      </aside>

      <section className="space-y-4">
        {parcelas ? (
          <>
            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                {tS("land_use.heading_distribution")}
              </h3>
              <ExportableFigure
                name="distribucion-estratos"
                title={tS("land_use.heading_distribution")}
                exportSize={{ width: 1200, height: 260 }}
              >
                <StratumDistribution parcelas={parcelas} />
              </ExportableFigure>
            </div>
            {prices && (
              <div>
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                  {tS("land_use.heading_equilibrium")}
                </h3>
                <ExportableFigure
                  name="precio-suelo"
                  title={tS("land_use.bid_price_title")}
                  exportSize={{ width: 1200, height: 200 }}
                >
                  <BidPriceCurve p={prices} />
                </ExportableFigure>
              </div>
            )}
          </>
        ) : (
          <div className="rounded border border-dashed border-slate-300 p-12 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
            {tS("land_use.run_placeholder")}
          </div>
        )}

        {mode === "coupled" && coupledResult && (
          <OuterTrajectory result={coupledResult} />
        )}
      </section>
    </div>
  );
}
