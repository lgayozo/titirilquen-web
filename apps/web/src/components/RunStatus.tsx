import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { IterationSnapshot, Modo } from "@/lib/types";

interface RunStatusProps {
  current: number;
  total: number;
  lastIter?: IterationSnapshot;
  stage: "booting" | "running" | "done" | "idle" | "error";
  engine: "api" | "local";
  className?: string;
}

const MODE_CSS_VAR: Record<Modo, string> = {
  Auto: "var(--auto)",
  Metro: "var(--metro)",
  Bici: "var(--bici)",
  Caminata: "var(--walk)",
  Teletrabajo: "var(--tele)",
};

const MODES: Modo[] = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"];

/**
 * Indicador rico durante una corrida, en estética editorial paper/ink.
 *  - Fase textual en mono caps
 *  - Iteration-flash (box-shadow accent) al llegar nueva iteración
 *  - Modal split apilado con colores de --auto/--metro/--bici/--walk/--tele
 *  - Residuo con tendencia ↓ (converging, bici-green) / ↑ (diverging, accent)
 *  - Barra de progreso fina
 */
export function RunStatus({ current, total, lastIter, stage, engine, className }: RunStatusProps) {
  const { t } = useTranslation("simulator");
  const [flash, setFlash] = useState(false);
  const prevIter = useRef(-1);
  const prevResidual = useRef<number | null>(null);

  useEffect(() => {
    if (lastIter && lastIter.iter !== prevIter.current) {
      prevIter.current = lastIter.iter;
      setFlash(true);
      const tm = setTimeout(() => setFlash(false), 500);
      return () => clearTimeout(tm);
    }
  }, [lastIter]);

  const pct = total > 0 ? Math.min(100, (current / total) * 100) : 0;

  const phaseLabel = (() => {
    if (stage === "booting") {
      return engine === "local"
        ? t("run_status.booting_pyodide")
        : t("run_status.connecting_api");
    }
    if (stage === "running") {
      if (current === 0) return t("run_status.generating_population");
      if (current === total) return t("run_status.smoothing_final");
      return t("run_status.iterating");
    }
    if (stage === "done") return t("equilibrium.converged");
    return "";
  })();

  const residual = lastIter?.residuo ?? null;
  const trend: "down" | "up" | "same" | null =
    residual == null
      ? null
      : prevResidual.current == null
      ? null
      : residual < prevResidual.current - 1e-6
      ? "down"
      : residual > prevResidual.current + 1e-6
      ? "up"
      : "same";
  if (residual != null && prevResidual.current !== residual) {
    prevResidual.current = residual;
  }

  const totalAgents = lastIter
    ? MODES.reduce((s, m) => s + (lastIter.modal_split[m] ?? 0), 0)
    : 0;

  const dotColor =
    stage === "done"
      ? "var(--bici)"
      : stage === "error"
      ? "var(--metro)"
      : "var(--accent)";

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy={stage === "running" || stage === "booting"}
      className={cn(
        "run-status",
        flash && "run-status--flash",
        className
      )}
    >
      <div className="run-status-head">
        <div className="run-status-phase">
          <span
            className={cn(
              "run-status-dot",
              (stage === "running" || stage === "booting") && "animate-pulse-dot"
            )}
            style={{ backgroundColor: dotColor }}
            aria-hidden
          />
          <span className="run-status-counter">
            {t("equilibrium.iteration", { n: current, total })}
          </span>
          {phaseLabel && <span className="run-status-sub">· {phaseLabel}</span>}
        </div>

        {residual != null && (
          <div className="run-status-residual">
            <div className="run-status-residual-label">{t("equilibrium.residual")}</div>
            <div className="run-status-residual-value">
              <span className="num">{residual.toFixed(3)}</span>
              {trend === "down" && (
                <span
                  className="trend trend-down"
                  title={t("run_status.converging")}
                  aria-label={t("run_status.converging")}
                >
                  ↓
                </span>
              )}
              {trend === "up" && (
                <span
                  className="trend trend-up"
                  title={t("run_status.diverging")}
                  aria-label={t("run_status.diverging")}
                >
                  ↑
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      <div
        role="progressbar"
        aria-valuenow={current}
        aria-valuemin={0}
        aria-valuemax={total}
        className="run-status-progress"
      >
        <div className="run-status-progress-fill" style={{ width: `${pct}%` }} />
      </div>

      {lastIter && totalAgents > 0 && (
        <div className="run-status-split">
          <div className="run-status-split-head">
            <span>{t("sandbox.modal_split_last")}</span>
            <span className="num">{totalAgents.toLocaleString()}</span>
          </div>
          <div
            className="run-status-split-bar"
            role="img"
            aria-label={t("sandbox.modal_split_last")}
          >
            {MODES.map((m) => {
              const n = lastIter.modal_split[m] ?? 0;
              const w = (n / totalAgents) * 100;
              if (w < 0.1) return null;
              return (
                <div
                  key={m}
                  className="run-status-split-seg"
                  style={{ width: `${w}%`, backgroundColor: MODE_CSS_VAR[m] }}
                  title={`${t(`modes.${m.toLowerCase()}`)}: ${n} (${w.toFixed(1)}%)`}
                >
                  {w > 7 && (
                    <span className="run-status-split-label">{w.toFixed(0)}%</span>
                  )}
                </div>
              );
            })}
          </div>
          <div className="run-status-split-legend">
            {MODES.map((m) => {
              const n = lastIter.modal_split[m] ?? 0;
              if (n === 0) return null;
              return (
                <span key={m} className="run-status-legend-item">
                  <span
                    className="sw"
                    style={{ backgroundColor: MODE_CSS_VAR[m] }}
                    aria-hidden
                  />
                  <span className="name">{t(`modes.${m.toLowerCase()}`)}</span>
                  <span className="num">{n.toLocaleString()}</span>
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
