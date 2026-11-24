import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import { COLOR_MODO, fmtPct } from "@/lib/modos";
import type { RepartoModal } from "@/lib/types-v2";

/** Una fila a graficar: un estrato o el agregado del sistema. */
export interface ModalShareRow {
  label: string;
  reparto: RepartoModal;
}

interface ModalShareBarsProps {
  rows: readonly ModalShareRow[];
  className?: string;
}

const MODE_ORDER: (keyof RepartoModal)[] = [
  "Auto",
  "Metro",
  "Bici",
  "Caminata",
  "Teletrabajo",
  "Varado",
];
const MODE_COLOR: Record<keyof RepartoModal, string> = COLOR_MODO;

// 108: «Estrato medio» en Plex Mono de 12 px (B2) mide ~94.
const LABEL_W = 108;
const ROW_H = 28;
const ROW_GAP = 10;
const TOP_PAD = 6;
const LEGEND_H = 24;

/**
 * Reparto modal por estrato/sistema como barras horizontales 100 % apiladas,
 * a partir de los **shares** ya calculados en el core (`reparto_modal`). A
 * diferencia de `ModeShareBars` (que cuenta agentes y omite varados), grafica
 * directamente las proporciones del reporte de métricas e incluye Teletrabajo y
 * Varado. Barras altas con % embebido para que se distingan bien (corrige las
 * franjas finas e ilegibles de la tabla anterior). Todo en `<svg>` para export.
 */
export function ModalShareBars({ rows, className }: ModalShareBarsProps) {
  const { t } = useTranslation("simulator");

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(420);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(280, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const barX = LABEL_W;
  const barW = Math.max(60, W - LABEL_W - 8);
  const H = TOP_PAD + rows.length * (ROW_H + ROW_GAP) + LEGEND_H;
  const legendY = TOP_PAD + rows.length * (ROW_H + ROW_GAP) + 12;

  const data = useMemo(
    () =>
      rows.map((r) => {
        const total =
          MODE_ORDER.reduce((s, m) => s + (r.reparto[m] ?? 0), 0) || 1;
        return {
          label: r.label,
          shares: MODE_ORDER.map((m) => (r.reparto[m] ?? 0) / total),
        };
      }),
    [rows],
  );

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", maxWidth: "100%" }}
        role="img"
      >
        {data.map((r, i) => {
          const y = TOP_PAD + i * (ROW_H + ROW_GAP);
          let cursor = barX;
          return (
            <g key={i}>
              <text
                x={LABEL_W - 10}
                y={y + ROW_H / 2 + 3}
                textAnchor="end"
                className="series-label"
                style={{ fontSize: 12 }}
              >
                {r.label}
              </text>
              <rect
                x={barX}
                y={y}
                width={barW}
                height={ROW_H}
                fill="var(--paper-2)"
                stroke="var(--rule)"
                strokeWidth={1}
              />
              {MODE_ORDER.map((m, k) => {
                const share = r.shares[k] ?? 0;
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
                      fill={MODE_COLOR[m]}
                      opacity={0.92}
                    >
                      <title>{`${t(`eqt.mode_${m.toLowerCase()}`)}: ${fmtPct(share * 100)}`}</title>
                    </rect>
                    {w > 30 && (
                      <text
                        x={x + w / 2}
                        y={y + ROW_H / 2 + 4}
                        textAnchor="middle"
                        style={{
                          fontFamily: "var(--font-fig)",
                          fontSize: 12,
                          fill: "var(--on-dato)",
                        }}
                      >
                        {fmtPct(share * 100, 0)}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* Leyenda */}
        {MODE_ORDER.map((m, i) => {
          const x = 2 + i * Math.min(96, (W - 6) / MODE_ORDER.length);
          return (
            <g key={`lg-${m}`} transform={`translate(${x}, ${legendY})`}>
              <rect x={0} y={-7} width={10} height={8} fill={MODE_COLOR[m]} />
              <text x={14} y={0} className="label">
                {t(`eqt.mode_${m.toLowerCase()}`)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
