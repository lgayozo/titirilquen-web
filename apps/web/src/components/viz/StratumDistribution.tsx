import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface StratumDistributionProps {
  parcelas: readonly (readonly number[])[];
  /** Nº objetivo de barras (bins de igual tamaño entero). Cada barra promedia
   *  unas pocas parcelas para revelar el descenso desde el centro sin el ruido
   *  parcela‑a‑parcela de la asignación estocástica. */
  nBins?: number;
  height?: number;
  className?: string;
}

const STRATUM_VAR: Record<number, string> = {
  1: "var(--s1)",
  2: "var(--s2)",
  3: "var(--s3)",
};

const MARGIN = { top: 8, right: 8, bottom: 26, left: 42 };

/**
 * Distribución espacial de hogares por estrato como barras apiladas.
 *
 * Se agrega en bins de igual cantidad de parcelas (entero) para evitar dos
 * fuentes de "ruido" entre barras consecutivas:
 *  1. el aliasing de un `binWidth` fraccionario (cada bin recibiría 2 ó 3
 *     parcelas → alturas alternadas), y
 *  2. la varianza parcela‑a‑parcela de la asignación estocástica.
 * Con bins de igual tamaño y algo anchos, las barras descienden suave desde el
 * CBD hacia las periferias (densidad bid‑rent).
 */
export function StratumDistribution({
  parcelas,
  nBins = 50,
  height = 180,
  className,
}: StratumDistributionProps) {
  const { t } = useTranslation("simulator");

  const { areas, max } = useMemo(() => {
    const L = parcelas.length;
    const step = Math.max(1, Math.round(L / Math.max(1, nBins)));
    const nb = Math.max(1, Math.ceil(L / step));
    const bins: [number, number, number][] = [];
    for (let b = 0; b < nb; b++) {
      const start = b * step;
      const end = Math.min(L, (b + 1) * step);
      const c: [number, number, number] = [0, 0, 0];
      for (let i = start; i < end; i++) {
        for (const h of parcelas[i] ?? []) {
          if (h === 1) c[0] += 1;
          else if (h === 2) c[1] += 1;
          else if (h === 3) c[2] += 1;
        }
      }
      // Escala el último bin parcial para que represente `step` parcelas (evita
      // una caída espuria al final).
      const pc = end - start;
      if (pc > 0 && pc < step) {
        const f = step / pc;
        c[0] *= f;
        c[1] *= f;
        c[2] *= f;
      }
      bins.push(c);
    }
    const mx = Math.max(1, ...bins.map((c) => c[0] + c[1] + c[2]));
    return { areas: bins, max: mx };
  }, [parcelas, nBins]);

  const wrapRef = useRef<HTMLDivElement | null>(null);
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
  const yFloor = MARGIN.top + plotH;

  const n = areas.length;
  const yOf = (v: number) => yFloor - (v / max) * plotH;
  const barW = plotW / n;
  const gap = Math.min(barW * 0.12, 1.5);

  const yTicks = [0, Math.round(max * 0.25), Math.round(max * 0.5), Math.round(max * 0.75), Math.round(max)];

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{ display: "block", maxWidth: "100%" }}
      >
        {/* Grid lines + Y-axis labels */}
        {yTicks.map((v) => {
          const y = yOf(v);
          return (
            <g key={v}>
              <line className="grid-line" x1={MARGIN.left} y1={y} x2={MARGIN.left + plotW} y2={y} />
              <text
                className="label"
                x={MARGIN.left - 6}
                y={y + 3}
                textAnchor="end"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {v}
              </text>
            </g>
          );
        })}

        {/* Barras apiladas por bin (estrato 1 abajo → 3 arriba) */}
        {areas.map((c, i) => {
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
                    x={x + gap / 2}
                    y={yCursor}
                    width={Math.max(barW - gap, 0.4)}
                    height={h}
                    fill={STRATUM_VAR[k + 1]}
                    opacity={0.85}
                  />
                );
              })}
            </g>
          );
        })}

        {/* CBD vertical marker */}
        <line
          x1={MARGIN.left + plotW / 2}
          y1={MARGIN.top}
          x2={MARGIN.left + plotW / 2}
          y2={yFloor}
          stroke="var(--accent)"
          strokeWidth={1}
          strokeDasharray="3 3"
          opacity={0.8}
        />
        <text className="label" x={MARGIN.left + plotW / 2} y={MARGIN.top - 1} textAnchor="middle" fill="var(--accent)">
          CBD
        </text>

        {/* X axis baseline */}
        <line x1={MARGIN.left} y1={yFloor} x2={MARGIN.left + plotW} y2={yFloor} stroke="var(--ink)" strokeWidth={0.8} />

        {/* X labels */}
        <text className="label" x={MARGIN.left} y={H - 8} textAnchor="start">
          {t("stratum_distribution.left_periphery").toUpperCase()}
        </text>
        <text className="label" x={MARGIN.left + plotW} y={H - 8} textAnchor="end">
          {t("stratum_distribution.right_periphery").toUpperCase()}
        </text>

        {/* Y-axis title */}
        <text className="label" x={-MARGIN.top - plotH / 2} y={12} textAnchor="middle" transform="rotate(-90)">
          HOGARES
        </text>
      </svg>

      <div className="mt-2 flex flex-wrap gap-4" style={{ fontFamily: "var(--font-fig)", fontSize: 10 }}>
        {[1, 2, 3].map((h) => (
          <span key={h} className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
            <span className="inline-block" style={{ width: 10, height: 10, backgroundColor: STRATUM_VAR[h] }} />
            <span style={{ color: "var(--ink-2)" }}>
              {t(`strata.${h === 1 ? "alto" : h === 2 ? "medio" : "bajo"}`)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
