import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface PanelProps {
  /** Número de figura (ej. "01", "02"). Se muestra como "FIG. NN" en accent. */
  n?: string;
  title: string;
  meta?: ReactNode;
  /** Columnas en el grid de 12 (col-4 | col-5 | col-6 | col-7 | col-8 | col-12). */
  cls?: "col-3" | "col-4" | "col-5" | "col-6" | "col-7" | "col-8" | "col-9" | "col-12";
  children: ReactNode;
  className?: string;
}

/**
 * Panel editorial: caja con borde, header con "FIG. NN" + título serif + meta
 * en mono, separador inferior y body padded. Usa el grid de 12 columnas.
 */
export function Panel({ n, title, meta, cls = "col-6", children, className }: PanelProps) {
  return (
    <div className={cn("panel", cls, className)}>
      <div className="panel-head">
        <div className="panel-title">
          {n && <span className="n">FIG. {n}</span>}
          <h4>{title}</h4>
        </div>
        {meta && <div className="panel-meta">{meta}</div>}
      </div>
      <div className="panel-body">{children}</div>
    </div>
  );
}
