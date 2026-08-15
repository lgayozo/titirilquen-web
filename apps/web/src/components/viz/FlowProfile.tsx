import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/cn";

interface FlowProfileProps {
  flows: readonly number[];
  largoKm: number;
  label?: string;
  color?: string;
  /** Tope máximo para el eje Y (comparte escala entre paneles). Si no se
   *  entrega, se usa el propio máximo del vector. */
  yMax?: number | null;
  /** Capacidad del corredor, en la MISMA unidad que `flows`. Se dibuja como
   *  línea sobre la escala y el encabezado pasa a mostrar v/c.
   *
   *  Antes esto era una pill de texto porque la serie graficada era la demanda
   *  ORIGINADA por celda, que no es comparable con una capacidad de corredor
   *  (difieren ~60×). Con `flows` = flujo acumulado del corredor sí lo es. */
  capacity?: number | null;
  /** Unidad de la capacidad para la etiqueta de la línea (ej. "veh/h"). */
  capacityLabel?: string;
  /** Formateo de valores (encabezado "max" y ticks Y). Default: redondeo entero. */
  valueFmt?: (v: number) => string;
  height?: number;
  className?: string;
}

const MARGIN = { top: 16, right: 10, bottom: 18, left: 40 };

/**
 * Perfil de demanda **por celda** de origen a lo largo de la ciudad.
 *
 * Se dibuja como barras discretas —una por celda— y no como área continua: la
 * magnitud es por celda, y el resto de las figuras espaciales (silueta de la
 * ciudad, distribución por estrato, diagrama de red) ya usan esa gramática.
 * Con área+línea el eje X sugería una variable continua que no existe.
 *
 * Todo (ejes, ticks, etiquetas, encabezado) se dibuja DENTRO del `<svg>` con
 * ancho medido en píxeles reales — así la figura exporta completa a SVG/PNG y
 * el texto no se deforma. Escala Y: `yMax` compartido entre paneles para
 * comparación visual; si no se entrega, usa el máximo local.
 */
export function FlowProfile({
  flows,
  largoKm,
  label,
  color = "var(--ink)",
  yMax = null,
  capacity = null,
  capacityLabel,
  valueFmt = (v: number) => String(Math.round(v)),
  height = 120,
  className,
}: FlowProfileProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(360);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(240, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const H = height + MARGIN.top + MARGIN.bottom;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = height;
  const yTop = MARGIN.top;
  const yFloor = MARGIN.top + plotH;

  const localMax = useMemo(() => Math.max(...flows, 1), [flows]);

  // La capacidad entra en la escala: si el flujo queda por debajo, la línea
  // igual tiene que caber en el gráfico; si lo supera, se ve por cuánto.
  const base = yMax != null ? Math.max(yMax, 1) : localMax;
  const scale = Math.max(base, capacity ?? 0, 1);
  const effectiveMax = yMax ?? localMax;
  const ticks = [0, scale / 2, scale];
  // Una barra por celda, igual que StratumDistribution/CityStrip. Con 201
  // celdas la barra mide ~2 px: se dibuja sin separación para que la envolvente
  // se lea; con pocas celdas se deja 1 px de aire y se ven individuales.
  const nCeldas = Math.max(flows.length, 1);
  const barW = plotW / nCeldas;
  const rectW = barW > 3 ? barW - 1 : barW;
  const cbdX = MARGIN.left + (Math.floor(nCeldas / 2) + 0.5) * barW;

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
        aria-label={label ?? "flujo"}
      >
        {/* Encabezado: label (izq) y max/cap (der) */}
        {label && (
          <text x={MARGIN.left} y={11} textAnchor="start" className="label">
            {label}
          </text>
        )}
        <text
          x={MARGIN.left + plotW}
          y={11}
          textAnchor="end"
          className="label"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {`max ${valueFmt(localMax)}${capacity ? ` · v/c ${(localMax / capacity).toFixed(2)}` : ""}`}
        </text>

        {/* Grid + etiquetas Y */}
        {ticks.map((v, i) => {
          const y = yFloor - (v / scale) * plotH;
          return (
            <g key={i}>
              <line
                x1={MARGIN.left}
                y1={y}
                x2={MARGIN.left + plotW}
                y2={y}
                stroke="var(--rule)"
                strokeWidth={0.6}
                strokeDasharray="2 3"
                opacity={0.6}
              />
              <text
                x={MARGIN.left - 6}
                y={y + 3}
                textAnchor="end"
                className="label"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {valueFmt(v)}
              </text>
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
          opacity={0.6}
        />

        {/* Barras por celda, con el color pleno del modo. */}
        {flows.map((f, i) => {
          if (!(f > 0)) return null;
          const h = (Math.min(f, scale) / scale) * plotH;
          if (h <= 0) return null;
          return (
            <rect
              key={i}
              x={MARGIN.left + i * barW}
              y={yFloor - h}
              width={rectW}
              height={h}
              fill={color}
              opacity={0.75}
            />
          );
        })}

        {/* Capacidad: línea sobre la MISMA escala que las barras, así el cruce
            v/c = 1 se lee de un vistazo en vez de tener que comparar cifras. */}
        {capacity != null && capacity > 0 && (
          <g>
            <line
              x1={MARGIN.left}
              y1={yFloor - (capacity / scale) * plotH}
              x2={MARGIN.left + plotW}
              y2={yFloor - (capacity / scale) * plotH}
              stroke="var(--s1)"
              strokeWidth={1.2}
              strokeDasharray="5 3"
            />
            <text
              x={MARGIN.left + plotW - 2}
              y={yFloor - (capacity / scale) * plotH - 3}
              textAnchor="end"
              className="label"
              fill="var(--s1)"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {`cap ${valueFmt(capacity)}${capacityLabel ? ` ${capacityLabel}` : ""}`}
            </text>
          </g>
        )}

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
        <text x={MARGIN.left} y={H - 5} textAnchor="start" className="label">
          0 KM
        </text>
        <text
          x={cbdX}
          y={H - 5}
          textAnchor="middle"
          className="label"
          fill="var(--accent)"
        >
          CBD
        </text>
        <text
          x={MARGIN.left + plotW}
          y={H - 5}
          textAnchor="end"
          className="label"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {largoKm.toFixed(0)} KM
        </text>
      </svg>
      {/* effectiveMax expuesto para tooltips/lectores; no se muestra aparte */}
      <span className="sr-only">{`max ${Math.round(effectiveMax)}`}</span>
    </div>
  );
}
