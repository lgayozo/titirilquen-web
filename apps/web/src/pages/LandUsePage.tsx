import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { LandUseBuilder } from "@/components/modules/LandUseBuilder";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { Panel } from "@/components/ui/Panel";
import { BidPriceCurve } from "@/components/viz/BidPriceCurve";
import { CityShapePreview } from "@/components/viz/CityShapePreview";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { solveLandUse } from "@/lib/api-v2";
import { theilSegregation } from "@/lib/metrics";
import { isLandUseStale, useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

export function LandUsePage() {
  const { t } = useTranslation("common");
  const { t: tS } = useTranslation("simulator");
  const config = useLandUseStore((s) => s.config);
  const setConfig = useLandUseStore((s) => s.setConfig);
  const stage = useLandUseStore((s) => s.stage);
  const result = useLandUseStore((s) => s.result);
  const error = useLandUseStore((s) => s.error);
  const startRun = useLandUseStore((s) => s.startRun);
  const finishStandalone = useLandUseStore((s) => s.finishStandalone);
  const fail = useLandUseStore((s) => s.fail);
  const reset = useLandUseStore((s) => s.reset);
  const runContext = useLandUseStore((s) => s.runContext);

  const simConfig = useSimulationStore((s) => s.config);

  const L = simConfig.city.n_celdas;
  const CBD = Math.floor(L / 2);

  const handleRun = async () => {
    startRun({ L, CBD, largoKm: simConfig.city.largo_ciudad_km, config });
    try {
      const r = await solveLandUse({ L, CBD, land_use: config });
      finishStandalone(r);
    } catch (e) {
      fail(e instanceof Error ? e.message : String(e));
    }
  };

  // El resultado queda desactualizado si cambia la config de suelo O la
  // geometría compartida con Transporte (n_celdas / largo de la ciudad).
  const stale = isLandUseStale({
    stage,
    config,
    runContext,
    liveL: L,
    liveLargoKm: simConfig.city.largo_ciudad_km,
  });

  const parcelas = result?.parcelas;
  const prices = result?.result.p ?? null;
  const hasResult = !!result;

  // Métricas del equilibrio: distancia media al CBD por estrato (el test del
  // bid-rent) + segregación de Theil. La distancia se reporta en km usando el
  // largo de la ciudad de transporte.
  const metrics = useMemo<KPI[] | null>(() => {
    if (!result) return null;
    const { parcelas: parc, L: nL, CBD: cbd } = result;
    // Geometría de la corrida (snapshot), no la viva: cambiar la ciudad en
    // Transporte no debe reinterpretar un resultado viejo.
    const kmPerCell =
      (runContext?.largoKm ?? simConfig.city.largo_ciudad_km) / Math.max(nL, 1);
    const sum = [0, 0, 0];
    const cnt = [0, 0, 0];
    for (let i = 0; i < parc.length; i++) {
      const dkm = Math.abs(i - cbd) * kmPerCell;
      for (const h of parc[i] ?? []) {
        const k = h - 1;
        if (k === 0 || k === 1 || k === 2) {
          sum[k] = (sum[k] ?? 0) + dkm;
          cnt[k] = (cnt[k] ?? 0) + 1;
        }
      }
    }
    const theil = theilSegregation(result.result.Q);
    const STR = ["alto", "medio", "bajo"];
    const VAR = ["var(--s1)", "var(--s2)", "var(--s3)"];
    return [
      ...[0, 1, 2].map((k) => {
        const c = cnt[k] ?? 0;
        const dist = c > 0 ? (sum[k] ?? 0) / c : 0;
        return {
          label: tS("land_use.metric_dist", { s: tS(`strata.${STR[k]}`) }),
          value: dist.toFixed(1),
          unit: "km",
          color: VAR[k],
        };
      }),
      { label: tS("land_use.metric_segregation"), value: theil.toFixed(3) },
    ];
  }, [result, runContext, simConfig.city.largo_ciudad_km, tS]);

  return (
    <div className="page">
      <aside className="sidebar">
        <p className="text-[11px] text-muted" style={{ marginBottom: 6 }}>
          {tS("land_use.info_standalone")}
        </p>

        <LandUseBuilder config={config} onChange={setConfig} />

        {(stage === "done" || stage === "error") && (
          <button
            type="button"
            className="reset-btn"
            onClick={reset}
            title={t("actions.new_run")}
          >
            {`↺ ${t("actions.new_run")}`}
          </button>
        )}

        <button
          type="button"
          className="run-btn"
          disabled={stage === "running"}
          onClick={handleRun}
        >
          {stage === "running" ? "◜ …" : `▶ ${t("actions.run")}`}
        </button>

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
            <span>{tS("stale.banner")}</span>
            <button type="button" onClick={() => void handleRun()}>
              {`▶ ${tS("stale.rerun")}`}
            </button>
          </div>
        )}

        <div className="hero">
          <div className="hero-head">
            <h1 className="hero-title">{tS("land_use.title")}</h1>
            <div className="hero-sub">
              <span className="dot">●</span> {tS("land_use.subtitle")}
            </div>
          </div>
          <p
            className="font-display"
            style={{
              fontSize: 14,
              lineHeight: 1.6,
              color: "var(--ink-2)",
              marginBottom: 0,
            }}
          >
            {tS("land_use.intro")}
          </p>
        </div>

        {hasResult ? (
          <>
            {metrics && (
              <>
                <div className="kpi-caption">
                  {tS("land_use.metrics_caption")}
                </div>
                <KPIStrip items={metrics} />
              </>
            )}
            <div className="panel-grid">
              {parcelas && parcelas.length > 0 && (
                <Panel
                  n="01"
                  title={tS("land_use.heading_distribution")}
                  meta={tS("land_use.distribution_meta")}
                  cls="col-12"
                >
                  <ExportableFigure
                    name="distribucion-estratos"
                    title={tS("land_use.heading_distribution")}
                    exportSize={{ width: 1000, height: 260 }}
                  >
                    <StratumDistribution parcelas={parcelas} />
                  </ExportableFigure>
                </Panel>
              )}

              {prices && (
                <Panel
                  n="02"
                  title={tS("land_use.bid_price_title")}
                  meta="log-sum"
                  cls="col-12"
                >
                  <ExportableFigure
                    name="precio-suelo"
                    title={tS("land_use.bid_price_title")}
                    exportSize={{ width: 800, height: 200 }}
                  >
                    <BidPriceCurve p={prices} solver={config.solver} />
                  </ExportableFigure>
                </Panel>
              )}
            </div>
          </>
        ) : (
          <div className="panel-grid">
            <Panel
              n="00"
              title={tS("land_use.shape_preview_title")}
              meta={tS(`land_use.forma_${config.forma}`)}
              cls="col-12"
            >
              <CityShapePreview
                forma={config.forma}
                L={L}
                CBD={CBD}
                sigmaFrac={config.oferta_sigma_frac}
                formaParam={config.forma_param}
              />
              <p className="kpi-caption" style={{ marginTop: 8 }}>
                {tS("land_use.shape_preview_caption")}
              </p>
            </Panel>
          </div>
        )}
      </section>
    </div>
  );
}
