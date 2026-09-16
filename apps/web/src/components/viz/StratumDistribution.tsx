import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface StratumDistributionProps {
  /** Asignación discreta (muestreada) de hogares por celda. parcelas[i] = lista
   *  de estratos. Fallback si no se entrega `composition`. */
  parcelas?: readonly (readonly number[])[];
  /** Ocupación **esperada** por celda S[i]·Q[h,i] (floats), preferida sobre
   *  `parcelas`. El muestreo discreto produce una "peineta" entre celdas
   *  contiguas (varianza alta donde hay pocos hogares); la esperada deriva
   *  directo de la composición de equilibrio Q y es pseudocontinua.
   *  composition[i] = [alto, medio, bajo]. La suma por celda sigue siendo S[i],
   *  así que la envolvente coincide con la oferta. */
  composition?: readonly (readonly number[])[];
  height?: number;
  className?: string;
  /** Largo de la ciudad (km). Su presencia activa el modo "figura con métrica":
   *  ejes rotulados (Y en hogares, X en km) y tooltip por celda. Sin él el
   *  componente se comporta igual que antes, así que las llamadas de Uso de
   *  Suelo, Comparar y Ciudad en Equilibrio no cambian. */
  largoKm?: number;
  /** Geometría horizontal para alinear el área de dibujo con otra figura
   *  apilada (ver `CITY_PREVIEW_X_LAYOUT`). Van los tres datos: con distinto
   *  margen derecho el ancho útil difiere y el eje x deriva, y con distinto
   *  `minWidth` se desalinean en contenedores angostos. */
  xLayout?: { marginLeft: number; marginRight: number; minWidth: number };
}

const STRATUM_VAR: Record<number, string> = {
  1: "var(--s1)",
  2: "var(--s2)",
  3: "var(--s3)",
};

// Mismo encuadre que CityShapePreview: el resultado es la misma silueta de la
// ciudad (la oferta), ahora rellena con los colores de estrato.
const MARGIN_BASE = { top: 16, right: 14, bottom: 26, left: 44 };

/** Alto extra bajo el plot cuando hay eje X en km: ticks + rótulo del eje. */
const BOTTOM_CON_EJES = 44;

/**
 * Distribución espacial de hogares por estrato — barras apiladas **por celda**.
 *
 * Comparte el lenguaje visual de `CityShapePreview` (mismo encuadre, escala y
 * ejes) para que se lea como la misma figura: el preview muestra la capacidad
 * de la ciudad "sin asignar" y este resultado, la misma envolvente coloreada
 * por estrato (la altura total de cada celda = su oferta S[i]). Por eso ambas
 * siluetas coinciden.
 */
export function StratumDistribution({
  parcelas,
  composition,
  height = 150,
  className,
  largoKm,
  xLayout,
}: StratumDistributionProps) {
  const { t } = useTranslation("simulator");

  // Un solo interruptor en vez de varios flags: `largoKm` es lo que convierte
  // la figura de "índices de celda" en "una ciudad con métrica", que es
  // justamente cuando ejes en km y tooltip tienen sentido.
  const conEjes = largoKm != null;

  const { counts, max, cbd } = useMemo(() => {
    // Preferir la ocupación esperada (suave); si no, contar el muestreo discreto.
    if (composition) {
      const cs: [number, number, number][] = [];
      let mx = 1;
      for (const row of composition) {
        const c: [number, number, number] = [
          row[0] ?? 0,
          row[1] ?? 0,
          row[2] ?? 0,
        ];
        cs.push(c);
        mx = Math.max(mx, c[0] + c[1] + c[2]);
      }
      return { counts: cs, max: mx, cbd: Math.floor(composition.length / 2) };
    }
    const src = parcelas ?? [];
    const L = src.length;
    const cs: [number, number, number][] = [];
    let mx = 1;
    for (let i = 0; i < L; i++) {
      const c: [number, number, number] = [0, 0, 0];
      for (const h of src[i] ?? []) {
        if (h === 1) c[0] += 1;
        else if (h === 2) c[1] += 1;
        else if (h === 3) c[2] += 1;
      }
      cs.push(c);
      mx = Math.max(mx, c[0] + c[1] + c[2]);
    }
    return { counts: cs, max: mx, cbd: Math.floor(L / 2) };
  }, [parcelas, composition]);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [W, setW] = useState(800);
  const minW = xLayout?.minWidth ?? 360;
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(minW, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, [minW]);

  const MARGIN = useMemo(
    () => ({
      ...MARGIN_BASE,
      left: xLayout?.marginLeft ?? MARGIN_BASE.left,
      right: xLayout?.marginRight ?? MARGIN_BASE.right,
      bottom: conEjes ? BOTTOM_CON_EJES : MARGIN_BASE.bottom,
    }),
    [xLayout, conEjes],
  );

  const L = counts.length;
  const H = height;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;
  const yFloor = MARGIN.top + plotH;
  const barW = plotW / Math.max(L, 1);
  const cbdX = MARGIN.left + (cbd + 0.5) * barW;

  // Ticks del eje Y en hogares por celda. Sin escala numérica el rótulo
  // "HOGARES" no permitía leer magnitudes, solo la forma.
  const yTicks = useMemo(() => {
    if (!conEjes) return [] as { v: number; y: number }[];
    const n = 4;
    return Array.from({ length: n + 1 }, (_, i) => {
      const v = (i / n) * max;
      return { v, y: yFloor - (v / max) * plotH };
    });
  }, [conEjes, max, yFloor, plotH]);

  // Mismos 5 cortes que el eje X de CityPreview, para que apilados coincidan.
  const xTicks = useMemo(() => {
    if (largoKm == null) return [] as { km: number; x: number }[];
    const n = 5;
    return Array.from({ length: n }, (_, i) => ({
      km: (i / (n - 1)) * largoKm,
      x: MARGIN.left + (i / (n - 1)) * plotW,
    }));
  }, [largoKm, MARGIN.left, plotW]);

  // Una sola capa de captura en vez de un handler por barra: con 201 celdas
  // serían 201 listeners para leer un dato que se deduce de la coordenada x.
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const svg = svgRef.current;
    if (!svg || L === 0) return;
    const r = svg.getBoundingClientRect();
    // El SVG se escala con maxWidth:100%, así que hay que llevar el px del
    // puntero a coordenadas del viewBox antes de mapearlo a una celda.
    const xView = ((e.clientX - r.left) * W) / Math.max(r.width, 1);
    const i = Math.floor((xView - MARGIN.left) / barW);
    setHoverIdx(i >= 0 && i < L ? i : null);
  };

  const hovered = hoverIdx != null ? counts[hoverIdx] : undefined;
  const hoverTotal = hovered ? hovered[0] + hovered[1] + hovered[2] : 0;
  const cellKm = largoKm != null && L > 0 ? largoKm / L : 0;
  const hoverX = hoverIdx != null ? MARGIN.left + (hoverIdx + 0.5) * barW : 0;

  const fmt = (v: number) =>
    Math.round(v).toLocaleString(undefined, { maximumFractionDigits: 0 });

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
        }}
        role="img"
        aria-label={t("stratum_distribution.aria")}
      >
        {/* Marco dibujado DENTRO del viewBox, no con `border` de CSS: con
            box-sizing:border-box el borde le come 2px al área de contenido
            mientras el viewBox sigue midiendo W, y esa escala de 0.9977
            desalineaba el eje x respecto del plano apilado debajo. */}
        <rect
          x={0.5}
          y={0.5}
          width={Math.max(W - 1, 0)}
          height={Math.max(H - 1, 0)}
          fill="none"
          stroke="var(--rule)"
          strokeWidth={1}
        />
        {/* Eje Y (rótulo) */}
        <text
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
          className="label"
        >
          {conEjes
            ? t("stratum_distribution.y_axis")
            : t("stratum_distribution.y_axis_short")}
        </text>

        {/* Eje Y: línea, ticks y valores */}
        {conEjes && (
          <>
            <line
              x1={MARGIN.left}
              y1={MARGIN.top}
              x2={MARGIN.left}
              y2={yFloor}
              stroke="var(--ink)"
              strokeWidth={0.8}
            />
            {yTicks.map((tick, i) => (
              <g key={`y-${i}`}>
                <line
                  x1={MARGIN.left - 4}
                  y1={tick.y}
                  x2={MARGIN.left}
                  y2={tick.y}
                  stroke="var(--ink)"
                  strokeWidth={0.8}
                />
                <text
                  x={MARGIN.left - 7}
                  y={tick.y + 3}
                  textAnchor="end"
                  className="label"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {fmt(tick.v)}
                </text>
              </g>
            ))}
          </>
        )}

        {/* Barras apiladas por celda (estrato 1 abajo → 3 arriba) */}
        {counts.map((c, i) => {
          const total = c[0] + c[1] + c[2];
          if (total <= 0) return null;
          const x = MARGIN.left + i * barW;
          let yCursor = yFloor;
          return (
            <g key={i}>
              {[0, 1, 2].map((k) => {
                const v = c[k]!;
                if (v <= 0) return null;
                const h = (v / max) * plotH;
                yCursor -= h;
                return (
                  <rect
                    key={k}
                    x={x}
                    y={yCursor}
                    width={Math.max(barW - 0.2, 0.3)}
                    height={h}
                    fill={STRATUM_VAR[k + 1]}
                    opacity={hoverIdx == null || hoverIdx === i ? 0.85 : 0.55}
                  />
                );
              })}
            </g>
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

        {conEjes ? (
          /* Eje X en km, con los mismos cortes que el plano de infraestructura */
          <>
            {xTicks.map((tick, i) => (
              <g key={`x-${i}`}>
                <line
                  x1={tick.x}
                  y1={yFloor}
                  x2={tick.x}
                  y2={yFloor + 4}
                  stroke="var(--ink)"
                  strokeWidth={0.8}
                />
                <text
                  x={tick.x}
                  y={yFloor + 16}
                  textAnchor="middle"
                  className="label"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {tick.km.toFixed(0)}
                </text>
              </g>
            ))}
            <text
              x={MARGIN.left + plotW / 2}
              y={H - 6}
              textAnchor="middle"
              className="label"
            >
              {t("network.x_axis")}
            </text>
          </>
        ) : (
          /* Etiquetas X */
          <>
            <text
              x={MARGIN.left}
              y={H - 8}
              textAnchor="start"
              className="label"
            >
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
          </>
        )}

        {/* Capa de captura del puntero — encima de todo para que el hover no se
            pierda en los huecos entre barras. */}
        {conEjes && (
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

      {/* Tooltip como HTML (no SVG): el texto multilínea y el ajuste de ancho
          los resuelve el layout del navegador. */}
      {conEjes && hoverIdx != null && hovered && (
        <div
          className="pointer-events-none absolute z-10"
          style={{
            left: Math.min(Math.max(hoverX, 92), Math.max(W - 92, 92)),
            top: MARGIN.top + 4,
            transform: "translateX(-50%)",
            background: "var(--paper)",
            border: "1px solid var(--rule)",
            padding: "6px 8px",
            fontFamily: "var(--font-fig)",
            fontSize: 10,
            lineHeight: 1.5,
            whiteSpace: "nowrap",
            color: "var(--ink)",
          }}
        >
          <div style={{ color: "var(--muted)" }}>
            {t("stratum_distribution.tooltip_pos", {
              km: ((hoverIdx + 0.5) * cellKm).toFixed(1),
              dist: (Math.abs(cbd - hoverIdx) * cellKm).toFixed(1),
            })}
          </div>
          <div style={{ fontWeight: 600 }}>
            {t("stratum_distribution.tooltip_total", {
              n: fmt(hoverTotal),
            })}
          </div>
          {[1, 2, 3].map((h) => {
            const v = hovered[h - 1]!;
            const pct = hoverTotal > 0 ? (v / hoverTotal) * 100 : 0;
            return (
              <div key={h} className="flex items-center gap-1.5">
                <span
                  className="inline-block"
                  style={{
                    width: 8,
                    height: 8,
                    backgroundColor: STRATUM_VAR[h],
                  }}
                />
                <span style={{ color: "var(--ink-2)" }}>
                  {t(`strata.${h === 1 ? "alto" : h === 2 ? "medio" : "bajo"}`)}
                </span>
                <span
                  style={{
                    marginLeft: "auto",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {fmt(v)} · {pct.toFixed(0)}%
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div
        className="mt-2 flex flex-wrap gap-4"
        style={{ fontFamily: "var(--font-fig)", fontSize: 10 }}
      >
        {[1, 2, 3].map((h) => (
          <span
            key={h}
            className="flex items-center gap-1.5"
            style={{ color: "var(--muted)" }}
          >
            <span
              className="inline-block"
              style={{ width: 10, height: 10, backgroundColor: STRATUM_VAR[h] }}
            />
            <span style={{ color: "var(--ink-2)" }}>
              {t(`strata.${h === 1 ? "alto" : h === 2 ? "medio" : "bajo"}`)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
