import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface SimulationSkeletonProps {
  nCeldas: number;
  className?: string;
}

/**
 * Placeholder animado mientras corre la primera iteración del MSA.
 *
 * Estética editorial: barras accent pulsantes con retraso proporcional a la
 * distancia al CBD — visualmente sugiere agentes convergiendo al centro. El
 * CBD se marca con una barra `--ink` sólida. Flechas mono acompañan la
 * narrativa "hacia el centro".
 */
export function SimulationSkeleton({ nCeldas, className }: SimulationSkeletonProps) {
  const { t } = useTranslation("simulator");
  const nBars = Math.min(nCeldas, 60);
  const cbdBar = Math.floor(nBars / 2);

  return (
    <div
      className={cn("sim-skeleton", className)}
      aria-busy="true"
      role="status"
    >
      <div className="sim-skeleton-frame">
        <div className="sim-skeleton-bars">
          {Array.from({ length: nBars }).map((_, i) => {
            const dist = Math.abs(i - cbdBar);
            const delay = dist * 60;
            const heightPct = 20 + (1 - dist / cbdBar) * 50;
            const isCbd = i === cbdBar;
            return (
              <div
                key={i}
                className={cn("sim-skeleton-bar", isCbd && "sim-skeleton-bar--cbd")}
                style={{
                  height: `${heightPct}%`,
                  animationDelay: isCbd ? undefined : `${delay}ms`,
                }}
              />
            );
          })}
        </div>
        <div className="sim-skeleton-arrows" aria-hidden>
          <span>→</span>
          <span className="sim-skeleton-cbd-tag">CBD</span>
          <span>←</span>
        </div>
      </div>

      <p className="sim-skeleton-hint">{t("run_status.skeleton_hint")}</p>
    </div>
  );
}
