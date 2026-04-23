import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface SidebarSectionProps {
  title: string;
  /** Si se entrega, aparece en mono al lado del título (hint o stat). */
  meta?: string;
  /** Por defecto cerrado — el usuario despliega la sección que quiere editar. */
  defaultOpen?: boolean;
  children: ReactNode;
  className?: string;
}

/**
 * Sección desplegable editorial para el sidebar. Usa `<details>` nativo —
 * accesible con teclado (Enter/Space) y lectores de pantalla (se anuncia
 * automáticamente el estado expandido/colapsado). Se estiliza el summary para
 * que luzca como el h3 editorial + chevron rotatorio.
 */
export function SidebarSection({
  title,
  meta,
  defaultOpen = false,
  children,
  className,
}: SidebarSectionProps) {
  return (
    <details className={cn("sidebar-section", className)} open={defaultOpen}>
      <summary>
        <span className="sidebar-section-title">{title}</span>
        {meta && <span className="sidebar-section-meta">{meta}</span>}
        <span className="sidebar-section-chevron" aria-hidden>
          ›
        </span>
      </summary>
      <div className="sidebar-section-body">{children}</div>
    </details>
  );
}
