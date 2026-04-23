import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { AgentRecord, Modo } from "@/lib/types";

interface ModeShareByLocationProps {
  agents: readonly AgentRecord[];
  nCeldas: number;
  largoKm: number;
  nBins?: number;
  height?: number;
  className?: string;
  /** Si `true`, normaliza cada bin a 100 % (reparto relativo). Si `false`, el
   *  alto total refleja densidad. Default: `true` — más legible en aula. */
  normalize?: boolean;
}

const MODE_ORDER: Modo[] = ["Teletrabajo", "Caminata", "Bici", "Metro", "Auto"];
const MODE_COLORS: Record<Modo, string> = {
  Auto: "var(--auto)",
  Metro: "var(--metro)",
  Bici: "var(--bici)",
  Caminata: "var(--walk)",
  Teletrabajo: "var(--tele)",
};

/**
 * Histograma apilado de reparto modal por ubicación (km desde periferia W).
 *
 * Mejoras de esta versión:
 * - Normalizado a 100 % por defecto: cada barra lee "qué porcentaje del bin
 *   eligió cada modo" — la comparación visual es honesta aunque la densidad
 *   caiga hacia la periferia.
 * - Paleta editorial (--auto / --metro / --bici / --walk / --tele).
 * - Ticks Y en 25/50/75 % con líneas guía.
 * - Spacing entre barras (gap) para que se vea como "barras" no como área.
 * - Orden apilado: Tele → Walk → Bici → Metro → Auto (Auto queda arriba,
 *   visualmente predominante con cualquier política pro-auto).
 * - Altura generosa (200px) + Y-axis labels.
 */
export function ModeShareByLocation({
  agents,
  nCeldas,
  largoKm,
  nBins = 48,
  height = 200,
  className,
  normalize = true,
}: ModeShareByLocationProps) {
  const { t } = useTranslation("simulator");
  const binWidth = nCeldas / nBins;

  const data = useMemo(() => {
    const bins: Record<Modo, number>[] = Array.from({ length: nBins }, () => ({
      Auto: 0,
      Metro: 0,
      Bici: 0,
      Caminata: 0,
      Teletrabajo: 0,
    }));
    for (const a of agents) {
      if (!a.modo_elegido) continue;
      const idx = Math.min(nBins - 1, Math.floor(a.celda_origen / binWidth));
      const bin = bins[idx];
      if (bin) bin[a.modo_elegido] += 1;
    }
    const totals = bins.map((b) => MODE_ORDER.reduce((s, m) => s + b[m], 0));
    const maxTotal = Math.max(1, ...totals);
    return { bins, totals, maxTotal };
  }, [agents, nBins, binWidth]);

  const barGap = 0.15;
  const barW = 100 / nBins;
  const innerBarW = Math.max(barW - barGap, 0.2);

  return (
    <div className={cn("relative", className)}>
      <div
        className="relative"
        style={{ height, border: "1px solid var(--rule)", background: "var(--paper-2)" }}
      >
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="absolute inset-0 block h-full w-full"
        >
          {/* Grid lines 25/50/75 */}
          {[25, 50, 75].map((y) => (
            <line
              key={y}
              x1={0}
              y1={y}
              x2={100}
              y2={y}
              stroke="var(--rule)"
              strokeWidth={0.25}
              strokeDasharray="1 2"
              opacity={0.6}
            />
          ))}

          {data.bins.map((bin, i) => {
            const total = data.totals[i] ?? 0;
            if (total === 0) return null;
            const totalH = normalize ? 100 : (total / data.maxTotal) * 100;
            let yCursor = 100;
            return (
              <g key={i}>
                {MODE_ORDER.map((m) => {
                  const count = bin[m];
                  if (count === 0) return null;
                  const share = count / total;
                  const h = share * totalH;
                  yCursor -= h;
                  return (
                    <rect
                      key={m}
                      x={i * barW + barGap / 2}
                      y={yCursor}
                      width={innerBarW}
                      height={h}
                      fill={MODE_COLORS[m]}
                      opacity={0.92}
                    >
                      <title>{`${t(`modes.${m.toLowerCase()}`)} — bin ${i}: ${count} (${(share * 100).toFixed(1)}%)`}</title>
                    </rect>
                  );
                })}
              </g>
            );
          })}

          {/* CBD vertical */}
          <line
            x1={50}
            y1={0}
            x2={50}
            y2={100}
            stroke="var(--accent)"
            strokeWidth={0.5}
            strokeDasharray="1 1"
            opacity={0.7}
          />
        </svg>

        {/* Y-axis labels */}
        {normalize && (
          <div className="pointer-events-none absolute inset-y-0 left-0 flex w-10 flex-col justify-between py-1 pl-1 font-fig text-[9px] tabular-nums text-muted">
            <span>100%</span>
            <span>50%</span>
            <span>0%</span>
          </div>
        )}
      </div>

      <div className="mt-1 flex justify-between font-fig text-[10px] uppercase tracking-[0.06em] text-muted">
        <span>0 km</span>
        <span>CBD</span>
        <span>{largoKm.toFixed(0)} km</span>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-fig text-[10px] uppercase tracking-[0.04em]">
        {MODE_ORDER.slice()
          .reverse()
          .map((m) => (
            <span key={m} className="flex items-center gap-1">
              <span
                className="inline-block h-2 w-3"
                style={{ backgroundColor: MODE_COLORS[m] }}
                aria-hidden
              />
              <span className="text-ink-2">{t(`modes.${m.toLowerCase()}`)}</span>
            </span>
          ))}
      </div>
    </div>
  );
}
