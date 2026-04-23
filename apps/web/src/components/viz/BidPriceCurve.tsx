import { useMemo } from "react";

import { cn } from "@/lib/cn";

interface BidPriceCurveProps {
  p: readonly number[];
  className?: string;
  height?: number;
}

const MARGIN = { top: 8, right: 8, bottom: 22, left: 48 };

/**
 * Precios implícitos por parcela en el equilibrio. Curva con eje Y rotulado
 * en la misma unidad del precio y marcador vertical del CBD.
 */
export function BidPriceCurve({ p, className, height = 160 }: BidPriceCurveProps) {
  const { path, min, max, yTicks } = useMemo(() => {
    const finite = p.filter(Number.isFinite);
    const mn = finite.length ? Math.min(...finite) : 0;
    const mx = finite.length ? Math.max(...finite) : 1;
    const range = Math.max(mx - mn, 1e-6);
    const ticks = [mn, mn + range * 0.25, mn + range * 0.5, mn + range * 0.75, mx];
    return { path: { p, mn, mx, range }, min: mn, max: mx, yTicks: ticks };
  }, [p]);

  const W = 600;
  const H = height;
  const plotW = W - MARGIN.left - MARGIN.right;
  const plotH = H - MARGIN.top - MARGIN.bottom;

  const xOf = (i: number) => MARGIN.left + (i / Math.max(path.p.length - 1, 1)) * plotW;
  const yOf = (v: number) =>
    MARGIN.top + plotH - ((v - path.mn) / path.range) * plotH;

  const pathD = path.p
    .map((v, i) => (i === 0 ? `M${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}` : `L${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`))
    .join(" ");

  const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1));

  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="block w-full"
        style={{ height }}
      >
        {/* Grid + Y labels */}
        {yTicks.map((v, i) => {
          const y = yOf(v);
          return (
            <g key={i}>
              <line
                className="grid-line"
                x1={MARGIN.left}
                y1={y}
                x2={MARGIN.left + plotW}
                y2={y}
              />
              <text
                className="label"
                x={MARGIN.left - 6}
                y={y + 3}
                textAnchor="end"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {fmt(v)}
              </text>
            </g>
          );
        })}

        {/* Curve */}
        <path d={pathD} fill="none" stroke="var(--accent)" strokeWidth={1.5} />

        {/* CBD vertical */}
        <line
          x1={MARGIN.left + plotW / 2}
          y1={MARGIN.top}
          x2={MARGIN.left + plotW / 2}
          y2={MARGIN.top + plotH}
          stroke="var(--ink)"
          strokeWidth={0.8}
          strokeDasharray="3 3"
          opacity={0.5}
        />

        {/* X axis baseline */}
        <line
          x1={MARGIN.left}
          y1={MARGIN.top + plotH}
          x2={MARGIN.left + plotW}
          y2={MARGIN.top + plotH}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* X labels */}
        <text className="label" x={MARGIN.left} y={H - 6} textAnchor="start">
          0
        </text>
        <text
          className="label"
          x={MARGIN.left + plotW / 2}
          y={H - 6}
          textAnchor="middle"
          fill="var(--accent)"
        >
          CBD
        </text>
        <text
          className="label"
          x={MARGIN.left + plotW}
          y={H - 6}
          textAnchor="end"
        >
          L
        </text>

        {/* Y-axis title */}
        <text
          className="label"
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
        >
          PRECIO IMPLÍCITO
        </text>
      </svg>

      <div
        style={{
          marginTop: 4,
          fontFamily: "var(--font-fig)",
          fontSize: 10,
          color: "var(--muted)",
          letterSpacing: "0.04em",
          fontVariantNumeric: "tabular-nums",
          textAlign: "right",
        }}
      >
        RANGO [{fmt(min)}, {fmt(max)}]
      </div>
    </div>
  );
}
