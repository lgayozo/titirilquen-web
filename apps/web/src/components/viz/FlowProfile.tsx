import { useMemo } from "react";

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
  height?: number;
  className?: string;
}

/**
 * Perfil de demanda por celda de origen a lo largo de la ciudad.
 *
 * Escala Y: `yMax` compartido entre paneles (eje común para permitir
 * comparación visual Auto vs Bici vs Metro). Si no se entrega, usa el máximo
 * local del vector.
 *
 * Incluye regla vertical en el CBD y ticks de eje Y sutiles.
 */
export function FlowProfile({
  flows,
  largoKm,
  label,
  color = "var(--ink)",
  yMax = null,
  capacityHint,
  height = 120,
  className,
}: FlowProfileProps) {
  const { path, linePath, max } = useMemo(() => {
    const N = flows.length;
    if (N === 0) return { path: "", linePath: "", max: 1 };
    const localMax = Math.max(...flows, 1);
    const scale = yMax != null ? Math.max(yMax, 1) : localMax;
    const areaPts: string[] = [];
    const linePts: string[] = [];
    areaPts.push(`M0,100`);
    flows.forEach((f, i) => {
      const x = (i / (N - 1)) * 100;
      const y = 100 - (Math.min(f, scale) / scale) * 92;
      areaPts.push(`L${x.toFixed(2)},${y.toFixed(2)}`);
      linePts.push(`${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`);
    });
    areaPts.push(`L100,100`);
    areaPts.push(`Z`);
    return { path: areaPts.join(" "), linePath: linePts.join(" "), max: localMax };
  }, [flows, yMax]);

  // Ticks Y a 0, 1/2, 1
  const effectiveMax = yMax ?? max;
  const ticks = [0, effectiveMax / 2, effectiveMax];

  return (
    <div className={cn("relative", className)}>
      <div className="mb-1 flex items-baseline justify-between text-[11px]">
        <span className="font-fig uppercase tracking-[0.06em] text-muted">
          {label ?? ""}
        </span>
        <span className="font-fig tabular-nums text-muted">
          max {Math.round(max)}
          {capacityHint && <span className="ml-2 opacity-70">cap {capacityHint}</span>}
        </span>
      </div>

      <div
        className="relative"
        style={{ height, border: "1px solid var(--rule)", background: "var(--paper-2)" }}
      >
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="absolute inset-0 block h-full w-full"
        >
          {/* Grid-lines horizontales */}
          {ticks.map((_, i) => {
            const y = 100 - (i / (ticks.length - 1)) * 92 - 4;
            return (
              <line
                key={i}
                x1={0}
                y1={y}
                x2={100}
                y2={y}
                stroke="var(--rule)"
                strokeWidth={0.25}
                strokeDasharray="1 2"
                opacity={0.7}
              />
            );
          })}

          {/* CBD vertical */}
          <line
            x1={50}
            y1={0}
            x2={50}
            y2={100}
            stroke="var(--accent)"
            strokeWidth={0.4}
            strokeDasharray="1 1"
            opacity={0.5}
          />

          {/* Área */}
          <path d={path} fill={color} opacity={0.2} />

          {/* Línea superior */}
          <path d={linePath} fill="none" stroke={color} strokeWidth={0.8} />
        </svg>

        {/* Y-axis labels — absolutos en HTML para que no se deformen con preserveAspectRatio */}
        <div className="pointer-events-none absolute inset-y-0 left-0 flex w-10 flex-col justify-between py-1 pl-1 font-fig text-[9px] tabular-nums text-muted">
          <span>{Math.round(effectiveMax)}</span>
          <span>{Math.round(effectiveMax / 2)}</span>
          <span>0</span>
        </div>
      </div>

      <div className="flex justify-between font-fig text-[10px] uppercase tracking-[0.06em] text-muted">
        <span>0 km</span>
        <span>CBD</span>
        <span>{largoKm.toFixed(0)} km</span>
      </div>
    </div>
  );
}
