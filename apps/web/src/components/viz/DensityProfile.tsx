import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface DensityProfileProps {
  /** Densidad por celda (hab/km) = S_i/Δx, consecuencia de la oferta. */
  densidad: readonly number[];
  className?: string;
  height?: number;
}

const MARGIN = { top: 8, right: 8, bottom: 22, left: 52 };

/**
 * Perfil de densidad por celda a lo largo del corredor. Es una **consecuencia de
 * la oferta**: dens(i) = S_i/Δx (hogares por km), así que sigue la forma de la
 * ciudad (perfil de oferta), no un gradiente geométrico impuesto. Comparte forma
 * con las figuras de población (todas derivan de S). Escala absoluta en hab/km.
 */
export function DensityProfile({
  densidad,
  className,
  height = 160,
}: DensityProfileProps) {
  const { t } = useTranslation("simulator");

  const { max, yTicks } = useMemo(() => {
    const finite = densidad.filter(Number.isFinite);
    const mx = finite.length ? Math.max(...finite) : 1;
    const top = Math.max(mx, 1e-6);
    return {
      max: top,
      yTicks: [0, top * 0.25, top * 0.5, top * 0.75, top],
    };
  }, [densidad]);

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
    MARGIN.left + (i / Math.max(densidad.length - 1, 1)) * plotW;
  const yOf = (v: number) =>
    MARGIN.top + plotH - (Math.max(v, 0) / max) * plotH;

  const pathD = densidad
    .map((v, i) =>
      i === 0
        ? `M${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`
        : `L${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`,
    )
    .join(" ");
  const areaD =
    `${pathD} L${xOf(densidad.length - 1).toFixed(2)},${(MARGIN.top + plotH).toFixed(2)}` +
    ` L${xOf(0).toFixed(2)},${(MARGIN.top + plotH).toFixed(2)} Z`;

  const fmt = (v: number) => (v >= 100 ? v.toFixed(0) : v.toFixed(1));

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{ display: "block", maxWidth: "100%" }}
      >
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

        <path d={areaD} fill="var(--accent)" opacity={0.12} />
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

        <line
          x1={MARGIN.left}
          y1={MARGIN.top + plotH}
          x2={MARGIN.left + plotW}
          y2={MARGIN.top + plotH}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

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

        <text
          className="label"
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
        >
          {t("land_use.density_y_label")}
        </text>
      </svg>
    </div>
  );
}
