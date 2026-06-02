import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { AgentRecord, Modo } from "@/lib/types";

/** Un grupo de agentes a comparar (un estrato, o estrato×tenencia, etc.). */
export interface AgentGroup {
  label: string;
  /** Etiqueta secundaria opcional (p. ej. "con auto"). */
  tag?: string;
  agents: readonly AgentRecord[];
}

interface ModeShareBarsProps {
  groups: readonly AgentGroup[];
  className?: string;
}

const MODE_ORDER: Modo[] = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"];
const MODE_COLORS: Record<Modo, string> = {
  Auto: "var(--auto)",
  Metro: "var(--metro)",
  Bici: "var(--bici)",
  Caminata: "var(--walk)",
  Teletrabajo: "var(--tele)",
};

const LABEL_W = 84;
const COUNT_W = 46;
const ROW_H = 22;
const ROW_GAP = 8;
const TOP_PAD = 6;
const LEGEND_H = 22;

/**
 * Barras horizontales 100 % apiladas (reparto modal por grupo). Todo se dibuja
 * dentro de un `<svg>` con ancho medido en píxeles, para que exporte completo a
 * SVG/PNG. Pensado para comparar proporciones entre estratos o tenencia de auto.
 */
export function ModeShareBars({ groups, className }: ModeShareBarsProps) {
  const { t } = useTranslation("simulator");

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(420);
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
        const counts: Record<Modo, number> = {
          Auto: 0,
          Metro: 0,
          Bici: 0,
          Caminata: 0,
          Teletrabajo: 0,
        };
        for (const a of g.agents) {
          if (a.modo_elegido) counts[a.modo_elegido] += 1;
        }
        const total = MODE_ORDER.reduce((s, m) => s + counts[m], 0);
        return { ...g, counts, total };
      }),
    [groups]
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
                style={{ fontSize: 11 }}
              >
                {r.label}
              </text>
              {r.tag && (
                <text x={LABEL_W - 8} y={y + ROW_H / 2 + 10} textAnchor="end" className="label">
                  {r.tag}
                </text>
              )}

              {/* Fondo de la barra */}
              <rect x={barX} y={y} width={barW} height={ROW_H} fill="var(--paper-2)" stroke="var(--rule)" strokeWidth={1} />

              {/* Segmentos apilados */}
              {r.total > 0 &&
                MODE_ORDER.map((m) => {
                  const share = r.counts[m] / r.total;
                  if (share <= 0) return null;
                  const w = share * barW;
                  const x = cursor;
                  cursor += w;
                  return (
                    <g key={m}>
                      <rect x={x} y={y} width={w} height={ROW_H} fill={MODE_COLORS[m]} opacity={0.92}>
                        <title>{`${t(`modes.${m.toLowerCase()}`)}: ${r.counts[m].toLocaleString()} (${(share * 100).toFixed(1)}%)`}</title>
                      </rect>
                      {w > 26 && (
                        <text
                          x={x + w / 2}
                          y={y + ROW_H / 2 + 3}
                          textAnchor="middle"
                          style={{ fontFamily: "var(--font-fig)", fontSize: 9, fill: "var(--paper)" }}
                        >
                          {(share * 100).toFixed(0)}%
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
                {r.total.toLocaleString()}
              </text>
            </g>
          );
        })}

        {/* Leyenda */}
        {MODE_ORDER.map((m, i) => {
          const x = 2 + i * Math.min(104, (W - 6) / MODE_ORDER.length);
          return (
            <g key={`lg-${m}`} transform={`translate(${x}, ${legendY})`}>
              <rect x={0} y={-7} width={10} height={8} fill={MODE_COLORS[m]} />
              <text x={14} y={0} className="label">
                {t(`modes.${m.toLowerCase()}`)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
