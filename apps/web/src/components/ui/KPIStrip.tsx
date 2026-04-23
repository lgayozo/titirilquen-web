import { cn } from "@/lib/cn";

export interface KPI {
  label: string;
  value: string;
  unit?: string;
  color?: string;
  delta?: string;
}

interface KPIStripProps {
  items: readonly KPI[];
  className?: string;
}

/**
 * KPI strip editorial: grid horizontal con dividers verticales entre celdas.
 * Cada KPI tiene label (mono, caps), value (serif grande) y opcional unit/delta.
 */
export function KPIStrip({ items, className }: KPIStripProps) {
  return (
    <div
      className={cn("kpis", className)}
      style={{ gridTemplateColumns: `repeat(${items.length}, 1fr)` }}
    >
      {items.map((it, i) => (
        <div key={i} className="kpi">
          <div className="label">{it.label}</div>
          <div className="value" style={{ color: it.color }}>
            {it.value}
            {it.unit && <span className="unit">{it.unit}</span>}
          </div>
          {it.delta && <div className="delta">{it.delta}</div>}
        </div>
      ))}
    </div>
  );
}
