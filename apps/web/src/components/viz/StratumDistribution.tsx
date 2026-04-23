import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface StratumDistributionProps {
  parcelas: readonly (readonly number[])[];
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
 * Histograma apilado de hogares por estrato a lo largo de las parcelas.
 * Eje Y en hogares/bin, eje X anotado como Periferia oeste · CBD · Periferia
 * este. Usa paleta editorial (CSS vars).
 */
export function StratumDistribution({
  parcelas,
  nBins,
  height = 180,
  className,
}: StratumDistributionProps) {
  const { t } = useTranslation("simulator");
  const L = parcelas.length;
  const bins = nBins ?? Math.min(L, 80);
  const binWidth = L / bins;

  const { counts, max } = useMemo(() => {
    const c: [number, number, number][] = Array.from({ length: bins }, () => [0, 0, 0]);
    parcelas.forEach((parcela, i) => {
      const idx = Math.min(bins - 1, Math.floor(i / binWidth));
      parcela.forEach((h) => {
        const bin = c[idx];
        if (!bin) return;
        if (h === 1) bin[0] += 1;
        else if (h === 2) bin[1] += 1;
        else if (h === 3) bin[2] += 1;
      });
    });
    const mx = Math.max(1, ...c.map((cc) => cc[0] + cc[1] + cc[2]));
    return { counts: c, max: mx };
  }, [parcelas, bins, binWidth]);

  // Medimos el contenedor para escalar el SVG en 1:1 píxel físico (evita la
  // distorsión de texto que producía `preserveAspectRatio="none"`).
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
  const barW = plotW / bins;

  const yTicks = [0, Math.round(max * 0.25), Math.round(max * 0.5), Math.round(max * 0.75), max];

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
          const y = MARGIN.top + plotH - (v / max) * plotH;
          return (
            <g key={v}>
              <line
                className="grid-line"
                x1={MARGIN.left}
                y1={y}
                x2={MARGIN.left + plotW}
                y2={y}
              />
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

        {/* Bars */}
        {counts.map((c, i) => {
          const total = c[0] + c[1] + c[2];
          if (total === 0) return null;
          const totalPx = (total / max) * plotH;
          let yCursor = MARGIN.top + plotH;
          return (
            <g key={i} transform={`translate(${MARGIN.left + i * barW}, 0)`}>
              {c.map((count, h) => {
                if (count === 0) return null;
                const part = (count / total) * totalPx;
                yCursor -= part;
                return (
                  <rect
                    key={h}
                    x={0.2}
                    y={yCursor}
                    width={Math.max(barW - 0.4, 0.4)}
                    height={part}
                    fill={STRATUM_VAR[h + 1]}
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
          y2={MARGIN.top + plotH}
          stroke="var(--accent)"
          strokeWidth={1}
          strokeDasharray="3 3"
          opacity={0.8}
        />
        <text
          className="label"
          x={MARGIN.left + plotW / 2}
          y={MARGIN.top - 1}
          textAnchor="middle"
          fill="var(--accent)"
        >
          CBD
        </text>

        {/* X axis baseline */}
        <line
          className="axis"
          x1={MARGIN.left}
          y1={MARGIN.top + plotH}
          x2={MARGIN.left + plotW}
          y2={MARGIN.top + plotH}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* X labels */}
        <text className="label" x={MARGIN.left} y={H - 8} textAnchor="start">
          {t("stratum_distribution.left_periphery").toUpperCase()}
        </text>
        <text className="label" x={MARGIN.left + plotW} y={H - 8} textAnchor="end">
          {t("stratum_distribution.right_periphery").toUpperCase()}
        </text>

        {/* Y-axis title */}
        <text
          className="label"
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
        >
          HOGARES / BIN
        </text>
      </svg>

      <div className="mt-2 flex flex-wrap gap-4" style={{ fontFamily: "var(--font-fig)", fontSize: 10 }}>
        {[1, 2, 3].map((h) => (
          <span key={h} className="flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
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
