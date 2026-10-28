import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { ModoTransporte } from "@/lib/types";
import { COLOR_MODO, MODOS, fmtEntero, fmtPct } from "@/lib/modos";

/** Un grupo a comparar (un estrato, o estrato×tenencia, etc.) con sus viajes
 *  por modo. Son los viajes ESPERADOS del núcleo (`viajes_por_modo_estrato`),
 *  no un conteo de los modos sorteados por agente (auditoría C, ítem 9). */
export interface ModeGroup {
  label: string;
  /** Etiqueta secundaria opcional (p. ej. "con auto"). */
  tag?: string;
  viajes: Partial<Record<ModoTransporte, number>>;
}

/** Los cuatro modos físicos: el reparto es sobre viajes (auditoría C, ítem
 *  10); el teletrabajo no viaja y, si lo hay, va en la etiqueta del grupo. */
const ORDEN = MODOS as readonly ModoTransporte[];

interface ModeShareBarsProps {
  groups: readonly ModeGroup[];
  className?: string;
}

const LABEL_W = 84;
// 56: «18.010» en Plex Mono de 12 px (B2) no cabía en 46.
const COUNT_W = 56;
const ROW_H = 22;
const ROW_GAP = 8;
const TOP_PAD = 6;
const LEGEND_H = 22;

/** Segmento bajo el cursor.
 *
 *  Antes esto era un `<title>` nativo: aparece recién tras ~1 s de reposo, sin
 *  estilo y fuera del tema, y en la práctica el usuario no lo encontraba. El
 *  tooltip propio es el mismo que ya usan la FIG. 00 y el perfil de flujo, así
 *  que no agrega un dialecto más. */
interface HoverSegmento {
  grupo: string;
  modo: ModoTransporte;
  conteo: number;
  share: number;
  total: number;
}

/**
 * Barras horizontales 100 % apiladas (reparto modal por grupo). Todo se dibuja
 * dentro de un `<svg>` con ancho medido en píxeles, para que exporte completo a
 * SVG/PNG. Pensado para comparar proporciones entre estratos o tenencia de auto.
 */
export function ModeShareBars({ groups, className }: ModeShareBarsProps) {
  const { t } = useTranslation("simulator");

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(420);
  const [hover, setHover] = useState<HoverSegmento | null>(null);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(260, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const rows = useMemo(
    () =>
      groups.map((g) => {
        const counts = Object.fromEntries(
          ORDEN.map((m) => [m, g.viajes[m] ?? 0]),
        ) as Record<ModoTransporte, number>;
        const total = ORDEN.reduce((s, m) => s + counts[m], 0);
        return { ...g, counts, total };
      }),
    [groups],
  );

  const barX = LABEL_W;
  const barW = Math.max(40, W - LABEL_W - COUNT_W);
  const H = TOP_PAD + rows.length * (ROW_H + ROW_GAP) + LEGEND_H;
  const legendY = TOP_PAD + rows.length * (ROW_H + ROW_GAP) + 12;

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{ display: "block", maxWidth: "100%" }}
        role="img"
      >
        {rows.map((r, i) => {
          const y = TOP_PAD + i * (ROW_H + ROW_GAP);
          let cursor = barX;
          return (
            <g key={i}>
              {/* Etiqueta del grupo (principal + tag) */}
              <text
                x={LABEL_W - 8}
                y={r.tag ? y + ROW_H / 2 - 1 : y + ROW_H / 2 + 3}
                textAnchor="end"
                className="series-label"
                style={{ fontSize: 12 }}
              >
                {r.label}
              </text>
              {r.tag && (
                <text
                  x={LABEL_W - 8}
                  y={y + ROW_H / 2 + 10}
                  textAnchor="end"
                  className="label"
                >
                  {r.tag}
                </text>
              )}

              {/* Fondo de la barra */}
              <rect
                x={barX}
                y={y}
                width={barW}
                height={ROW_H}
                fill="var(--paper-2)"
                stroke="var(--rule)"
                strokeWidth={1}
              />

              {/* Segmentos apilados */}
              {r.total > 0 &&
                ORDEN.map((m) => {
                  const share = r.counts[m] / r.total;
                  if (share <= 0) return null;
                  const w = share * barW;
                  const x = cursor;
                  cursor += w;
                  return (
                    <g key={m}>
                      <rect
                        x={x}
                        y={y}
                        width={w}
                        height={ROW_H}
                        fill={COLOR_MODO[m]}
                        opacity={
                          hover && hover.grupo === r.label && hover.modo === m
                            ? 1
                            : 0.92
                        }
                        onMouseEnter={() =>
                          setHover({
                            grupo: r.label,
                            modo: m,
                            conteo: r.counts[m],
                            share,
                            total: r.total,
                          })
                        }
                        onMouseLeave={() => setHover(null)}
                      />
                      {w > 26 && (
                        <text
                          x={x + w / 2}
                          y={y + ROW_H / 2 + 3}
                          textAnchor="middle"
                          style={{
                            fontFamily: "var(--font-fig)",
                            fontSize: 12,
                            fontWeight: 600,
                            fill: "var(--on-dato)",
                          }}
                        >
                          {fmtPct(share * 100, 0)}
                        </text>
                      )}
                    </g>
                  );
                })}

              {/* Conteo total */}
              <text
                x={barX + barW + 6}
                y={y + ROW_H / 2 + 3}
                textAnchor="start"
                className="label"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {fmtEntero(r.total)}
              </text>
            </g>
          );
        })}

        {/* Leyenda */}
        {ORDEN.map((m, i) => {
          const x = 2 + i * Math.min(104, (W - 6) / ORDEN.length);
          return (
            <g key={`lg-${m}`} transform={`translate(${x}, ${legendY})`}>
              <rect x={0} y={-7} width={10} height={8} fill={COLOR_MODO[m]} />
              <text x={14} y={0} className="label">
                {t(`modes.${m.toLowerCase()}`)}
              </text>
            </g>
          );
        })}
      </svg>
      {hover && (
        <div className="network-tooltip" role="tooltip">
          <div className="nt-head" style={{ color: COLOR_MODO[hover.modo] }}>
            {t(`modes.${hover.modo.toLowerCase()}`)} · {hover.grupo}
          </div>
          <div className="nt-row">
            <span>
              {t("sandbox.n_de_viajes", {
                n: fmtEntero(hover.conteo),
                total: fmtEntero(hover.total),
              })}
            </span>
          </div>
          <div className="nt-row">
            <span>{fmtPct(hover.share * 100)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
