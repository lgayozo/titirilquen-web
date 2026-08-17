import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { Modo } from "@/lib/types";
import { COLOR_MODO } from "@/lib/modos";

interface ModeShareByLocationProps {
  /** Flujo por celda de origen de cada modo de viaje. Con asignación
   *  "expected" es el flujo **esperado** (nₐ·prob, continuo); con "montecarlo"
   *  es la realización muestreada — igual que las figuras de demanda 2/3/4. Usar
   *  esto (y no el conteo de `modo_elegido` por agente, que siempre se sortea)
   *  evita el "dentado" de muestreo agente‑nivel bajo asignación esperada. */
  demandByCell: {
    Auto: readonly number[];
    Metro: readonly number[];
    Bici: readonly number[];
    Caminata: readonly number[];
  };
  /** Teletrabajo por celda de origen (conteo determinista: no viaja, así que no
   *  aparece en `demandByCell`). */
  teleByCell: readonly number[];
  largoKm: number;
  nBins?: number;
  height?: number;
  className?: string;
  /** Si `true`, normaliza cada bin a 100 % (reparto relativo). Si `false`, el
   *  alto total refleja densidad. Default: `true` — más legible en aula. */
  normalize?: boolean;
}

const MODE_ORDER: Modo[] = ["Teletrabajo", "Caminata", "Bici", "Metro", "Auto"];
const MARGIN = { top: 8, right: 10, bottom: 16, left: 34 };
const LEGEND_H = 20;

/**
 * Histograma apilado de reparto modal por ubicación (km a lo largo de la
 * ciudad, CBD al centro). Todo (ejes, %, leyenda) va dentro del `<svg>` con
 * ancho medido en píxeles, para exportar completo a SVG/PNG sin distorsión.
 */
export function ModeShareByLocation({
  demandByCell,
  teleByCell,
  largoKm,
  nBins = 48,
  height = 200,
  className,
  normalize = true,
}: ModeShareByLocationProps) {
  const { t } = useTranslation("simulator");
  const nCeldas = teleByCell.length;
  const binWidth = nCeldas / nBins;

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(480);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(280, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => {
    const bins: Record<Modo, number>[] = Array.from({ length: nBins }, () => ({
      Auto: 0,
      Metro: 0,
      Bici: 0,
      Caminata: 0,
      Teletrabajo: 0,
    }));
    // Acumula el flujo esperado por celda (fraccional bajo "expected") en su bin
    // de ubicación. Teletrabajo va aparte (conteo por celda), no es un viaje.
    for (let i = 0; i < nCeldas; i++) {
      const idx = Math.min(nBins - 1, Math.floor(i / binWidth));
      const bin = bins[idx];
      if (!bin) continue;
      bin.Auto += demandByCell.Auto[i] ?? 0;
      bin.Metro += demandByCell.Metro[i] ?? 0;
      bin.Bici += demandByCell.Bici[i] ?? 0;
      bin.Caminata += demandByCell.Caminata[i] ?? 0;
      bin.Teletrabajo += teleByCell[i] ?? 0;
    }
    const totals = bins.map((b) => MODE_ORDER.reduce((s, m) => s + b[m], 0));
    const maxTotal = Math.max(1, ...totals);
    return { bins, totals, maxTotal };
  }, [demandByCell, teleByCell, nCeldas, nBins, binWidth]);

  const H = MARGIN.top + height + MARGIN.bottom + LEGEND_H;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = height;
  const yTop = MARGIN.top;
  const yFloor = MARGIN.top + plotH;
  const barW = plotW / nBins;
  const cbdX = MARGIN.left + plotW / 2;

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{
          display: "block",
          maxWidth: "100%",
          background: "var(--paper-2)",
          border: "1px solid var(--rule)",
        }}
        role="img"
      >
        {/* Grid + etiquetas Y (% si normalizado) */}
        {(normalize ? [0, 25, 50, 75, 100] : [0, 50, 100]).map((pct) => {
          const y = yFloor - (pct / 100) * plotH;
          return (
            <g key={pct}>
              <line
                x1={MARGIN.left}
                y1={y}
                x2={MARGIN.left + plotW}
                y2={y}
                stroke="var(--rule)"
                strokeWidth={0.5}
                strokeDasharray="1 2"
                opacity={0.6}
              />
              {normalize && (
                <text
                  x={MARGIN.left - 5}
                  y={y + 3}
                  textAnchor="end"
                  className="label"
                >
                  {pct}
                </text>
              )}
            </g>
          );
        })}

        {/* Barras apiladas */}
        {data.bins.map((bin, i) => {
          const total = data.totals[i] ?? 0;
          if (total === 0) return null;
          const totalH = (normalize ? 1 : total / data.maxTotal) * plotH;
          let yCursor = yFloor;
          return (
            <g key={i}>
              {MODE_ORDER.map((m) => {
                const count = bin[m];
                if (count === 0) return null;
                const h = (count / total) * totalH;
                yCursor -= h;
                return (
                  <rect
                    key={m}
                    x={MARGIN.left + i * barW + barW * 0.08}
                    y={yCursor}
                    width={Math.max(barW * 0.84, 0.4)}
                    height={h}
                    fill={COLOR_MODO[m]}
                    opacity={0.92}
                  >
                    <title>{`${t(`modes.${m.toLowerCase()}`)} — bin ${i}: ${Math.round(count)} (${((count / total) * 100).toFixed(1)}%)`}</title>
                  </rect>
                );
              })}
            </g>
          );
        })}

        {/* CBD vertical */}
        <line
          x1={cbdX}
          y1={yTop}
          x2={cbdX}
          y2={yFloor}
          stroke="var(--accent)"
          strokeWidth={0.8}
          strokeDasharray="2 2"
          opacity={0.7}
        />

        {/* Baseline */}
        <line
          x1={MARGIN.left}
          y1={yFloor}
          x2={MARGIN.left + plotW}
          y2={yFloor}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* Etiquetas X */}
        <text
          x={MARGIN.left}
          y={yFloor + 13}
          textAnchor="start"
          className="label"
        >
          0 KM
        </text>
        <text
          x={cbdX}
          y={yFloor + 13}
          textAnchor="middle"
          className="label"
          fill="var(--accent)"
        >
          CBD
        </text>
        <text
          x={MARGIN.left + plotW}
          y={yFloor + 13}
          textAnchor="end"
          className="label"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {largoKm.toFixed(0)} KM
        </text>

        {/* Leyenda */}
        {MODE_ORDER.slice()
          .reverse()
          .map((m, i) => {
            const x = MARGIN.left + i * Math.min(96, plotW / MODE_ORDER.length);
            const ly = yFloor + MARGIN.bottom + 12;
            return (
              <g key={`lg-${m}`} transform={`translate(${x}, ${ly})`}>
                <rect x={0} y={-7} width={10} height={8} fill={COLOR_MODO[m]} />
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
