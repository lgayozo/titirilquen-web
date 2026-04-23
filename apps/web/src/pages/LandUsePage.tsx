import { useState } from "react";
import { useTranslation } from "react-i18next";

import { LandUseBuilder } from "@/components/modules/LandUseBuilder";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { Panel } from "@/components/ui/Panel";
import { BidPriceCurve } from "@/components/viz/BidPriceCurve";
import { CoupledMetrics } from "@/components/viz/CoupledMetrics";
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
        const last = collected[collected.length - 1];
        const synthetic: CoupledResult = {
          converged: last != null && last.T_residual != null && last.T_residual < 1.0,
          iterations: collected,
          final_parcelas: [],
          S: null,
        };
        finishCoupled(synthetic);
      }
    } catch (e) {
      fail(e instanceof Error ? e.message : String(e));
    }
  };

  const parcelas = mode === "standalone" ? result?.parcelas : coupledResult?.final_parcelas;
  const prices = mode === "standalone" ? result?.result.p : null;

  return (
    <div className="page">
      <aside className="sidebar">
        <h3>{tS("sections.mode")}</h3>
        <div className="seg" style={{ width: "100%" }}>
          <button
            type="button"
            className={mode === "standalone" ? "active" : ""}
            onClick={() => setMode("standalone")}
            style={{ flex: 1 }}
          >
            {tS("land_use.mode_standalone")}
          </button>
          <button
            type="button"
            className={mode === "coupled" ? "active" : ""}
            onClick={() => setMode("coupled")}
            style={{ flex: 1 }}
          >
            {tS("land_use.mode_coupled")}
          </button>
        </div>
        <p className="mt-2 text-[11px] text-muted">
          {mode === "standalone" ? tS("land_use.info_standalone") : tS("land_use.info_coupled")}
        </p>
        {mode === "coupled" && (
          <p className="mt-1 text-[10px]" style={{ color: "var(--accent)" }}>
            {tS("land_use.density_ignored_hint", {
              total: config.H_por_estrato.reduce((a, b) => a + b, 0).toLocaleString(),
            })}
          </p>
        )}

        <LandUseBuilder config={config} onChange={setConfig} />

        {mode === "coupled" && (
          <>
            <h3>{tS("land_use.outer_iterations")}</h3>
            <label className="slider-row block">
              <div className="srow-top">
                <span className="srow-label">{tS("land_use.outer_iter_label")}</span>
                <span className="srow-val" aria-hidden>
                  {outerMaxIter}
                </span>
              </div>
              <input
                type="range"
                min={1}
                max={5}
                step={1}
                value={outerMaxIter}
                onChange={(e) => setOuterMaxIter(Number(e.target.value))}
              />
            </label>
            <p className="text-[11px] text-muted">{tS("land_use.outer_iter_hint")}</p>
          </>
        )}

        <button
          type="button"
          className="run-btn"
          disabled={stage === "running"}
          onClick={handleRun}
        >
          {stage === "running" ? "◜ …" : `▶ ${t("actions.run")}`}
        </button>

        {stage === "running" && mode === "coupled" && (
          <div className="callout mt-3" style={{ borderLeftColor: "var(--accent)" }}>
            <div className="flex items-center justify-between">
              <span>{tS("land_use.outer_iter_progress")}</span>
              <span className="font-fig tabular-nums">
                {liveOuterIters.length} / {outerMaxIter}
              </span>
            </div>
            {liveOuterIters.length > 0 && (
              <div
                className="mt-1 text-[11px]"
                style={{ fontStyle: "normal", fontFamily: "var(--font-body)" }}
              >
                {tS("land_use.outer_iter_last_residual")}{" "}
                <strong className="font-fig tabular-nums">
                  {liveOuterIters[liveOuterIters.length - 1]?.T_residual?.toFixed(2) ?? "—"} min
                </strong>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="callout" style={{ borderLeftColor: "var(--metro)", marginTop: 12 }}>
            {error}
          </div>
        )}
      </aside>

      <section className="main">
        <div className="hero">
          <div className="hero-head">
            <h1 className="hero-title">{tS("land_use.title")}</h1>
            <div className="hero-sub">
              <span className="dot">●</span> {tS("land_use.subtitle")}
            </div>
          </div>
          <p
            className="font-display"
            style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ink-2)", marginBottom: 0 }}
          >
            La teoría del <em>bid-rent</em> predice que los hogares con mayor valoración de la
            accesibilidad al centro superan en subasta a los demás por parcelas cercanas al CBD,
            empujando a los grupos de menor valoración hacia la periferia.
          </p>
        </div>

        {parcelas ? (
          <div className="panel-grid">
            <Panel
              n="01"
              title={tS("land_use.heading_distribution")}
              meta="bid-rent · 3 strata"
              cls="col-7"
            >
              <ExportableFigure
                name="distribucion-estratos"
                title={tS("land_use.heading_distribution")}
                exportSize={{ width: 1000, height: 260 }}
              >
                <StratumDistribution parcelas={parcelas} />
              </ExportableFigure>
            </Panel>

            {prices && (
              <Panel
                n="02"
                title={tS("land_use.bid_price_title")}
                meta="log-sum"
                cls="col-5"
              >
                <ExportableFigure
                  name="precio-suelo"
                  title={tS("land_use.bid_price_title")}
                  exportSize={{ width: 800, height: 200 }}
                >
                  <BidPriceCurve p={prices} />
                </ExportableFigure>
              </Panel>
            )}

            {mode === "coupled" && coupledResult && (
              <>
                <Panel
                  n="03"
                  title={tS("coupled_metrics.header")}
                  meta="Theil · welfare · Hansen"
                  cls="col-12"
                >
                  <CoupledMetrics result={coupledResult} landUseConfig={config} />
                </Panel>
                <Panel n="04" title={tS("land_use.outer_iterations")} cls="col-12">
                  <OuterTrajectory result={coupledResult} />
                </Panel>
              </>
            )}
          </div>
        ) : (
          <div className="callout">{tS("land_use.run_placeholder")}</div>
        )}
      </section>
    </div>
  );
}
