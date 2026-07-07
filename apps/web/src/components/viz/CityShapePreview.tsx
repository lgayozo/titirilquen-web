import { useEffect, useMemo, useRef, useState } from "react";

import { cityShapeWeights } from "@/lib/citySupply";
import { cn } from "@/lib/cn";
import type { FormaOferta } from "@/lib/types-v2";

interface CityShapePreviewProps {
  forma: FormaOferta;
  /** nº de celdas (= simConfig.city.n_celdas) */
  L: number;
  /** índice del CBD (centro) */
  CBD: number;
  sigmaFrac: number;
  formaParam: number;
  className?: string;
}

const MARGIN = { top: 16, right: 14, bottom: 26, left: 44 };

/**
 * Vista previa de la **forma de la ciudad** (oferta de vivienda) antes de
 * resolver el equilibrio. Barras por celda con la densidad de oferta, CBD
 * marcado. Se actualiza en vivo al cambiar forma · σ · separación.
 */
export function CityShapePreview({
  forma,
  L,
  CBD,
  sigmaFrac,
  formaParam,
  className,
}: CityShapePreviewProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(800);

  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(360, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const weights = useMemo(
    () => cityShapeWeights(forma, L, CBD, sigmaFrac, formaParam),
    [forma, L, CBD, sigmaFrac, formaParam],
  );
  const wMax = useMemo(() => Math.max(...weights, 1e-9), [weights]);

  const H = 150;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;
  const yFloor = MARGIN.top + plotH;
  const barW = plotW / L;
  const cbdX = MARGIN.left + (CBD + 0.5) * barW;

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{
          display: "block",
          maxWidth: "100%",
          background: "var(--paper-2)",
          border: "1px solid var(--rule)",
        }}
        role="img"
        aria-label="Forma de la ciudad — oferta de vivienda"
      >
        {/* Eje Y (rótulo) */}
        <text
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
          className="label"
        >
          OFERTA
        </text>

        {/* Barras de densidad de oferta por celda */}
        {weights.map((v, i) => {
          if (i === CBD) return null;
          const barH = Math.max(0, (v / wMax) * plotH);
          return (
            <rect
              key={i}
              x={MARGIN.left + i * barW}
              y={yFloor - barH}
              width={Math.max(barW - 0.2, 0.3)}
              height={barH}
              // Ciudad vacía: oferta de vivienda (capacidad) sin estratos aún.
              // Gris neutro — NO un color de estrato ni de modo; la Fig. 01
              // colorea esta misma silueta por estrato.
              fill="var(--muted)"
              opacity={0.8}
              style={{ transition: "y 200ms ease-out, height 200ms ease-out" }}
            />
          );
        })}

        {/* Baseline */}
        <line
          x1={MARGIN.left}
          y1={yFloor}
          x2={MARGIN.left + plotW}
          y2={yFloor}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* CBD marker */}
        <line
          x1={cbdX}
          y1={MARGIN.top}
          x2={cbdX}
          y2={yFloor}
          stroke="var(--accent)"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
        <text
          x={cbdX}
          y={MARGIN.top - 2}
          textAnchor="middle"
          className="label"
          fill="var(--accent)"
        >
          CBD
        </text>

        {/* Etiquetas X */}
        <text x={MARGIN.left} y={H - 8} textAnchor="start" className="label">
          PERIFERIA
        </text>
        <text
          x={MARGIN.left + plotW}
          y={H - 8}
          textAnchor="end"
          className="label"
        >
          PERIFERIA
        </text>
      </svg>
    </div>
  );
}
