import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

type SingleMode = "auto" | "metro" | "bici" | "caminata";
/** Vistas de la figura: un modo individual, todos los modos a la vez, o el
 *  tiempo de espera del tren por estación. */
export type CityView = SingleMode | "todos" | "espera";

interface ModeTimes {
  t_auto: number;
  t_metro: number;
  t_bici: number;
  t_caminata: number;
  /** Tiempo de espera del metro (escalonado por estación). */
  t_espera: number;
}

interface CityStripProps {
  nCeldas: number;
  largoKm: number;
  pendientePct?: number;
  /** Perfil de tiempos por celda — eje Y (altura) */
  modeProfile?: ModeTimes[];
  /** Shares de estratos (A, M, B) — coloreado de barras */
  shareEstratos?: readonly [number, number, number];
  /** Vista activa; define qué se grafica y el color uniforme de las barras */
  heatMode?: CityView;
  /** Umbral de factibilidad (min) del modo: sobre él las barras se atenúan y se dibuja una línea de corte. */
  cutoffMin?: number;
  /** Etiqueta de la línea de corte (ya traducida). */
  cutoffLabel?: string;
  /** Posiciones (km) de las estaciones de tren — marcadores verticales. */
  estacionesKm?: readonly number[];
  /** Cuando cambia este token, se dispara un flash visual (para indicar "nueva iteración"). */
  iterationToken?: number | string;
  className?: string;
  height?: number;
}

const MARGIN = { top: 12, right: 10, bottom: 26, left: 48 };

/** Color uniforme por modo — el color codifica QUÉ modo se está mostrando. */
const MODE_COLOR: Record<SingleMode, string> = {
  auto: "var(--auto)",
  metro: "var(--metro)",
  bici: "var(--bici)",
  caminata: "var(--walk)",
};

/** Modos incluidos (en orden de apilado de leyenda) en la vista "todos". */
const ALL_MODES: ReadonlyArray<{ mode: SingleMode; key: keyof ModeTimes }> = [
  { mode: "auto", key: "t_auto" },
  { mode: "metro", key: "t_metro" },
  { mode: "bici", key: "t_bici" },
  { mode: "caminata", key: "t_caminata" },
];

const KEY_BY_MODE: Record<SingleMode, keyof ModeTimes> = {
  auto: "t_auto",
  metro: "t_metro",
  bici: "t_bici",
  caminata: "t_caminata",
};

/**
 * Visualización SVG de la ciudad lineal. Según la vista:
 *  - modo individual (auto/metro/bici/caminata): barras de color uniforme cuya
 *    altura = tiempo de viaje (min); con línea de corte de factibilidad.
 *  - "todos": una línea por modo (color del modo) para comparar tiempos.
 *  - "espera": barras del tiempo de espera del metro, escalonado por estación.
 * Tiene eje Y rotulado, marcador del CBD, marcadores de estación y km.
 */
export function CityStrip({
  nCeldas,
  largoKm,
  pendientePct = 0,
  modeProfile,
  heatMode = "auto",
  cutoffMin,
  cutoffLabel,
  estacionesKm,
  iterationToken,
  className,
  height = 160,
}: CityStripProps) {
  const { t } = useTranslation("simulator");
  const cbdIdx = Math.floor(nCeldas / 2);
  const isAll = heatMode === "todos";
  const isEspera = heatMode === "espera";
  const singleColor = isEspera
    ? MODE_COLOR.metro
    : MODE_COLOR[(heatMode as SingleMode) ?? "auto"];

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

  // Series a graficar según la vista, y el máximo del eje Y.
  const { lines, barValues, maxValue } = useMemo(() => {
    if (!modeProfile) {
      return { lines: null, barValues: null as number[] | null, maxValue: 0 };
    }
    if (isAll) {
      const ls = ALL_MODES.map(({ mode, key }) => ({
        mode,
        color: MODE_COLOR[mode],
        values: modeProfile.map((p) => p[key]),
      }));
      const max = Math.max(...ls.flatMap((l) => l.values), 0.1);
      return { lines: ls, barValues: null, maxValue: max };
    }
    const key: keyof ModeTimes = isEspera
      ? "t_espera"
      : KEY_BY_MODE[heatMode as SingleMode];
    const values = modeProfile.map((p) => p[key]);
    const max = Math.max(...values, 0.1);
    return { lines: null, barValues: values, maxValue: max };
  }, [modeProfile, heatMode, isAll, isEspera]);

  // Pendiente: desplaza la línea del "piso" proporcionalmente.
  const slopeOffset = (xPct: number) => (pendientePct / 20) * (xPct - 50) * 0.4;

  const yTop = MARGIN.top;
  const yFloor = MARGIN.top + plotH;
  const yOf = (v: number) => yFloor - (v / maxValue) * plotH;
  const xOfCell = (i: number) => MARGIN.left + (i + 0.5) * barW;
  const xOfKm = (km: number) => MARGIN.left + (km / largoKm) * plotW;

  const yTicks = useMemo(() => {
    if (maxValue <= 0) return [0];
    return [0, maxValue / 2, maxValue];
  }, [maxValue]);

  const fmt = (v: number) => (v >= 10 ? v.toFixed(0) : v.toFixed(1));

  const showStations =
    !!estacionesKm &&
    estacionesKm.length > 0 &&
    (isAll || isEspera || heatMode === "metro");

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className={cn(
          "block transition-colors",
          flash && "animate-iteration-flash",
        )}
        style={{
          display: "block",
          maxWidth: "100%",
          background: "var(--paper-2)",
          border: `1px solid ${flash ? "var(--accent)" : "var(--rule)"}`,
        }}
        role="img"
        aria-label={t("sandbox.city_strip_aria")}
      >
        {/* Grid horizontales + etiquetas Y */}
        {yTicks.map((v, i) => {
          const y = yOf(v);
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
          {isEspera
            ? t("sandbox.city_strip_y_wait")
            : t("sandbox.city_strip_y_time")}
        </text>

        {/* Marcadores de estación (posición km) */}
        {showStations &&
          estacionesKm!.map((km, i) => {
            const x = xOfKm(km);
            return (
              <line
                key={`st-${i}`}
                x1={x}
                y1={yTop}
                x2={x}
                y2={yFloor}
                stroke="var(--metro)"
                strokeWidth={0.7}
                strokeDasharray="1 3"
                opacity={0.5}
              />
            );
          })}

        {/* Barras (vistas de un modo o espera) */}
        {barValues &&
          barValues.map((raw, idx) => {
            const isCbd = idx === cbdIdx;
            if (isCbd) return null;
            const x = MARGIN.left + idx * barW;
            const barH = Math.max(0.5, (raw / maxValue) * plotH);
            const floor = yFloor + slopeOffset(((idx + 0.5) / nCeldas) * 100);
            const infeasible = cutoffMin != null && raw > cutoffMin;
            return (
              <rect
                key={idx}
                x={x}
                y={floor - barH}
                width={Math.max(barW - 0.15, 0.2)}
                height={barH}
                fill={singleColor}
                opacity={infeasible ? 0.28 : 0.85}
                style={{
                  transition:
                    "y 400ms ease-out, height 400ms ease-out, fill 400ms ease-out, opacity 400ms ease-out",
                }}
              />
            );
          })}

        {/* Placeholder cuando aún no hay datos */}
        {!modeProfile &&
          Array.from({ length: nCeldas }).map((_, idx) =>
            idx === cbdIdx ? null : (
              <rect
                key={`ph-${idx}`}
                x={MARGIN.left + idx * barW}
                y={yFloor - 0.5}
                width={Math.max(barW - 0.15, 0.2)}
                height={0.5}
                fill="var(--rule)"
              />
            ),
          )}

        {/* Líneas (vista "todos") — una por modo */}
        {lines &&
          lines.map((l) => (
            <polyline
              key={l.mode}
              points={l.values
                .map((v, i) => `${xOfCell(i)},${yOf(v)}`)
                .join(" ")}
              fill="none"
              stroke={l.color}
              strokeWidth={1.6}
              strokeLinejoin="round"
              opacity={0.95}
            />
          ))}

        {/* Baseline del plot (eje X visual) */}
        <line
          x1={MARGIN.left}
          y1={yFloor}
          x2={MARGIN.left + plotW}
          y2={yFloor}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* Línea de corte de factibilidad del modo (caminata 30, bici 45). */}
        {cutoffMin != null && cutoffMin > 0 && cutoffMin <= maxValue && (
          <g>
            <line
              x1={MARGIN.left}
              y1={yOf(cutoffMin)}
              x2={MARGIN.left + plotW}
              y2={yOf(cutoffMin)}
              stroke="var(--accent)"
              strokeWidth={1.2}
              strokeDasharray="5 3"
            />
            {cutoffLabel && (
              <text
                x={MARGIN.left + plotW}
                y={yOf(cutoffMin) - 4}
                textAnchor="end"
                className="label"
                fill="var(--accent)"
              >
                {cutoffLabel}
              </text>
            )}
          </g>
        )}

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

        {/* Etiquetas X: 0 / L en km */}
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
