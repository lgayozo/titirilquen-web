import { useMemo } from "react";

import { cn } from "@/lib/cn";

interface BPRCurveProps {
  alpha: number;
  beta: number;
  /** Posición del operating point sobre la curva (q/C). */
  operatingRatio?: number | null;
  className?: string;
}

/**
 * Curva BPR t/t0 = 1 + α·(q/C)^β. Pedagógica: muestra cómo el tiempo se
 * dispara al superar la capacidad. El "operating point" marca dónde opera
 * el sistema con la demanda actual.
 */
export function BPRCurve({ alpha, beta, operatingRatio = null, className }: BPRCurveProps) {
  const points = useMemo(() => {
    const N = 100;
    const maxRatio = 1.6;
    return Array.from({ length: N + 1 }, (_, i) => {
      const q = (i / N) * maxRatio;
      const t = 1 + alpha * Math.pow(q, beta);
      return { q, t };
    });
  }, [alpha, beta]);

  const yMax = Math.max(...points.map((p) => p.t), 2);
  const xMax = 1.6;

  const svgW = 200;
  const svgH = 120;
  const pad = { top: 10, right: 12, bottom: 22, left: 28 };
  const plotW = svgW - pad.left - pad.right;
  const plotH = svgH - pad.top - pad.bottom;

  const xScale = (q: number) => pad.left + (q / xMax) * plotW;
  const yScale = (t: number) => pad.top + plotH - (Math.min(t, yMax) / yMax) * plotH;

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${xScale(p.q)},${yScale(p.t)}`).join(" ");

  const opT = operatingRatio != null ? 1 + alpha * Math.pow(operatingRatio, beta) : null;

  return (
    <svg
      viewBox={`0 0 ${svgW} ${svgH}`}
      className={cn("block w-full", className)}
      role="img"
      aria-label="Curva BPR"
    >
      {/* Capacity = 1 line */}
      <line
        x1={xScale(1)}
        y1={pad.top}
        x2={xScale(1)}
        y2={pad.top + plotH}
        stroke="currentColor"
        strokeWidth={0.5}
        strokeDasharray="2 2"
        opacity={0.4}
      />
      <text
        x={xScale(1)}
        y={pad.top - 2}
        fontSize={7}
        textAnchor="middle"
        className="fill-slate-500"
      >
        q/C=1
      </text>

      {/* Axes */}
      <line
        x1={pad.left}
        y1={pad.top + plotH}
        x2={pad.left + plotW}
        y2={pad.top + plotH}
        className="stroke-slate-400"
        strokeWidth={0.5}
      />
      <line
        x1={pad.left}
        y1={pad.top}
        x2={pad.left}
        y2={pad.top + plotH}
        className="stroke-slate-400"
        strokeWidth={0.5}
      />

      <path d={path} className="fill-none stroke-slate-900 dark:stroke-slate-100" strokeWidth={1.2} />

      {opT != null && (
        <g>
          <circle cx={xScale(operatingRatio!)} cy={yScale(opT)} r={2.5} className="fill-red-500" />
        </g>
      )}

      {/* Axis labels */}
      <text x={pad.left + plotW / 2} y={svgH - 4} fontSize={7} textAnchor="middle" className="fill-slate-500">
        q / C
      </text>
      <text
        x={8}
        y={pad.top + plotH / 2}
        fontSize={7}
        textAnchor="middle"
        className="fill-slate-500"
        transform={`rotate(-90, 8, ${pad.top + plotH / 2})`}
      >
        t / t₀
      </text>
    </svg>
  );
}
