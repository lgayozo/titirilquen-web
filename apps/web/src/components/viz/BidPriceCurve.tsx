import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface BidPriceCurveProps {
  p: readonly number[];
  /** Solver de suelo que produjo `p` — define las unidades de la nota al pie:
   * `logit` puja en $ (WTP); `heteroscedastic` score en utiles (no convertible a $). */
  solver?: "heteroscedastic" | "logit";
  className?: string;
  height?: number;
}

const MARGIN = { top: 8, right: 8, bottom: 22, left: 52 };

/**
 * Precio implícito del suelo por parcela en el equilibrio. El precio está
 * definido **salvo una constante aditiva** (la normalización u[0]=0 fija un cero
 * arbitrario), así que solo el *gradiente* tiene sentido. Para no mostrar
 * negativos confusos, se grafica **relativo** al mínimo (periferia = 0); la
 * forma de la curva es idéntica.
 */
export function BidPriceCurve({
  p,
  solver,
  className,
  height = 160,
}: BidPriceCurveProps) {
  const { t } = useTranslation("simulator");
  const { path, max, yTicks } = useMemo(() => {
    const finite = p.filter(Number.isFinite);
    const mn = finite.length ? Math.min(...finite) : 0;
    const mx = finite.length ? Math.max(...finite) : 1;
    const range = Math.max(mx - mn, 1e-6);
    // Relativo al mínimo: periferia ≈ 0, CBD = Δ máximo.
    const pr = p.map((v) => (Number.isFinite(v) ? v - mn : v));
    const ticks = [0, range * 0.25, range * 0.5, range * 0.75, range];
    return {
      path: { p: pr, mn: 0, mx: range, range },
      max: range,
      yTicks: ticks,
    };
  }, [p]);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(600);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(240, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const H = height;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;

  const xOf = (i: number) =>
    MARGIN.left + (i / Math.max(path.p.length - 1, 1)) * plotW;
  const yOf = (v: number) =>
    MARGIN.top + plotH - ((v - path.mn) / path.range) * plotH;

  const pathD = path.p
    .map((v, i) =>
      i === 0
        ? `M${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`
        : `L${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`,
    )
    .join(" ");

  const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1));

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{ display: "block", maxWidth: "100%" }}
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
          {t("bid_price.y_label")}
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
        {t("bid_price.footer", { delta: fmt(max) })}
        {solver && (
          <>
            <br />
            {t(`bid_price.units_${solver}`)}
          </>
        )}
      </div>
    </div>
  );
}
