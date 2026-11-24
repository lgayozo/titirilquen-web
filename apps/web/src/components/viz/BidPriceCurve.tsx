import { ticks } from "d3";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import { fmtDecimal, fmtEntero } from "@/lib/modos";

interface BidPriceCurveProps {
  p: readonly number[];
  className?: string;
  height?: number;
  /** Largo de la ciudad (km). Activa el tooltip por parcela, como en la
   *  figura de la ciudad de Transporte; sin él la curva no responde al hover. */
  largoKm?: number;
}

// left 70 y top 12: con 12 px (B2) un tick de seis cifras («133165») pisaba el
// título del eje y el de arriba se salía del SVG.
const MARGIN = { top: 12, right: 8, bottom: 22, left: 70 };

/**
 * Precio esperado del suelo por parcela en el equilibrio, el p*_i de Martínez
 * (4.27): el máximo esperado de las pujas, en $/mes. El precio está
 * definido **salvo una constante aditiva** (la normalización u[0]=0 fija un cero
 * arbitrario), así que solo el *gradiente* tiene sentido. Para no mostrar
 * negativos confusos, se grafica **relativo al mínimo**; la forma de la curva
 * es idéntica.
 *
 * **La celda del CBD se excluye.** Es la única sin oferta de vivienda
 * (`S_CBD = 0`), así que ahí la densidad vale cero y la accesibilidad es la
 * mejor de la ciudad por construcción: da un pico de precio en el único punto
 * donde nadie puede vivir. Dejarlo dentro deformaba la escala —llegó a
 * ocupar la mitad del alto del gráfico— y ponía el máximo de la curva en una
 * parcela vacía. Se corta el trazo ahí, que es lo honesto: no hay mercado de
 * suelo residencial sobre el centro de negocios.
 *
 * El docstring anterior afirmaba «periferia = 0, CBD = Δ máximo» como un hecho.
 * Es lo que predice el modelo de Alonso, pero era **falso** con la calibración
 * de ρ vigente hasta el 2026-08-24, y la figura lo dibujaba sin advertirlo. El
 * signo hoy lo vigila `test_el_suelo_central_vale_mas_que_el_periferico`; acá
 * no se asume.
 */
export function BidPriceCurve({
  p,
  className,
  height = 160,
  largoKm,
}: BidPriceCurveProps) {
  const { t } = useTranslation("simulator");
  const cbd = Math.floor(p.length / 2);
  const { path, max, yTicks } = useMemo(() => {
    // La escala se calcula SIN el CBD (ver el comentario del componente).
    const finite = p.filter((v, i) => i !== cbd && Number.isFinite(v));
    const mn = finite.length ? Math.min(...finite) : 0;
    const mx = finite.length ? Math.max(...finite) : 1;
    const range = Math.max(mx - mn, 1e-6);
    const pr = p.map((v, i) =>
      i === cbd || !Number.isFinite(v) ? NaN : v - mn,
    );
    // Marcas 1·2·5×10ⁿ dentro del rango, no cuartos del máximo (33.076, …).
    return {
      path: { p: pr, mn: 0, mx: range, range },
      max: range,
      yTicks: ticks(0, range, 4),
    };
  }, [p, cbd]);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
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

  // Una sola capa de captura, como en StratumDistribution. La curva es una
  // línea de puntos en xOf(i), no barras: la parcela bajo el puntero es la del
  // punto más cercano (round), no la del intervalo (floor).
  const n = path.p.length;
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const svg = svgRef.current;
    if (!svg || n === 0) return;
    const r = svg.getBoundingClientRect();
    // El SVG se escala con maxWidth:100%: px del puntero → coordenadas del viewBox.
    const xView = ((e.clientX - r.left) * W) / Math.max(r.width, 1);
    const i = Math.round(((xView - MARGIN.left) / plotW) * Math.max(n - 1, 1));
    setHoverIdx(i >= 0 && i < n ? i : null);
  };
  const cellKm = largoKm != null && n > 0 ? largoKm / n : 0;
  const hoverV = hoverIdx != null ? path.p[hoverIdx] : undefined;

  // `M` tras cada hueco: el trazo se interrumpe en el CBD en vez de cruzarlo
  // con una recta que insinuaría un precio que no existe.
  let arranca = true;
  const pathD = path.p
    .map((v, i) => {
      if (!Number.isFinite(v)) {
        arranca = true;
        return "";
      }
      const cmd = arranca ? "M" : "L";
      arranca = false;
      return `${cmd}${xOf(i).toFixed(2)},${yOf(v).toFixed(2)}`;
    })
    .filter(Boolean)
    .join(" ");

  // Separador de miles en los enteros, como `fmtInt` de las tablas de
  // transporte: «Δ 133165» se leía mal. Las marcas enteras sin decimales
  // («0», no «0,0»).
  const fmt = (v: number) =>
    Math.abs(v) >= 100 || Number.isInteger(v) ? fmtEntero(v) : fmtDecimal(v);

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        ref={svgRef}
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

        {/* Guía y punto de la parcela bajo el puntero */}
        {hoverIdx != null && (
          <line
            x1={xOf(hoverIdx)}
            y1={MARGIN.top}
            x2={xOf(hoverIdx)}
            y2={MARGIN.top + plotH}
            stroke="var(--ink)"
            strokeWidth={0.8}
            opacity={0.5}
          />
        )}
        {hoverIdx != null && hoverV != null && Number.isFinite(hoverV) && (
          <circle
            cx={xOf(hoverIdx)}
            cy={yOf(hoverV)}
            r={3}
            fill="var(--accent)"
          />
        )}

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

        {/* Capa de captura del puntero, encima de todo. */}
        {largoKm != null && (
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
      {largoKm != null && hoverIdx != null && (
        <div
          className="pointer-events-none absolute z-10"
          style={{
            left: Math.min(Math.max(xOf(hoverIdx), 92), Math.max(W - 92, 92)),
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
              dist: fmtDecimal(Math.abs(cbd - hoverIdx) * cellKm),
            })}
          </div>
          <div style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
            {hoverV != null && Number.isFinite(hoverV)
              ? t("bid_price.tooltip_precio", { v: fmt(hoverV) })
              : t("bid_price.tooltip_cbd")}
          </div>
        </div>
      )}

      <div
        style={{
          marginTop: 4,
          fontSize: "var(--fs-etiqueta)",
          color: "var(--muted)",
          fontVariantNumeric: "tabular-nums",
          textAlign: "right",
        }}
      >
        {t("bid_price.footer", { delta: fmt(max) })}
        <br />
        {/* Las dos ramas (cerrada y HEV) devuelven p*, en $/mes. */}
        {t("bid_price.units_logit")}
      </div>
    </div>
  );
}
