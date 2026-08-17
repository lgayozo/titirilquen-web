import { useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";

import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { Panel } from "@/components/ui/Panel";
import { CityShapePreview } from "@/components/viz/CityShapePreview";
import { EquilibriumMetricsTable } from "@/components/viz/EquilibriumMetricsTable";
import { OuterTrajectory } from "@/components/viz/OuterTrajectory";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { resolverAcopladoStream } from "@/lib/api";
import { expectedComposition, supplyVector } from "@/lib/citySupply";
import {
  JOINT_PRESETS,
  applyJointPreset,
  describePresetParams,
} from "@/lib/joint-presets";
import type {
  CoupledResult,
  LandUseConfig,
  OuterIteration,
} from "@/lib/types-v2";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

type Stage = "idle" | "running" | "done" | "error";

/**
 * Página dedicada al loop acoplado: storytelling "sin feedback" vs "con
 * feedback". Permite al estudiante seleccionar un escenario conjunto
 * (ciudad + política + suelo) y comparar el equilibrio ingenuo (iter 0,
 * donde land use no sabe de transporte) con el equilibrio acoplado (iter N,
 * donde suelo y transporte se reconcilian).
 */
/** Fuente del escenario: la config propia del usuario o un preset de prueba. */
const CUSTOM = "custom";

// AbortController de la corrida activa, a nivel de módulo: la página puede
// desmontarse y volver a montar mientras el stream sigue (el estado vive en el
// store); esto permite cancelar igual tras la navegación.
let activeCoupledAbort: AbortController | null = null;

export function CoupledPage() {
  const { t: tS } = useTranslation("simulator");

  // Config "propia" del usuario, compartida con los módulos Transporte (Sandbox)
  // y Uso de Suelo vía sus stores. Es el escenario **por defecto**.
  const simStore = useSimulationStore((s) => s.config);
  const luStore = useLandUseStore((s) => s.config);

  const CUSTOM_POBLACION = 25000;
  // El estado de la corrida vive en el store (no en useState): navegar a mitad
  // de una corrida no la pierde — al volver, el stream sigue poblando la página.
  const source = useLandUseStore((s) => s.coupledSource);
  const setSource = useLandUseStore((s) => s.setCoupledSource);
  const outerMaxIter = useLandUseStore((s) => s.coupledOuterMaxIter);
  const setOuterMaxIter = useLandUseStore((s) => s.setCoupledOuterMaxIter);
  const poblacion = useLandUseStore((s) => s.coupledPoblacion);
  const setPoblacion = useLandUseStore((s) => s.setCoupledPoblacion);
  const stage: Stage = useLandUseStore((s) => s.coupledStage);
  const error = useLandUseStore((s) => s.coupledError);
  const iters = useLandUseStore((s) => s.coupledIters);
  const snapshot = useLandUseStore((s) => s.coupledSnapshot);
  const startCoupled = useLandUseStore((s) => s.startCoupled);
  const pushOuterIter = useLandUseStore((s) => s.pushOuterIter);
  const finishCoupled = useLandUseStore((s) => s.finishCoupled);
  const failCoupled = useLandUseStore((s) => s.failCoupled);
  const cancelCoupled = useLandUseStore((s) => s.cancelCoupled);
  const resetCoupled = useLandUseStore((s) => s.resetCoupled);

  // Seleccionar escenario fija también la población recomendada (cada escenario
  // tiene un techo de demanda distinto antes de gridlockear — ver D-24).
  const selectSource = (key: string) => {
    setSource(key);
    const p = JOINT_PRESETS.find((x) => x.key === key);
    setPoblacion(p ? p.poblacionDefault : CUSTOM_POBLACION);
  };

  const isCustom = source === CUSTOM;
  const preset = JOINT_PRESETS.find((p) => p.key === source) ?? null;
  const { sim, landUse } = useMemo(
    () =>
      isCustom || !preset
        ? { sim: simStore, landUse: luStore }
        : applyJointPreset(preset),
    [isCustom, preset, simStore, luStore],
  );

  // Escala de demanda: re-escala H_por_estrato a la población elegida,
  // conservando la composición por estrato. Es la palanca que activa los
  // feedbacks del transporte (congestión, frecuencia de metro, capacidad).
  const landUseEff = useMemo<LandUseConfig>(() => {
    const H = landUse.H_por_estrato;
    const sum = H.reduce((a, b) => a + b, 0) || 1;
    const scaled = H.map((h) =>
      Math.max(1, Math.round((poblacion * h) / sum)),
    ) as [number, number, number];
    return { ...landUse, H_por_estrato: scaled };
  }, [landUse, poblacion]);

  const abortRef = useRef<AbortController | null>(activeCoupledAbort);

  const handleRun = async () => {
    const ctrl = new AbortController();
    activeCoupledAbort = ctrl;
    abortRef.current = ctrl;
    startCoupled({ sim, landUse: landUseEff, outerMaxIter });
    try {
      await resolverAcopladoStream(
        {
          sim,
          land_use: landUseEff,
          outer_max_iter: outerMaxIter,
          outer_tol: 1.0,
        },
        (it) => pushOuterIter(it),
        ctrl.signal,
      );
      finishCoupled();
    } catch (e) {
      if (ctrl.signal.aborted) return; // cancelado por el usuario
      failCoupled(e instanceof Error ? e.message : String(e));
    }
  };

  const handleCancel = () => {
    (abortRef.current ?? activeCoupledAbort)?.abort();
    cancelCoupled();
  };

  const handleReset = () => resetCoupled();

  // ¿El resultado quedó desactualizado respecto del escenario configurado?
  const stale = useMemo(
    () =>
      stage === "done" &&
      snapshot != null &&
      JSON.stringify({ sim, landUse: landUseEff, outerMaxIter }) !==
        JSON.stringify(snapshot),
    [stage, snapshot, sim, landUseEff, outerMaxIter],
  );

  const first = iters[0] ?? null;
  const last = iters[iters.length - 1] ?? null;

  // Resultado en forma de CoupledResult para los componentes de trayectoria.
  const result: CoupledResult | null = iters.length
    ? {
        converged: stage === "done",
        iterations: iters,
        final_parcelas: [],
        S: null,
      }
    : null;

  // Palancas del escenario, para el KPIStrip de parámetros.
  // Parámetros agrupados en dos filas con sentido (antes una sola grilla de 10
  // ítems que dejaba un huérfano en la segunda fila): ciudad+suelo (3) arriba,
  // transporte (7) abajo.
  const { kpisCityLand, kpisTransport } = useMemo(() => {
    const groupColor: Record<string, string> = {
      city: "var(--s2)",
      land_use: "var(--accent)",
      transport: "var(--ink)",
    };
    const all = describePresetParams(sim, landUseEff).map((p) => ({
      group: p.group,
      kpi: {
        label: tS(p.labelKey),
        value: p.value,
        // "hog" (hogares) es la única unidad con idioma; el resto son símbolos.
        unit: p.unit === "hog" ? tS("coupled.unit_households") : p.unit,
        color: groupColor[p.group],
      } as KPI,
    }));
    return {
      kpisCityLand: all
        .filter((x) => x.group !== "transport")
        .map((x) => x.kpi),
      kpisTransport: all
        .filter((x) => x.group === "transport")
        .map((x) => x.kpi),
    };
  }, [sim, landUseEff, tS]);

  const L = sim.city.n_celdas;
  const CBD = Math.floor(L / 2);
  const running = stage === "running";

  // Oferta S(i) real de la forma elegida, para que la distribución de resultados
  // comparta la misma envolvente que la figura de la forma (figura 00).
  const supply = useMemo(
    () =>
      supplyVector(
        landUseEff.forma,
        L,
        CBD,
        landUseEff.oferta_sigma_frac,
        landUseEff.forma_param,
        landUseEff.H_por_estrato.reduce((a, b) => a + b, 0),
      ),
    [landUseEff, L, CBD],
  );

  return (
    <div className="page">
      {/* ---------- Sidebar: selección de escenario + controles ---------- */}
      <aside className="sidebar">
        <p className="coupled-sidebar-info">{tS("coupled.lede")}</p>

        <div className="coupled-source-label">
          {tS("coupled.source_custom_label")}
        </div>
        <div className="coupled-scenario-list">
          <button
            type="button"
            className={`coupled-preset compact ${isCustom ? "active" : ""}`}
            onClick={() => selectSource(CUSTOM)}
          >
            <div className="coupled-preset-title">
              {tS("coupled.custom_title")}
            </div>
            <div className="coupled-preset-desc">
              {tS("coupled.custom_desc")}
            </div>
            <div className="coupled-preset-tags">
              <span>{tS("coupled.custom_tag")}</span>
            </div>
          </button>
        </div>

        <div className="coupled-source-label">
          {tS("coupled.source_preset_label")}
        </div>
        <div className="coupled-scenario-list">
          {JOINT_PRESETS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`coupled-preset compact ${source === p.key ? "active" : ""}`}
              onClick={() => selectSource(p.key)}
            >
              <div className="coupled-preset-title">{tS(p.titleKey)}</div>
              <div className="coupled-preset-desc">{tS(p.descriptionKey)}</div>
              <div className="coupled-preset-tags">
                <span>{p.city}</span>
                <span>·</span>
                <span>{p.policy}</span>
              </div>
            </button>
          ))}
        </div>

        <label className="coupled-iter-input">
          <span>{tS("coupled.poblacion_label")}</span>
          <input
            type="range"
            min={10000}
            max={120000}
            step={10000}
            value={poblacion}
            onChange={(e) => setPoblacion(Number(e.target.value))}
          />
          <span className="num">{(poblacion / 1000).toFixed(0)}k</span>
        </label>
        {(() => {
          // Cada escenario tiene un techo de demanda antes de gridlockear el
          // corredor monocéntrico (D-24); sobre eso el equilibrio se degrada.
          const recomendada = preset?.poblacionDefault ?? CUSTOM_POBLACION;
          return poblacion > recomendada ? (
            <p
              className="text-[11px] leading-snug"
              style={{ color: "var(--accent)", marginTop: -6 }}
            >
              {tS("coupled.poblacion_warn", {
                n: Math.round(recomendada / 1000),
              })}
            </p>
          ) : null;
        })()}

        <label className="coupled-iter-input">
          <span>{tS("land_use.outer_iter_label")}</span>
          <input
            type="range"
            min={2}
            max={50}
            step={1}
            value={outerMaxIter}
            onChange={(e) => setOuterMaxIter(Number(e.target.value))}
          />
          <span className="num">{outerMaxIter}</span>
        </label>

        {(stage === "done" || stage === "error") && (
          <button type="button" className="reset-btn" onClick={handleReset}>
            ↺ {tS("coupled.reset")}
          </button>
        )}

        <button
          type="button"
          className="run-btn"
          onClick={handleRun}
          disabled={running}
        >
          {running ? "◜ …" : `▶ ${tS("coupled.run")}`}
        </button>

        {running && (
          <button type="button" className="reset-btn" onClick={handleCancel}>
            {`✕ ${tS("stale.cancel")}`}
          </button>
        )}

        {error && (
          <div
            className="callout"
            style={{ borderLeftColor: "var(--metro)", marginTop: 12 }}
          >
            <strong>{tS("coupled.error")}:</strong> {error}
          </div>
        )}
      </aside>

      {/* ---------- Main: imagen arriba + parámetros + resultados ---------- */}
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
            <h1 className="hero-title">{tS("coupled.title")}</h1>
            <div className="hero-sub">
              <span className="dot">●</span> {tS("coupled.eyebrow")}
            </div>
          </div>
        </div>

        {/* Imagen de la ciudad — solo como preview antes de correr (tras correr,
            la silueta se ve coloreada por estrato en los paneles de resultado). */}
        {iters.length === 0 && (
          <div className="panel-grid">
            <Panel
              n="00"
              title={tS("coupled.preset_detail_shape")}
              meta={tS(`land_use.forma_${landUse.forma}`)}
              cls="col-12"
            >
              <CityShapePreview
                forma={landUse.forma}
                L={L}
                CBD={CBD}
                sigmaFrac={landUse.oferta_sigma_frac}
                formaParam={landUse.forma_param}
              />
            </Panel>
          </div>
        )}

        {/* Palancas del escenario */}
        <div className="panel-grid">
          <Panel
            n="01"
            title={tS("coupled.preset_detail_title")}
            meta={tS("coupled.preset_detail_meta")}
            cls="col-12"
          >
            <p className="coupled-panel-hint">
              {isCustom
                ? tS("coupled.preset_detail_hint_custom")
                : tS("coupled.preset_detail_hint")}
            </p>
            <div className="kpi-caption">{tS("coupled.params_city_land")}</div>
            <KPIStrip items={kpisCityLand} />
            <div className="kpi-caption">{tS("coupled.params_transport")}</div>
            <KPIStrip items={kpisTransport} />
          </Panel>
        </div>

        {iters.length > 0 && (
          <>
            <Comparison
              first={first!}
              last={last!}
              supply={supply}
              tS={tS}
              stage={stage}
              iters={iters.length}
            />

            {result && (
              <div className="panel-grid">
                <Panel
                  n="04"
                  title={tS("coupled.convergence_title")}
                  meta={tS("coupled.convergence_meta")}
                  cls="col-12"
                >
                  <p className="coupled-panel-hint">
                    {tS("coupled.convergence_hint")}
                  </p>
                  <OuterTrajectory result={result} />
                </Panel>
              </div>
            )}

            {last && (
              <div className="panel-grid">
                <Panel
                  n="05"
                  title={tS("eqt.title")}
                  meta={tS("coupled_metrics.outer_count", { n: iters.length })}
                  cls="col-12"
                >
                  <EquilibriumMetricsTable
                    last={last.metrics}
                    first={first?.metrics ?? null}
                  />
                </Panel>
              </div>
            )}

            <Interpretation first={first!} last={last!} tS={tS} />
          </>
        )}

        {iters.length === 0 && stage !== "running" && (
          <div className="coupled-placeholder">
            <div className="coupled-placeholder-title">
              {tS("coupled.placeholder_title")}
            </div>
            <p className="coupled-placeholder-desc">
              {tS("coupled.placeholder_desc")}
            </p>
            <div className="coupled-placeholder-cta">
              {tS("coupled.placeholder")}
            </div>
          </div>
        )}

        {running && iters.length === 0 && (
          <div className="coupled-placeholder">{tS("coupled.booting")}</div>
        )}
      </section>
    </div>
  );
}

interface ComparisonProps {
  first: OuterIteration;
  last: OuterIteration;
  supply: readonly number[];
  tS: (key: string, opts?: Record<string, unknown>) => string;
  stage: Stage;
  iters: number;
}

function Comparison({
  first,
  last,
  supply,
  tS,
  stage,
  iters,
}: ComparisonProps) {
  // Distribución = oferta S × asignación Q (respeta la forma de la ciudad).
  // Composición ESPERADA en floats (S·Q sin redondear): el redondeo entero por
  // celda producía una "peineta" entre celdas contiguas con pocos hogares.
  const firstComposition = expectedComposition(first.land_use.Q, supply);
  const lastComposition = expectedComposition(last.land_use.Q, supply);
  const isSameIter = first.outer_iter === last.outer_iter;

  return (
    <div className="panel-grid">
      <Panel
        n="02"
        title={tS("coupled.without_feedback")}
        meta={tS("coupled.iter_n", { n: first.outer_iter + 1 })}
        cls="col-6"
      >
        <p className="coupled-panel-hint">
          {tS("coupled.without_feedback_hint")}
        </p>
        <StratumDistribution composition={firstComposition} />
      </Panel>

      <Panel
        n="03"
        title={tS("coupled.with_feedback")}
        meta={
          isSameIter
            ? tS("coupled.waiting")
            : tS("coupled.iter_n", { n: last.outer_iter + 1 })
        }
        cls="col-6"
      >
        <p className="coupled-panel-hint">
          {stage === "running"
            ? tS("coupled.running_hint", { n: iters })
            : tS("coupled.with_feedback_hint")}
        </p>
        <StratumDistribution composition={lastComposition} />
      </Panel>
    </div>
  );
}

interface InterpretationProps {
  first: OuterIteration;
  last: OuterIteration;
  tS: (key: string, opts?: Record<string, unknown>) => string;
}

function Interpretation({ first, last, tS }: InterpretationProps) {
  // Lectura pedagógica desde el REPORTE DEL CORE (metrics) — la misma fuente
  // que la tabla del equilibrio, comparando iteración 0 (sin feedback) vs
  // final. Antes se recomputaba en TS con métricas rotas: el índice de Hansen
  // underfloweaba con α en utiles/min (exp(−130) ≈ 0) sobre una T que ya es
  // común por ubicación (D-22), y el "bienestar" comparaba utiles ENTRE
  // estratos, que no son conmensurables (cada estrato tiene sus ASC/β).
  const eF = first.metrics.por_estrato;
  const eL = last.metrics.por_estrato;
  const alto = 0;
  const bajo = eL.length - 1;

  const dSeg =
    last.metrics.sistema.segregacion_theil -
    first.metrics.sistema.segregacion_theil;

  // Equidad: carga mensual costo/ingreso (adimensional ⇒ comparable entre
  // estratos), en puntos porcentuales.
  const dCargaAlto =
    ((eL[alto]?.carga_costo_ingreso ?? 0) -
      (eF[alto]?.carga_costo_ingreso ?? 0)) *
    100;
  const dCargaBajo =
    ((eL[bajo]?.carga_costo_ingreso ?? 0) -
      (eF[bajo]?.carga_costo_ingreso ?? 0)) *
    100;

  // Accesibilidad: tiempo medio de viaje experimentado por estrato (min).
  const dTAlto =
    (eL[alto]?.tiempo_medio_min ?? 0) - (eF[alto]?.tiempo_medio_min ?? 0);
  const dTBajo =
    (eL[bajo]?.tiempo_medio_min ?? 0) - (eF[bajo]?.tiempo_medio_min ?? 0);

  const highlights: Array<{ title: string; body: string }> = [];

  if (Math.abs(dSeg) > 0.01) {
    highlights.push({
      title: tS("coupled.interp.segregation_title"),
      body: tS(
        dSeg > 0
          ? "coupled.interp.segregation_up"
          : "coupled.interp.segregation_down",
        { delta: Math.abs(dSeg).toFixed(3) },
      ),
    });
  }
  if (Math.abs(dCargaBajo - dCargaAlto) > 0.2) {
    const regresivo = dCargaBajo > dCargaAlto;
    highlights.push({
      title: tS("coupled.interp.welfare_title"),
      body: tS(
        regresivo
          ? "coupled.interp.welfare_regressive"
          : "coupled.interp.welfare_progressive",
        {
          alto: fmt(dCargaAlto, 1),
          bajo: fmt(dCargaBajo, 1),
          cargaBajo: ((eL[bajo]?.carga_costo_ingreso ?? 0) * 100).toFixed(1),
        },
      ),
    });
  }
  if (Math.max(Math.abs(dTAlto), Math.abs(dTBajo)) > 0.5) {
    highlights.push({
      title: tS("coupled.interp.accessibility_title"),
      body: tS("coupled.interp.accessibility_body", {
        alto: fmt(dTAlto, 1),
        bajo: fmt(dTBajo, 1),
        tBajo: (eL[bajo]?.tiempo_medio_min ?? 0).toFixed(1),
      }),
    });
  }

  if (highlights.length === 0) {
    highlights.push({
      title: tS("coupled.interp.stable_title"),
      body: tS("coupled.interp.stable_body"),
    });
  }

  return (
    <div className="coupled-interpretation">
      <div className="coupled-interp-header">{tS("coupled.interp.header")}</div>
      <div className="coupled-interp-grid">
        {highlights.map((h, i) => (
          <div key={i} className="coupled-interp-card">
            <div className="coupled-interp-title">{h.title}</div>
            <p className="coupled-interp-body">{h.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function fmt(v: number, digits = 2): string {
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}`;
}
