import { useEffect, useId, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/cn";

interface CityStripProps {
  nCeldas: number;
  largoKm: number;
  pendientePct?: number;
  /** Perfil de tiempos por celda — eje Y (altura) */
  modeProfile?: Array<{ t_auto: number; t_metro: number; t_bici: number }>;
  /** Shares de estratos (A, M, B) — coloreado de barras */
  shareEstratos?: readonly [number, number, number];
  /** Tiempo seleccionado para colorear (auto|metro|bici) */
  heatMode?: "auto" | "metro" | "bici";
  /** Cuando cambia este token, se dispara un flash visual (para indicar "nueva iteración"). */
  iterationToken?: number | string;
  className?: string;
  height?: number;
}

const MARGIN = { top: 12, right: 10, bottom: 26, left: 48 };

/**
 * Visualización SVG de la ciudad lineal. Cada parcela es una barra vertical
 * cuya altura = tiempo de viaje (en minutos) del modo seleccionado. Tiene
 * eje Y rotulado, marcador del CBD y etiquetas de posición en km.
 */
export function CityStrip({
  nCeldas,
  largoKm,
  pendientePct = 0,
  modeProfile,
  heatMode = "auto",
  iterationToken,
  className,
  height = 160,
}: CityStripProps) {
  const gradId = useId();
  const cbdIdx = Math.floor(nCeldas / 2);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(600);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(320, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const [flash, setFlash] = useState(false);
  const prevToken = useRef(iterationToken);
  useEffect(() => {
    if (iterationToken !== undefined && iterationToken !== prevToken.current) {
      prevToken.current = iterationToken;
      setFlash(true);
      const tm = setTimeout(() => setFlash(false), 500);
      return () => clearTimeout(tm);
    }
  }, [iterationToken]);

  const H = height;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;
  const barW = plotW / nCeldas;

  const { bars, maxValue } = useMemo(() => {
    if (!modeProfile) {
      return {
        bars: Array.from({ length: nCeldas }, (_, i) => ({ idx: i, norm: 0, raw: 0 })),
        maxValue: 0,
      };
    }
    const values = modeProfile.map((p) =>
      heatMode === "auto" ? p.t_auto : heatMode === "metro" ? p.t_metro : p.t_bici
    );
    const max = Math.max(...values, 0.1);
    return {
      bars: values.map((v, i) => ({ idx: i, norm: v / max, raw: v })),
      maxValue: max,
    };
  }, [modeProfile, heatMode, nCeldas]);

  // Pendiente: desplaza la línea del "piso" proporcionalmente. Mantiene la
  // intuición visual del original pero dentro del plot area.
  const slopeOffset = (xPct: number) => (pendientePct / 20) * (xPct - 50) * 0.4;

  const yTop = MARGIN.top;
  const yFloor = MARGIN.top + plotH;

  const yTicks = useMemo(() => {
    if (maxValue <= 0) return [0];
    return [0, maxValue / 2, maxValue];
  }, [maxValue]);

  const fmt = (v: number) => (v >= 10 ? v.toFixed(0) : v.toFixed(1));

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className={cn("block transition-colors", flash && "animate-iteration-flash")}
        style={{
          display: "block",
          maxWidth: "100%",
          background: "var(--paper-2)",
          border: `1px solid ${flash ? "var(--accent)" : "var(--rule)"}`,
        }}
        role="img"
        aria-label="Ciudad lineal"
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--metro)" />
            <stop offset="50%" stopColor="var(--auto)" />
            <stop offset="100%" stopColor="var(--bici)" />
          </linearGradient>
        </defs>

        {/* Grid horizontales + etiquetas Y */}
        {yTicks.map((v, i) => {
          const y = yFloor - (v / maxValue) * plotH;
          return (
            <g key={`yt-${i}`}>
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
                {fmt(v)}
              </text>
            </g>
          );
        })}

        {/* Título del eje Y */}
        <text
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
          className="label"
        >
          TIEMPO · MIN
        </text>

        {/* Barras — altura proporcional al tiempo real */}
        {bars.map(({ idx, norm }) => {
          const isCbd = idx === cbdIdx;
          if (isCbd) return null;
          const x = MARGIN.left + idx * barW;
          const barH = Math.max(0.5, norm * plotH);
          const floor = yFloor + slopeOffset(((idx + 0.5) / nCeldas) * 100);
          return (
            <rect
              key={idx}
              x={x}
              y={floor - barH}
              width={Math.max(barW - 0.15, 0.2)}
              height={barH}
              fill={modeProfile ? `url(#${gradId})` : "var(--rule)"}
              opacity={0.85}
              style={{
                transition: "y 400ms ease-out, height 400ms ease-out, fill 400ms ease-out",
              }}
            />
          );
        })}

        {/* Baseline del plot (eje X visual) */}
        <line
          x1={MARGIN.left}
          y1={yFloor}
          x2={MARGIN.left + plotW}
          y2={yFloor}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* CBD marker */}
        {(() => {
          const cbdX = MARGIN.left + (cbdIdx + 0.5) * barW;
          return (
            <g>
              <line
                x1={cbdX}
                y1={yTop}
                x2={cbdX}
                y2={yFloor}
                stroke="var(--accent)"
                strokeWidth={1}
                strokeDasharray="3 3"
              />
              <text
                x={cbdX}
                y={yTop - 2}
                textAnchor="middle"
                className="label"
                fill="var(--accent)"
              >
                CBD
              </text>
            </g>
          );
        })()}

        {/* Etiquetas X: 0 / CBD / L en km */}
        <text x={MARGIN.left} y={H - 8} textAnchor="start" className="label">
          0 KM
        </text>
        <text
          x={MARGIN.left + plotW}
          y={H - 8}
          textAnchor="end"
          className="label"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {largoKm.toFixed(0)} KM
        </text>
      </svg>
    </div>
  );
}
