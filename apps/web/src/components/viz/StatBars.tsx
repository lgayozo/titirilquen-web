import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/cn";

export interface StatBar {
  label: string;
  value: number;
  color: string;
}

interface StatBarsProps {
  bars: readonly StatBar[];
  /** Unidad mostrada junto al valor (p. ej. "min"). */
  unit?: string;
  decimals?: number;
  height?: number;
  className?: string;
}

const MARGIN = { top: 16, right: 10, bottom: 28, left: 36 };

/**
 * Barras verticales para estadísticas agregadas (promedios por categoría).
 * Soporta valores con signo: dibuja una línea de cero y las barras crecen
 * hacia arriba (positivos) o hacia abajo (negativos). Cada barra rotula su
 * valor y su categoría.
 */
export function StatBars({ bars, unit, decimals = 1, height = 190, className }: StatBarsProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(360);
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

  const { lo, hi } = useMemo(() => {
    const vals = bars.map((b) => b.value);
    const mx = Math.max(0, ...vals);
    const mn = Math.min(0, ...vals);
    const span = mx - mn || 1;
    return { lo: mn - (mn < 0 ? span * 0.1 : 0), hi: mx + (mx > 0 ? span * 0.14 : 0) };
  }, [bars]);

  const span = hi - lo || 1;
  const yOf = (v: number) => MARGIN.top + plotH - ((v - lo) / span) * plotH;
  const zeroY = yOf(0);

  const n = bars.length || 1;
  const slot = plotW / n;
  const barW = Math.min(56, slot * 0.55);
  const fmt = (v: number) => v.toFixed(decimals);

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{ display: "block", maxWidth: "100%", background: "var(--paper-2)", border: "1px solid var(--rule)" }}
        role="img"
      >
        {/* Línea de cero / baseline */}
        <line
          x1={MARGIN.left}
          y1={zeroY}
          x2={MARGIN.left + plotW}
          y2={zeroY}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {bars.map((b, i) => {
          const cx = MARGIN.left + slot * (i + 0.5);
          const vy = yOf(b.value);
          const top = Math.min(vy, zeroY);
          const h = Math.max(Math.abs(vy - zeroY), 0.5);
          const labelY = b.value >= 0 ? top - 4 : top + h + 11;
          return (
            <g key={i}>
              <rect
                x={cx - barW / 2}
                y={top}
                width={barW}
                height={h}
                fill={b.color}
                opacity={0.85}
                style={{ transition: "y 400ms ease-out, height 400ms ease-out" }}
              />
              <text
                x={cx}
                y={labelY}
                textAnchor="middle"
                className="label"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {fmt(b.value)}
                {unit ? ` ${unit}` : ""}
              </text>
              <text x={cx} y={H - 8} textAnchor="middle" className="label">
                {b.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
