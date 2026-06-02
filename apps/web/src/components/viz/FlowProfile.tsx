import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/cn";

interface FlowProfileProps {
  flows: readonly number[];
  largoKm: number;
  label?: string;
  color?: string;
  /** Tope máximo para el eje Y (comparte escala entre paneles). Si no se
   *  entrega, se usa el propio máximo del vector. */
  yMax?: number | null;
  /** Capacidad del corredor — se muestra como pill informativa, NO como línea
   *  sobre la escala (está en unidad distinta: total vs por celda). */
  capacityHint?: string;
  /** Formateo de valores (encabezado "max" y ticks Y). Default: redondeo entero. */
  valueFmt?: (v: number) => string;
  height?: number;
  className?: string;
}

const MARGIN = { top: 16, right: 10, bottom: 18, left: 40 };

/**
 * Perfil de demanda por celda de origen a lo largo de la ciudad.
 *
 * Todo (ejes, ticks, etiquetas, encabezado) se dibuja DENTRO del `<svg>` con
 * ancho medido en píxeles reales — así la figura exporta completa a SVG/PNG y
 * el texto no se deforma. Escala Y: `yMax` compartido entre paneles para
 * comparación visual; si no se entrega, usa el máximo local.
 */
export function FlowProfile({
  flows,
  largoKm,
  label,
  color = "var(--ink)",
  yMax = null,
  capacityHint,
  valueFmt = (v: number) => String(Math.round(v)),
  height = 120,
  className,
}: FlowProfileProps) {
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

  const H = height + MARGIN.top + MARGIN.bottom;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = height;
  const yTop = MARGIN.top;
  const yFloor = MARGIN.top + plotH;

  const { areaPath, linePath, localMax } = useMemo(() => {
    const N = flows.length;
    if (N < 2) return { areaPath: "", linePath: "", localMax: Math.max(...flows, 1) };
    const lMax = Math.max(...flows, 1);
    const scale = yMax != null ? Math.max(yMax, 1) : lMax;
    const xOf = (i: number) => MARGIN.left + (i / (N - 1)) * plotW;
    const yOf = (f: number) => yFloor - (Math.min(f, scale) / scale) * plotH;
    const line: string[] = [];
    flows.forEach((f, i) => {
      line.push(`${i === 0 ? "M" : "L"}${xOf(i).toFixed(2)},${yOf(f).toFixed(2)}`);
    });
    const area = `M${MARGIN.left.toFixed(2)},${yFloor} ${line.join(" ").slice(1)} L${(MARGIN.left + plotW).toFixed(2)},${yFloor} Z`;
    return { areaPath: area, linePath: line.join(" "), localMax: lMax };
  }, [flows, yMax, plotW, plotH, yFloor]);

  const scale = yMax != null ? Math.max(yMax, 1) : localMax;
  const effectiveMax = yMax ?? localMax;
  const ticks = [0, scale / 2, scale];
  const cbdX = MARGIN.left + plotW / 2;

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{ display: "block", maxWidth: "100%", background: "var(--paper-2)", border: "1px solid var(--rule)" }}
        role="img"
        aria-label={label ?? "flujo"}
      >
        {/* Encabezado: label (izq) y max/cap (der) */}
        {label && (
          <text x={MARGIN.left} y={11} textAnchor="start" className="label">
            {label}
          </text>
        )}
        <text x={MARGIN.left + plotW} y={11} textAnchor="end" className="label" style={{ fontVariantNumeric: "tabular-nums" }}>
          {`max ${valueFmt(localMax)}${capacityHint ? ` · cap ${capacityHint}` : ""}`}
        </text>

        {/* Grid + etiquetas Y */}
        {ticks.map((v, i) => {
          const y = yFloor - (v / scale) * plotH;
          return (
            <g key={i}>
              <line
                x1={MARGIN.left}
                y1={y}
                x2={MARGIN.left + plotW}
                y2={y}
                stroke="var(--rule)"
                strokeWidth={0.6}
                strokeDasharray="2 3"
                opacity={0.6}
              />
              <text
                x={MARGIN.left - 6}
                y={y + 3}
                textAnchor="end"
                className="label"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {valueFmt(v)}
              </text>
            </g>
          );
        })}

        {/* CBD vertical */}
        <line
          x1={cbdX}
          y1={yTop}
          x2={cbdX}
          y2={yFloor}
          stroke="var(--accent)"
          strokeWidth={0.8}
          strokeDasharray="2 2"
          opacity={0.6}
        />

        {/* Área + línea */}
        {areaPath && <path d={areaPath} fill={color} opacity={0.2} />}
        {linePath && <path d={linePath} fill="none" stroke={color} strokeWidth={1.2} />}

        {/* Baseline */}
        <line x1={MARGIN.left} y1={yFloor} x2={MARGIN.left + plotW} y2={yFloor} stroke="var(--ink)" strokeWidth={0.8} />

        {/* Etiquetas X */}
        <text x={MARGIN.left} y={H - 5} textAnchor="start" className="label">
          0 KM
        </text>
        <text x={cbdX} y={H - 5} textAnchor="middle" className="label" fill="var(--accent)">
          CBD
        </text>
        <text
          x={MARGIN.left + plotW}
          y={H - 5}
          textAnchor="end"
          className="label"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {largoKm.toFixed(0)} KM
        </text>
      </svg>
      {/* effectiveMax expuesto para tooltips/lectores; no se muestra aparte */}
      <span className="sr-only">{`max ${Math.round(effectiveMax)}`}</span>
    </div>
  );
}
