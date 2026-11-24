import { cn } from "@/lib/cn";

export interface KPI {
  label: string;
  value: string;
  unit?: string;
  color?: string;
  delta?: string;
  /** Línea secundaria bajo el valor (p. ej. el parking por viaje), para que
   *  el valor no desborde la celda. */
  sub?: string;
}

interface KPIStripProps {
  items: readonly KPI[];
  className?: string;
}

/**
 * Fila de tarjetas KPI. Cada una lleva etiqueta, valor (Mono) y opcionales
 * unidad, delta y línea secundaria. El color de la variable (p. ej. el modo)
 * va en un punto junto a la etiqueta y no en la cifra: el gris de la
 * caminata, como texto sobre blanco, no alcanzaba contraste legible.
 */
export function KPIStrip({ items, className }: KPIStripProps) {
  return (
    <div className={cn("kpis", className)}>
      {items.map((it, i) => (
        <div key={i} className="kpi">
          <div className="label">
            {it.color && (
              <span
                className="kpi-dot"
                style={{ background: it.color }}
                aria-hidden
              />
            )}
            {it.label}
          </div>
          <div className="value">
            {it.value}
            {it.unit && <span className="unit">{it.unit}</span>}
          </div>
          {it.delta && <div className="delta">{it.delta}</div>}
          {it.sub && <div className="sub">{it.sub}</div>}
        </div>
      ))}
    </div>
  );
}
