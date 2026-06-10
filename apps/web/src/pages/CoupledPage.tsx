import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { Panel } from "@/components/ui/Panel";
import { CityShapePreview } from "@/components/viz/CityShapePreview";
import { EquilibriumMetricsTable } from "@/components/viz/EquilibriumMetricsTable";
import { OuterTrajectory } from "@/components/viz/OuterTrajectory";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { solveCoupledStream } from "@/lib/api-v2";
import { reconstructParcelas, supplyVector } from "@/lib/citySupply";
import {
  JOINT_PRESETS,
  applyJointPreset,
  describePresetParams,
} from "@/lib/joint-presets";
import {
  accessibilityHansen,
  meanUtilityByStratum,
  theilSegregation,
} from "@/lib/metrics";
import type { CoupledResult, LandUseConfig, OuterIteration } from "@/lib/types-v2";
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

export function CoupledPage() {
  const { t: tS } = useTranslation("simulator");

  // Config "propia" del usuario, compartida con los módulos Transporte (Sandbox)
  // y Uso de Suelo vía sus stores. Es el escenario **por defecto**.
  const simStore = useSimulationStore((s) => s.config);
  const luStore = useLandUseStore((s) => s.config);

  const CUSTOM_POBLACION = 25000;
  const [source, setSource] = useState<string>(CUSTOM);
  const [outerMaxIter, setOuterMaxIter] = useState(12);
  const [poblacion, setPoblacion] = useState(CUSTOM_POBLACION);

  // Seleccionar escenario fija también la población recomendada (cada escenario
  // tiene un techo de demanda distinto antes de gridlockear — ver D-24).
  const selectSource = (key: string) => {
    setSource(key);
    const p = JOINT_PRESETS.find((x) => x.key === key);
    setPoblacion(p ? p.poblacionDefault : CUSTOM_POBLACION);
  };
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [iters, setIters] = useState<OuterIteration[]>([]);

  const isCustom = source === CUSTOM;
  const preset = JOINT_PRESETS.find((p) => p.key === source) ?? null;
  const { sim, landUse } = useMemo(
    () =>
      isCustom || !preset
        ? { sim: simStore, landUse: luStore }
        : applyJointPreset(preset),
    [isCustom, preset, simStore, luStore]
  );

  // Escala de demanda: re-escala H_por_estrato a la población elegida,
  // conservando la composición por estrato. Es la palanca que activa los
  // feedbacks del transporte (congestión, frecuencia de metro, capacidad).
  const landUseEff = useMemo<LandUseConfig>(() => {
    const H = landUse.H_por_estrato;
    const sum = H.reduce((a, b) => a + b, 0) || 1;
    const scaled = H.map((h) => Math.max(1, Math.round((poblacion * h) / sum))) as [
      number,
      number,
      number,
    ];
    return { ...landUse, H_por_estrato: scaled };
  }, [landUse, poblacion]);

  const handleRun = async () => {
    setStage("running");
    setError(null);
    setIters([]);
    const collected: OuterIteration[] = [];
    try {
      await solveCoupledStream(
        { sim, land_use: landUseEff, outer_max_iter: outerMaxIter, outer_tol: 1.0 },
        (it) => {
          collected.push(it);
          setIters([...collected]);
        }
      );
      setStage("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStage("error");
    }
  };

  const handleReset = () => {
    setStage("idle");
    setIters([]);
    setError(null);
  };

  const first = iters[0] ?? null;
  const last = iters[iters.length - 1] ?? null;

  // Resultado en forma de CoupledResult para los componentes de trayectoria.
  const result: CoupledResult | null = iters.length
    ? { converged: stage === "done", iterations: iters, final_parcelas: [], S: null }
    : null;

  // Palancas del escenario, para el KPIStrip de parámetros.
  const kpis: KPI[] = useMemo(() => {
    const groupColor: Record<string, string> = {
      city: "var(--s2)",
      land_use: "var(--accent)",
      transport: "var(--ink)",
    };
    return describePresetParams(sim, landUseEff).map((p) => ({
      label: tS(p.labelKey),
      value: p.value,
      unit: p.unit,
      color: groupColor[p.group],
    }));
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
        landUseEff.H_por_estrato.reduce((a, b) => a + b, 0)
      ),
    [landUseEff, L, CBD]
  );

  return (
    <div className="page">
      {/* ---------- Sidebar: selección de escenario + controles ---------- */}
      <aside className="sidebar">
        <p className="coupled-sidebar-info">{tS("coupled.lede")}</p>

        <div className="coupled-source-label">{tS("coupled.source_custom_label")}</div>
        <div className="coupled-scenario-list">
          <button
            type="button"
            className={`coupled-preset compact ${isCustom ? "active" : ""}`}
            onClick={() => selectSource(CUSTOM)}
          >
            <div className="coupled-preset-title">{tS("coupled.custom_title")}</div>
            <div className="coupled-preset-desc">{tS("coupled.custom_desc")}</div>
            <div className="coupled-preset-tags">
              <span>{tS("coupled.custom_tag")}</span>
            </div>
          </button>
        </div>

        <div className="coupled-source-label">{tS("coupled.source_preset_label")}</div>
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

        {error && (
          <div className="callout" style={{ borderLeftColor: "var(--metro)", marginTop: 12 }}>
            <strong>{tS("coupled.error")}:</strong> {error}
          </div>
        )}
      </aside>

      {/* ---------- Main: imagen arriba + parámetros + resultados ---------- */}
      <section className="main">
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
            <KPIStrip items={kpis} />
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
                  n="03"
                  title={tS("coupled.convergence_title")}
                  meta={tS("coupled.convergence_meta")}
                  cls="col-12"
                >
                  <p className="coupled-panel-hint">{tS("coupled.convergence_hint")}</p>
                  <OuterTrajectory result={result} />
                </Panel>
              </div>
            )}

            {last && (
              <div className="panel-grid">
                <Panel
                  n="99"
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

            <Interpretation first={first!} last={last!} landUse={landUseEff} tS={tS} />
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

function Comparison({ first, last, supply, tS, stage, iters }: ComparisonProps) {
  // Distribución = oferta S × asignación Q (respeta la forma de la ciudad).
  const firstParcelas = reconstructParcelas(first.land_use.Q, supply);
  const lastParcelas = reconstructParcelas(last.land_use.Q, supply);
  const isSameIter = first.outer_iter === last.outer_iter;

  return (
    <div className="panel-grid">
      <Panel
        n="01"
        title={tS("coupled.without_feedback")}
        meta={tS("coupled.iter_n", { n: first.outer_iter + 1 })}
        cls="col-6"
      >
        <p className="coupled-panel-hint">{tS("coupled.without_feedback_hint")}</p>
        <StratumDistribution parcelas={firstParcelas} />
      </Panel>

      <Panel
        n="02"
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
        <StratumDistribution parcelas={lastParcelas} />
      </Panel>
    </div>
  );
}

interface InterpretationProps {
  first: OuterIteration;
  last: OuterIteration;
  landUse: LandUseConfig;
  tS: (key: string, opts?: Record<string, unknown>) => string;
}

function Interpretation({ first, last, landUse, tS }: InterpretationProps) {
  const alpha = landUse.estratos.map((s) => s.alpha);
  const segFirst = theilSegregation(first.land_use.Q);
  const segLast = theilSegregation(last.land_use.Q);
  const welfFirst = meanUtilityByStratum(first.transport.agentes);
  const welfLast = meanUtilityByStratum(last.transport.agentes);
  const accFirst = accessibilityHansen(first.T_matrix, alpha);
  const accLast = accessibilityHansen(last.T_matrix, alpha);

  const dSeg = segLast - segFirst;
  const dWelfAlto = diff(welfLast[0], welfFirst[0]);
  const dWelfBajo = diff(welfLast[2], welfFirst[2]);
  const dAccAlto = diff(accLast[0], accFirst[0]);
  const dAccBajo = diff(accLast[2], accFirst[2]);

  const highlights: Array<{ title: string; body: string }> = [];

  if (Math.abs(dSeg) > 0.01) {
    highlights.push({
      title: tS("coupled.interp.segregation_title"),
      body: tS(
        dSeg > 0 ? "coupled.interp.segregation_up" : "coupled.interp.segregation_down",
        { delta: Math.abs(dSeg).toFixed(3) }
      ),
    });
  }
  if (dWelfAlto != null && dWelfBajo != null) {
    const gap = dWelfAlto - dWelfBajo;
    highlights.push({
      title: tS("coupled.interp.welfare_title"),
      body: tS(
        gap > 0 ? "coupled.interp.welfare_regressive" : "coupled.interp.welfare_progressive",
        { alto: fmt(dWelfAlto), bajo: fmt(dWelfBajo) }
      ),
    });
  }
  if (dAccAlto != null && dAccBajo != null) {
    const ratio = dAccAlto !== 0 && dAccBajo !== 0 ? Math.abs(dAccAlto / dAccBajo) : 1;
    highlights.push({
      title: tS("coupled.interp.accessibility_title"),
      body: tS("coupled.interp.accessibility_body", {
        alto: fmt(dAccAlto, 3),
        bajo: fmt(dAccBajo, 3),
        ratio: ratio.toFixed(1),
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

function diff(a: number | null, b: number | null): number | null {
  if (a == null || b == null) return null;
  return a - b;
}

function fmt(v: number, digits = 2): string {
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}`;
}
