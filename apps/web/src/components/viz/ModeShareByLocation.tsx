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
}

const MODE_ORDER: Modo[] = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"];
const MODE_COLORS: Record<Modo, string> = {
  Auto: "#FF8C00",
  Metro: "#FF0000",
  Bici: "#228B22",
  Caminata: "#0000FF",
  Teletrabajo: "#A9A9A9",
};

/**
 * Histograma apilado de reparto modal por ubicación (km desde origen izquierdo).
 */
export function ModeShareByLocation({
  agents,
  nCeldas,
  largoKm,
  nBins = 40,
  height = 140,
  className,
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
    const maxTotal = Math.max(
      1,
      ...bins.map((b) => MODE_ORDER.reduce((s, m) => s + b[m], 0))
    );
    return { bins, maxTotal };
  }, [agents, nBins, binWidth]);

  const barW = 100 / nBins;

  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="block w-full rounded border border-slate-200 dark:border-slate-800"
        style={{ height }}
      >
        {data.bins.map((bin, i) => {
          let yCursor = 100;
          const total = MODE_ORDER.reduce((s, m) => s + bin[m], 0);
          const totalH = (total / data.maxTotal) * 98;
          return (
            <g key={i}>
              {MODE_ORDER.map((m) => {
                if (bin[m] === 0) return null;
                const h = total > 0 ? (bin[m] / total) * totalH : 0;
                yCursor -= h;
                return (
                  <rect
                    key={m}
                    x={i * barW}
                    y={yCursor}
                    width={Math.max(barW - 0.05, 0.05)}
                    height={h}
                    fill={MODE_COLORS[m]}
                    opacity={0.85}
                  />
                );
              })}
            </g>
          );
        })}
        <line x1={50} y1={0} x2={50} y2={100} stroke="#ef4444" strokeWidth={0.4} strokeDasharray="1 1" opacity={0.6} />
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-slate-500 dark:text-slate-400">
        <span>0 km</span>
        <span>CBD</span>
        <span>{largoKm.toFixed(0)} km</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[10px]">
        {MODE_ORDER.map((m) => (
          <span key={m} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-sm"
              style={{ backgroundColor: MODE_COLORS[m] }}
            />
            {t(`modes.${m.toLowerCase()}`)}
          </span>
        ))}
      </div>
    </div>
  );
}
