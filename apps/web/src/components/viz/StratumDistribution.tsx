import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface StratumDistributionProps {
  /** Asignación discreta (muestreada) de hogares por celda. parcelas[i] = lista
   *  de estratos. Fallback si no se entrega `composition`. */
  parcelas?: readonly (readonly number[])[];
  /** Ocupación **esperada** por celda S[i]·Q[h,i] (floats), preferida sobre
   *  `parcelas`. El muestreo discreto produce una "peineta" entre celdas
   *  contiguas (varianza alta donde hay pocos hogares); la esperada deriva
   *  directo de la composición de equilibrio Q y es pseudocontinua.
   *  composition[i] = [alto, medio, bajo]. La suma por celda sigue siendo S[i],
   *  así que la envolvente coincide con la oferta. */
  composition?: readonly (readonly number[])[];
  height?: number;
  className?: string;
}

const STRATUM_VAR: Record<number, string> = {
  1: "var(--s1)",
  2: "var(--s2)",
  3: "var(--s3)",
};

// Mismo encuadre que CityShapePreview: el resultado es la misma silueta de la
// ciudad (la oferta), ahora rellena con los colores de estrato.
const MARGIN = { top: 16, right: 14, bottom: 26, left: 44 };

/**
 * Distribución espacial de hogares por estrato — barras apiladas **por celda**.
 *
 * Comparte el lenguaje visual de `CityShapePreview` (mismo encuadre, escala y
 * ejes) para que se lea como la misma figura: el preview muestra la capacidad
 * de la ciudad "sin asignar" y este resultado, la misma envolvente coloreada
 * por estrato (la altura total de cada celda = su oferta S[i]). Por eso ambas
 * siluetas coinciden.
 */
export function StratumDistribution({
  parcelas,
  composition,
  height = 150,
  className,
}: StratumDistributionProps) {
  const { t } = useTranslation("simulator");

  const { counts, max, cbd } = useMemo(() => {
    // Preferir la ocupación esperada (suave); si no, contar el muestreo discreto.
    if (composition) {
      const cs: [number, number, number][] = [];
      let mx = 1;
      for (const row of composition) {
        const c: [number, number, number] = [
          row[0] ?? 0,
          row[1] ?? 0,
          row[2] ?? 0,
        ];
        cs.push(c);
        mx = Math.max(mx, c[0] + c[1] + c[2]);
      }
      return { counts: cs, max: mx, cbd: Math.floor(composition.length / 2) };
    }
    const src = parcelas ?? [];
    const L = src.length;
    const cs: [number, number, number][] = [];
    let mx = 1;
    for (let i = 0; i < L; i++) {
      const c: [number, number, number] = [0, 0, 0];
      for (const h of src[i] ?? []) {
        if (h === 1) c[0] += 1;
        else if (h === 2) c[1] += 1;
        else if (h === 3) c[2] += 1;
      }
      cs.push(c);
      mx = Math.max(mx, c[0] + c[1] + c[2]);
    }
    return { counts: cs, max: mx, cbd: Math.floor(L / 2) };
  }, [parcelas, composition]);

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

  const L = counts.length;
  const H = height;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;
  const yFloor = MARGIN.top + plotH;
  const barW = plotW / Math.max(L, 1);
  const cbdX = MARGIN.left + (cbd + 0.5) * barW;

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{
          display: "block",
          maxWidth: "100%",
          background: "var(--paper-2)",
          border: "1px solid var(--rule)",
        }}
        role="img"
        aria-label="Distribución espacial de hogares por estrato"
      >
        {/* Eje Y (rótulo) */}
        <text
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
          className="label"
        >
          HOGARES
        </text>

        {/* Barras apiladas por celda (estrato 1 abajo → 3 arriba) */}
        {counts.map((c, i) => {
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
                    x={x}
                    y={yCursor}
                    width={Math.max(barW - 0.2, 0.3)}
                    height={h}
                    fill={STRATUM_VAR[k + 1]}
                    opacity={0.85}
                  />
                );
              })}
            </g>
          );
        })}

        {/* Baseline */}
        <line
          x1={MARGIN.left}
          y1={yFloor}
          x2={MARGIN.left + plotW}
          y2={yFloor}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* CBD marker */}
        <line
          x1={cbdX}
          y1={MARGIN.top}
          x2={cbdX}
          y2={yFloor}
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

        {/* Etiquetas X */}
        <text x={MARGIN.left} y={H - 8} textAnchor="start" className="label">
          PERIFERIA
        </text>
        <text
          x={MARGIN.left + plotW}
          y={H - 8}
          textAnchor="end"
          className="label"
        >
          PERIFERIA
        </text>
      </svg>

      <div
        className="mt-2 flex flex-wrap gap-4"
        style={{ fontFamily: "var(--font-fig)", fontSize: 10 }}
      >
        {[1, 2, 3].map((h) => (
          <span
            key={h}
            className="flex items-center gap-1.5"
            style={{ color: "var(--muted)" }}
          >
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
