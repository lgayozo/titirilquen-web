import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { CityBuilder } from "@/components/modules/CityBuilder";
import { LandUseBuilder } from "@/components/modules/LandUseBuilder";
import { PresetGallery } from "@/components/modules/PresetGallery";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { Panel } from "@/components/ui/Panel";
import { BidPriceCurve } from "@/components/viz/BidPriceCurve";
import { CityShapePreview } from "@/components/viz/CityShapePreview";
import { DensityProfile } from "@/components/viz/DensityProfile";
import { StrataHeatmap } from "@/components/viz/StrataHeatmap";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { solveLandUse } from "@/lib/api-v2";
import { expectedComposition, smoothSupply } from "@/lib/citySupply";
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
  const setSimConfig = useSimulationStore((s) => s.setConfig);

  const L = simConfig.city.n_celdas;
  const CBD = Math.floor(L / 2);

  const handleRun = async () => {
    startRun({ L, CBD, largoKm: simConfig.city.largo_ciudad_km, config });
    try {
      const r = await solveLandUse({
        L,
        CBD,
        largo_km: simConfig.city.largo_ciudad_km,
        land_use: config,
      });
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
  const densidadCelda = result?.densidad_celda ?? null;
  const hasResult = !!result;

  // Heatmap de composición: ANTES = mezcla uniforme (proporciones π_h en cada
  // celda) · DESPUÉS = composición Q del equilibrio (ordenada por el bid-rent).
  const heatmap = useMemo<{
    before: number[][];
    after: number[][];
  } | null>(() => {
    if (!result) return null;
    const Q = result.result.Q; // Q[h][i]
    const Hc = (runContext?.config ?? config).H_por_estrato;
    const tot = Hc.reduce((a, b) => a + b, 0) || 1;
    const pi = Hc.map((h) => h / tot);
    const before = Array.from({ length: result.L }, () => [...pi]);
    const after = Array.from({ length: result.L }, (_, i) => [
      Q[0]?.[i] ?? 0,
      Q[1]?.[i] ?? 0,
      Q[2]?.[i] ?? 0,
    ]);
    return { before, after };
  }, [result, runContext, config]);

  // Hogares por celda = oferta S(i), repartidos por la composición Q del
  // equilibrio: N[h,i] = Q[h,i]·S_i. La envolvente es el perfil de OFERTA (la
  // «forma de la ciudad», Fig. 00), igual que como el core coloca los hogares
  // (asignar_hogares reparte según S). La Fig. de densidad usa la MISMA envolvente
  // (densidad = S/Δx), así que todas las figuras comparten forma. `smoothSupply`
  // reproduce la forma continua (sin el dentado de la discretización entera).
  const composition = useMemo<number[][] | null>(() => {
    if (!result) return null;
    const cfg = runContext?.config ?? config;
    const N = cfg.H_por_estrato.reduce((a, b) => a + b, 0);
    if (N <= 0) return null;
    const S = smoothSupply(
      cfg.forma,
      result.L,
      result.CBD,
      cfg.oferta_sigma_frac,
      cfg.forma_param,
      N,
    );
    return expectedComposition(result.result.Q, S);
  }, [result, runContext, config]);

  // Estado INICIAL (pre-equilibrio): todas las celdas con la MISMA proporción de
  // estratos (π_h = H_h/ΣH), sobre el perfil de OFERTA (la «forma de la ciudad»,
  // misma envolvente que la Fig. 00 y que la composición post-equilibrio). El
  // bid-rent luego reordena la mezcla uniforme sin cambiar el total por celda.
  const initComposition = useMemo<number[][] | null>(() => {
    const N = config.H_por_estrato.reduce((a, b) => a + b, 0);
    if (N <= 0) return null;
    const pi = config.H_por_estrato.map((h) => h / N);
    const S = smoothSupply(
      config.forma,
      L,
      CBD,
      config.oferta_sigma_frac,
      config.forma_param,
      N,
    );
    return S.map((s) => [s * pi[0]!, s * pi[1]!, s * pi[2]!]);
  }, [
    config.H_por_estrato,
    config.forma,
    config.oferta_sigma_frac,
    config.forma_param,
    L,
    CBD,
  ]);

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

        {/* Los presets de FORMA URBANA viven acá, no en Transporte: definen la
            ciudad (largo y compacidad), y Transporte solo la consume. */}
        <PresetGallery variant="city" />

        {/* Módulo completo de ciudad (largo, celdas, pendiente, teletrabajo):
            se define aquí y alimenta al módulo de Transporte. */}
        <CityBuilder config={simConfig} onChange={setSimConfig} />

        <LandUseBuilder
          config={config}
          onChange={setConfig}
          largoKm={simConfig.city.largo_ciudad_km}
        />

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
            className="font-display text-justify"
            style={{
              fontSize: 14,
              lineHeight: 1.6,
              color: "var(--ink-2)",
              marginBottom: 0,
            }}
          >
            {tS("land_use.intro")}
          </p>
          <p className="kpi-caption" style={{ marginTop: 8, marginBottom: 0 }}>
            {tS("land_use.relation")}{" "}
            <Link to="/coupled" style={{ color: "var(--accent)" }}>
              →
            </Link>
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
                    <StratumDistribution
                      parcelas={parcelas}
                      composition={composition ?? undefined}
                    />
                  </ExportableFigure>
                </Panel>
              )}

              {heatmap && (
                <Panel
                  n="02"
                  title={tS("land_use.heatmap_title")}
                  meta={tS("land_use.heatmap_meta")}
                  cls="col-12"
                >
                  <ExportableFigure
                    name="heatmap-estratos"
                    title={tS("land_use.heatmap_title")}
                    exportSize={{ width: 1000, height: 200 }}
                  >
                    <StrataHeatmap
                      before={heatmap.before}
                      after={heatmap.after}
                      largoKm={
                        runContext?.largoKm ?? simConfig.city.largo_ciudad_km
                      }
                    />
                  </ExportableFigure>
                  <p className="kpi-caption" style={{ marginTop: 8 }}>
                    {tS("land_use.heatmap_caption")}
                  </p>
                </Panel>
              )}

              {densidadCelda && densidadCelda.length > 0 && (
                <Panel
                  n="03"
                  title={tS("land_use.density_title")}
                  meta={tS("land_use.density_meta")}
                  cls="col-12"
                >
                  <ExportableFigure
                    name="densidad-por-celda"
                    title={tS("land_use.density_title")}
                    exportSize={{ width: 800, height: 200 }}
                  >
                    <DensityProfile densidad={densidadCelda} />
                  </ExportableFigure>
                </Panel>
              )}

              {prices && (
                <Panel
                  n="04"
                  title={tS("land_use.bid_price_title")}
                  meta="log-sum"
                  cls="col-12"
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

            {initComposition && initComposition.length > 0 && (
              <Panel
                n="01"
                title={tS("land_use.initial_pop_title")}
                meta={tS("land_use.initial_pop_meta")}
                cls="col-12"
              >
                <ExportableFigure
                  name="poblacion-inicial"
                  title={tS("land_use.initial_pop_title")}
                  exportSize={{ width: 1000, height: 260 }}
                >
                  <StratumDistribution composition={initComposition} />
                </ExportableFigure>
                <p className="kpi-caption" style={{ marginTop: 8 }}>
                  {tS("land_use.initial_pop_caption")}
                </p>
              </Panel>
            )}

            <div className="col-12">
              <div className="coupled-placeholder">
                <div className="coupled-placeholder-title">
                  {tS("land_use.placeholder_title")}
                </div>
                <p className="coupled-placeholder-desc">
                  {tS("land_use.placeholder_desc")}
                </p>
                <div className="coupled-placeholder-cta">
                  {tS("land_use.run_placeholder")}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
