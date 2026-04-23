import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Panel } from "@/components/ui/Panel";
import { CoupledMetrics } from "@/components/viz/CoupledMetrics";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { solveCoupledStream } from "@/lib/api-v2";
import { JOINT_PRESETS, applyJointPreset } from "@/lib/joint-presets";
import {
  accessibilityHansen,
  meanUtilityByStratum,
  theilSegregation,
} from "@/lib/metrics";
import type { CoupledResult, LandUseConfig, OuterIteration } from "@/lib/types-v2";

type Stage = "idle" | "running" | "done" | "error";

/**
 * Página dedicada al loop acoplado: storytelling "sin feedback" vs "con
 * feedback". Permite al estudiante seleccionar un escenario conjunto
 * (ciudad + política + suelo) y comparar el equilibrio ingenuo (iter 0,
 * donde land use no sabe de transporte) con el equilibrio acoplado (iter N,
 * donde suelo y transporte se reconcilian).
 */
export function CoupledPage() {
  const { t: tC } = useTranslation("common");
  const { t: tS } = useTranslation("simulator");

  const [presetKey, setPresetKey] = useState<string>(JOINT_PRESETS[0]!.key);
  const [outerMaxIter, setOuterMaxIter] = useState(4);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [iters, setIters] = useState<OuterIteration[]>([]);

  const preset = JOINT_PRESETS.find((p) => p.key === presetKey) ?? JOINT_PRESETS[0]!;
  const { sim, landUse } = useMemo(() => applyJointPreset(preset), [preset]);

  const handleRun = async () => {
    setStage("running");
    setError(null);
    setIters([]);
    const collected: OuterIteration[] = [];
    try {
      await solveCoupledStream(
        { sim, land_use: landUse, outer_max_iter: outerMaxIter, outer_tol: 1.0 },
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

  const first = iters[0] ?? null;
  const last = iters[iters.length - 1] ?? null;
  const result: CoupledResult | null = iters.length
    ? {
        converged: last != null && last.T_residual != null && last.T_residual < 1.0,
        iterations: iters,
        final_parcelas: [],
        S: null,
      }
    : null;

  return (
    <div className="coupled-page">
      <section className="coupled-hero">
        <div className="about-eyebrow">{tS("coupled.eyebrow")}</div>
        <h1 className="coupled-title">{tS("coupled.title")}</h1>
        <p className="coupled-lede">{tS("coupled.lede")}</p>
      </section>

      <section className="coupled-controls">
        <div className="coupled-preset-grid">
          {JOINT_PRESETS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`coupled-preset ${presetKey === p.key ? "active" : ""}`}
              onClick={() => setPresetKey(p.key)}
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

        <div className="coupled-actions">
          <label className="coupled-iter-input">
            <span>{tS("land_use.outer_iter_label")}</span>
            <input
              type="range"
              min={2}
              max={6}
              step={1}
              value={outerMaxIter}
              onChange={(e) => setOuterMaxIter(Number(e.target.value))}
            />
            <span className="num">{outerMaxIter}</span>
          </label>

          <button
            type="button"
            className="btn primary"
            onClick={handleRun}
            disabled={stage === "running"}
          >
            {stage === "running" ? tS("coupled.running") : tS("coupled.run")}
          </button>
        </div>

        {error && (
          <div className="coupled-error">
            <strong>{tS("coupled.error")}:</strong> {error}
          </div>
        )}
      </section>

      {iters.length > 0 && (
        <section className="coupled-results">
          <Comparison
            first={first!}
            last={last!}
            landUseConfig={landUse}
            tS={tS}
            stage={stage}
            iters={iters.length}
          />

          {result && (
            <div className="panel-grid">
              <Panel
                n="99"
                title={tS("coupled_metrics.header")}
                meta={`${iters.length} iter · Theil · welfare · Hansen`}
                cls="col-12"
              >
                <CoupledMetrics result={result} landUseConfig={landUse} />
              </Panel>
            </div>
          )}

          <Interpretation first={first!} last={last!} landUse={landUse} tS={tS} />
        </section>
      )}

      {iters.length === 0 && stage !== "running" && (
        <div className="coupled-placeholder">{tS("coupled.placeholder")}</div>
      )}

      {stage === "running" && iters.length === 0 && (
        <div className="coupled-placeholder">{tS("coupled.booting")}</div>
      )}
    </div>
  );
}

interface ComparisonProps {
  first: OuterIteration;
  last: OuterIteration;
  landUseConfig: LandUseConfig;
  tS: (key: string, opts?: Record<string, unknown>) => string;
  stage: Stage;
  iters: number;
}

function Comparison({ first, last, landUseConfig, tS, stage, iters }: ComparisonProps) {
  const firstParcelas = approximateParcelasFromQ(first.land_use.Q);
  const lastParcelas = approximateParcelasFromQ(last.land_use.Q);
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

function approximateParcelasFromQ(Q: number[][]): number[][] {
  const nStrata = Q.length;
  const I = Q[0]?.length ?? 0;
  const parcelas: number[][] = Array.from({ length: I }, () => []);
  for (let i = 0; i < I; i++) {
    let bestH = -1;
    let bestV = -Infinity;
    for (let h = 0; h < nStrata; h++) {
      const v = Q[h]?.[i] ?? 0;
      if (v > bestV) {
        bestV = v;
        bestH = h;
      }
    }
    if (bestH >= 0 && bestV > 0) {
      parcelas[i]!.push(bestH + 1);
    }
  }
  return parcelas;
}
