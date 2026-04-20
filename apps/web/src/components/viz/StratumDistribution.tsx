import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface StratumDistributionProps {
  parcelas: readonly (readonly number[])[];
  nBins?: number;
  height?: number;
  className?: string;
}

const STRATUM_COLORS: Record<number, string> = {
  1: "#1f77b4",
  2: "#ff7f0e",
  3: "#2ca02c",
};

/**
 * Histograma apilado de hogares por estrato a lo largo de las parcelas.
 * Fundamental para ver el efecto Alonso-Muth-Mills: estratos con α alto
 * tienden al centro, estratos con α bajo se dispersan.
 */
export function StratumDistribution({
  parcelas,
  nBins,
  height = 160,
  className,
}: StratumDistributionProps) {
  const { t } = useTranslation("simulator");
  const L = parcelas.length;
  const bins = nBins ?? Math.min(L, 80);
  const binWidth = L / bins;

  const data = useMemo(() => {
    const counts: [number, number, number][] = Array.from({ length: bins }, () => [0, 0, 0]);
    parcelas.forEach((parcela, i) => {
      const idx = Math.min(bins - 1, Math.floor(i / binWidth));
      parcela.forEach((h) => {
        const bin = counts[idx];
        if (!bin) return;
        if (h === 1) bin[0] += 1;
        else if (h === 2) bin[1] += 1;
        else if (h === 3) bin[2] += 1;
      });
    });
    const max = Math.max(1, ...counts.map((c) => c[0] + c[1] + c[2]));
    return { counts, max };
  }, [parcelas, bins, binWidth]);

  const barW = 100 / bins;

  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="block w-full rounded border border-slate-200 dark:border-slate-800"
        style={{ height }}
      >
        {data.counts.map((c, i) => {
          const total = c[0] + c[1] + c[2];
          if (total === 0) return null;
          const totalH = (total / data.max) * 98;
          let yCursor = 100;
          return (
            <g key={i}>
              {c.map((count, h) => {
                if (count === 0) return null;
                const part = (count / total) * totalH;
                yCursor -= part;
                return (
                  <rect
                    key={h}
                    x={i * barW}
                    y={yCursor}
                    width={Math.max(barW - 0.05, 0.05)}
                    height={part}
                    fill={STRATUM_COLORS[h + 1]}
                    opacity={0.85}
                  />
                );
              })}
            </g>
          );
        })}
        <line
          x1={50}
          y1={0}
          x2={50}
          y2={100}
          stroke="#ef4444"
          strokeWidth={0.4}
          strokeDasharray="1 1"
          opacity={0.6}
        />
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-slate-500 dark:text-slate-400">
        <span>{t("stratum_distribution.left_periphery")}</span>
        <span>{t("stratum_distribution.cbd")}</span>
        <span>{t("stratum_distribution.right_periphery")}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[10px]">
        {[1, 2, 3].map((h) => (
          <span key={h} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-sm"
              style={{ backgroundColor: STRATUM_COLORS[h] }}
            />
            {t(`strata.${h === 1 ? "alto" : h === 2 ? "medio" : "bajo"}`)}
          </span>
        ))}
      </div>
    </div>
  );
}
