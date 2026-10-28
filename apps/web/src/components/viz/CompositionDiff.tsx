import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { COLOR_ESTRATO, fmtDecimal } from "@/lib/modos";

interface CompositionDiffProps {
  /** Hogares esperados por celda y estrato, `[celda][estrato]`, sin feedback. */
  antes: readonly (readonly number[])[];
  /** Lo mismo en el equilibrio con feedback. */
  despues: readonly (readonly number[])[];
  height?: number;
}

// El encuadre de `StratumDistribution` en esta página, con 8 px más a la
// izquierda: los rótulos del eje llevan signo.
const MARGIN = { top: 16, right: 14, bottom: 26, left: 52 };

// Trazo por estrato, además del color: los tres tonos tierra de
// `COLOR_ESTRATO` se distinguen como áreas pero no como líneas finas.
const TRAZO: Record<1 | 2 | 3, string | undefined> = {
  1: undefined,
  2: "6 3",
  3: "1.5 2.5",
};

/** El menor 1, 2 o 5 × 10ⁿ que no es menor que `x`: marcas redondas. */
function topeRedondo(x: number): number {
  if (!(x > 0)) return 1;
  const p = 10 ** Math.floor(Math.log10(x));
  return ([1, 2, 5, 10].find((k) => k * p >= x) ?? 10) * p;
}

/**
 * Cuántos hogares de cada estrato gana o pierde cada celda por el feedback:
 * equilibrio final menos primera vuelta. Las dos distribuciones apiladas, una
 * al lado de la otra, se ven casi iguales aunque los estratos se muevan; la
 * diferencia es el efecto que la página quiere mostrar. La oferta S de cada
 * celda es la misma en las dos vueltas, así que en cada celda las tres curvas
 * suman cero.
 */
export function CompositionDiff({
  antes,
  despues,
  height = 170,
}: CompositionDiffProps) {
  const { t } = useTranslation("simulator");

  const { delta, tope } = useMemo(() => {
    const d = despues.map((fila, i) =>
      [0, 1, 2].map((h) => (fila[h] ?? 0) - (antes[i]?.[h] ?? 0)),
    );
    const mx = Math.max(0, ...d.flat().map(Math.abs));
    return { delta: d, tope: topeRedondo(mx) };
  }, [antes, despues]);

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(800);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(360, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const L = delta.length;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = height - MARGIN.top - MARGIN.bottom;
  const barW = plotW / Math.max(L, 1);
  // Centro de la celda, como las barras de `StratumDistribution`.
  const xOf = (i: number) => MARGIN.left + (i + 0.5) * barW;
  const yOf = (v: number) => MARGIN.top + plotH / 2 - (v / tope) * (plotH / 2);
  const cbdX = xOf(Math.floor(L / 2));
  const ticks = [-tope, -tope / 2, 0, tope / 2, tope];
  // Con tope 5 la marca media es 2,5: un decimal sólo cuando hace falta.
  const cifra = (v: number) => fmtDecimal(v, Number.isInteger(v) ? 0 : 1);
  const conSigno = (v: number) =>
    v > 0 ? `+${cifra(v)}` : v < 0 ? `−${cifra(-v)}` : "0";

  return (
    <div ref={wrapRef}>
      <svg
        width={W}
        height={height}
        viewBox={`0 0 ${W} ${height}`}
        style={{ display: "block", maxWidth: "100%" }}
        role="img"
        aria-label={t("coupled.diff_title")}
      >
        {ticks.map((v) => (
          <g key={v}>
            <line
              className="grid-line"
              x1={MARGIN.left}
              y1={yOf(v)}
              x2={MARGIN.left + plotW}
              y2={yOf(v)}
            />
            <text
              className="label"
              x={MARGIN.left - 6}
              y={yOf(v) + 3}
              textAnchor="end"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {conSigno(v)}
            </text>
          </g>
        ))}

        {/* El cero: ni gana ni pierde. */}
        <line
          x1={MARGIN.left}
          y1={yOf(0)}
          x2={MARGIN.left + plotW}
          y2={yOf(0)}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        <line
          x1={cbdX}
          y1={MARGIN.top}
          x2={cbdX}
          y2={MARGIN.top + plotH}
          stroke="var(--accent)"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
        <text
          x={cbdX}
          y={MARGIN.top - 2}
          textAnchor="middle"
          className="label"
          fill="var(--accent)"
        >
          CBD
        </text>

        {([1, 2, 3] as const).map((h) => (
          <path
            key={h}
            d={delta
              .map(
                (d, i) =>
                  `${i === 0 ? "M" : "L"}${xOf(i).toFixed(2)},${yOf(d[h - 1] ?? 0).toFixed(2)}`,
              )
              .join(" ")}
            fill="none"
            stroke={COLOR_ESTRATO[h]}
            strokeWidth={1.8}
            strokeDasharray={TRAZO[h]}
          />
        ))}

        <text
          x={MARGIN.left}
          y={height - 8}
          textAnchor="start"
          className="label"
        >
          {t("network.periphery")}
        </text>
        <text
          x={MARGIN.left + plotW}
          y={height - 8}
          textAnchor="end"
          className="label"
        >
          {t("network.periphery")}
        </text>
      </svg>

      <div
        className="mt-2 flex flex-wrap gap-4"
        style={{ fontSize: "var(--fs-etiqueta)" }}
      >
        {([1, 2, 3] as const).map((h) => (
          <span key={h} className="flex items-center gap-1.5">
            <svg width={22} height={6} aria-hidden="true">
              <line
                x1={0}
                y1={3}
                x2={22}
                y2={3}
                stroke={COLOR_ESTRATO[h]}
                strokeWidth={1.8}
                strokeDasharray={TRAZO[h]}
              />
            </svg>
            <span style={{ color: "var(--ink-2)" }}>
              {t(`strata.${h === 1 ? "alto" : h === 2 ? "medio" : "bajo"}`)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
