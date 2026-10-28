import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cityShapeWeights } from "@/lib/citySupply";
import { cn } from "@/lib/cn";
import { fmtDecimal, fmtEntero } from "@/lib/modos";
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
  /** Largo de la ciudad (km) y hogares totales (ΣH). Con los dos, la figura
   *  muestra un tooltip por celda con su oferta en hogares, como la figura de
   *  la ciudad de Transporte; sin ellos se comporta como antes. */
  largoKm?: number;
  hogares?: number;
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
  largoKm,
  hogares,
}: CityShapePreviewProps) {
  const { t } = useTranslation("simulator");
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
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
  const wSum = useMemo(() => weights.reduce((a, b) => a + b, 0), [weights]);

  const H = 150;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;
  const yFloor = MARGIN.top + plotH;
  const barW = plotW / L;
  const cbdX = MARGIN.left + (CBD + 0.5) * barW;

  // Una sola capa de captura, como en StratumDistribution. La oferta de la
  // celda en hogares es w_i/Σw·ΣH: la misma normalización de `smoothSupply`,
  // que la página usa para colocar los hogares en la Fig. 01.
  const conTooltip = largoKm != null && hogares != null;
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const svg = svgRef.current;
    if (!svg || L === 0) return;
    const r = svg.getBoundingClientRect();
    // El SVG se escala con maxWidth:100%: px del puntero → coordenadas del viewBox.
    const xView = ((e.clientX - r.left) * W) / Math.max(r.width, 1);
    const i = Math.floor((xView - MARGIN.left) / barW);
    setHoverIdx(i >= 0 && i < L ? i : null);
  };
  const cellKm = largoKm != null && L > 0 ? largoKm / L : 0;
  const hoverX = hoverIdx != null ? MARGIN.left + (hoverIdx + 0.5) * barW : 0;
  const hoverS =
    hoverIdx != null && hogares != null && wSum > 0
      ? ((weights[hoverIdx] ?? 0) / wSum) * hogares
      : 0;

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        ref={svgRef}
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
        aria-label={t("land_use.shape_aria")}
      >
        {/* Eje Y (rótulo) */}
        <text
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
          className="label"
        >
          {t("land_use.shape_y_axis")}
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

        {/* Guía de la celda bajo el puntero */}
        {hoverIdx != null && (
          <line
            x1={hoverX}
            y1={MARGIN.top}
            x2={hoverX}
            y2={yFloor}
            stroke="var(--ink)"
            strokeWidth={0.8}
            opacity={0.5}
          />
        )}

        {/* Etiquetas X */}
        <text x={MARGIN.left} y={H - 8} textAnchor="start" className="label">
          {t("network.periphery")}
        </text>
        <text
          x={MARGIN.left + plotW}
          y={H - 8}
          textAnchor="end"
          className="label"
        >
          {t("network.periphery")}
        </text>

        {/* Capa de captura del puntero, encima de todo. */}
        {conTooltip && (
          <rect
            x={MARGIN.left}
            y={MARGIN.top}
            width={plotW}
            height={plotH}
            fill="transparent"
            onMouseMove={onMove}
            onMouseLeave={() => setHoverIdx(null)}
          />
        )}
      </svg>

      {/* Tooltip como HTML, con el estilo del de StratumDistribution. */}
      {conTooltip && hoverIdx != null && (
        <div
          className="pointer-events-none absolute z-10"
          style={{
            left: Math.min(Math.max(hoverX, 92), Math.max(W - 92, 92)),
            top: MARGIN.top + 4,
            transform: "translateX(-50%)",
            background: "var(--panel)",
            border: "1px solid var(--rule)",
            borderRadius: 7,
            padding: "6px 8px",
            fontFamily: "var(--font-fig)",
            fontSize: "var(--fs-etiqueta)",
            lineHeight: 1.5,
            whiteSpace: "nowrap",
            color: "var(--ink)",
          }}
        >
          <div style={{ color: "var(--muted)" }}>
            {t("stratum_distribution.tooltip_pos", {
              km: fmtDecimal((hoverIdx + 0.5) * cellKm),
              dist: fmtDecimal(Math.abs(CBD - hoverIdx) * cellKm),
            })}
          </div>
          <div style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
            {hoverIdx === CBD
              ? t("land_use.shape_tooltip_cbd")
              : t("land_use.shape_tooltip_oferta", { n: fmtEntero(hoverS) })}
          </div>
        </div>
      )}
    </div>
  );
}
