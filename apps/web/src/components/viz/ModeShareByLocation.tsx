import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { Modo } from "@/lib/types";
import { COLOR_MODO } from "@/lib/modos";
import { EJE_ESPACIAL } from "@/lib/ejeEspacial";

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
  /** Celdas por barra. `1` —el default— dibuja una barra por celda, que es la
   *  misma resolución que usan las demás figuras del eje espacial. Agrupar de a
   *  varias suaviza el apilado, pero deja esta figura con una unidad distinta de
   *  las otras sin que nada lo diga en pantalla. */
  celdasPorBarra?: number;
  height?: number;
  className?: string;
  /** Si `true`, normaliza cada bin a 100 % (reparto relativo). Si `false`, el
   *  alto total refleja densidad. Default: `true` — más legible en aula. */
  normalize?: boolean;
}

const MODE_ORDER: Modo[] = ["Teletrabajo", "Caminata", "Bici", "Metro", "Auto"];
// El eje horizontal lo fija `EJE_ESPACIAL` (ver lib/ejeEspacial.ts). Antes esta
// figura traía `left: 34`, así que el CBD caía 20 px a la izquierda del de las
// otras figuras del mismo eje y no se podían leer en columna.
const MARGIN = {
  top: 8,
  bottom: 16,
  left: EJE_ESPACIAL.left,
  right: EJE_ESPACIAL.right,
};
const LEGEND_H = 20;

/** Celda bajo el cursor. Reemplaza a los `<title>` nativos: eran 778 por figura
 *  —uno por cada segmento— y el navegador los muestra recién tras ~1 s, sin
 *  estilo. Acá además se resuelve el reparto COMPLETO de la celda de una vez, no
 *  el modo suelto que quedó debajo del puntero, que es la pregunta que la figura
 *  invita a hacer. */
interface HoverCelda {
  i: number;
  km: number;
  total: number;
  porModo: { modo: Modo; valor: number; share: number }[];
}

/**
 * Histograma apilado de reparto modal por ubicación (km a lo largo de la
 * ciudad, CBD al centro). Todo (ejes, %, leyenda) va dentro del `<svg>` con
 * ancho medido en píxeles, para exportar completo a SVG/PNG sin distorsión.
 */
export function ModeShareByLocation({
  demandByCell,
  teleByCell,
  largoKm,
  celdasPorBarra = 1,
  height = 200,
  className,
  normalize = true,
}: ModeShareByLocationProps) {
  const { t } = useTranslation("simulator");
  const [hover, setHover] = useState<HoverCelda | null>(null);
  const nCeldas = teleByCell.length;
  // Con `celdasPorBarra = 1` hay tantas barras como celdas y el índice de barra
  // ES el de la celda: la figura queda en la misma unidad que FIG. 00/01/02.
  const binWidth = Math.max(1, celdasPorBarra);
  const nBins = Math.max(1, Math.ceil(nCeldas / binWidth));

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

        {/* Barras apiladas. El gap entre barras solo se dibuja si hay lugar: con
            una barra por celda (201 sobre ~930 px) cada una mide ~4,6 px y un
            8 % de gap produce un rayado de moiré que compite con los datos. */}
        {data.bins.map((bin, i) => {
          const total = data.totals[i] ?? 0;
          if (total === 0) return null;
          const totalH = (normalize ? 1 : total / data.maxTotal) * plotH;
          const gap = barW > 6 ? barW * 0.08 : 0;
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
                    x={MARGIN.left + i * barW + gap}
                    y={yCursor}
                    width={Math.max(barW - 2 * gap, 0.4)}
                    height={h}
                    fill={COLOR_MODO[m]}
                    opacity={hover?.i === i ? 1 : 0.92}
                  />
                );
              })}
            </g>
          );
        })}

        {/* Captura del mouse: una columna de alto completo por celda. Apuntar a
            un segmento suelto es imposible cuando la barra mide 4,6 px de ancho
            y el modo minoritario ocupa un 3 % del alto. */}
        {data.bins.map((bin, i) => {
          const total = data.totals[i] ?? 0;
          if (total === 0) return null;
          const km =
            nCeldas > 1
              ? ((i * binWidth + (binWidth - 1) / 2) / (nCeldas - 1)) * largoKm
              : 0;
          return (
            <rect
              key={`hit-${i}`}
              x={MARGIN.left + i * barW}
              y={yTop}
              width={Math.max(barW, 1)}
              height={plotH}
              fill="transparent"
              onMouseEnter={() =>
                setHover({
                  i,
                  km,
                  total,
                  porModo: MODE_ORDER.slice()
                    .reverse()
                    .map((m) => ({
                      modo: m,
                      valor: bin[m],
                      share: bin[m] / total,
                    }))
                    .filter((o) => o.valor > 0),
                })
              }
              onMouseLeave={() => setHover(null)}
            />
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
      {hover && (
        <div className="network-tooltip" role="tooltip">
          <div className="nt-head">{`${hover.km.toFixed(1)} km`}</div>
          {hover.porModo.map((o) => (
            <div key={o.modo} className="nt-row">
              <span style={{ color: COLOR_MODO[o.modo] }}>
                {t(`modes.${o.modo.toLowerCase()}`)}
              </span>
              <span>{`${(o.share * 100).toFixed(1)}%`}</span>
            </div>
          ))}
          <div className="nt-row">
            <span>{t("sandbox.total")}</span>
            <span>{Math.round(hover.total).toLocaleString("es-CL")}</span>
          </div>
        </div>
      )}
    </div>
  );
}
