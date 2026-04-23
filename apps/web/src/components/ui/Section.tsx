import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { cn } from "@/lib/cn";

interface SectionProps {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  className?: string;
  children: ReactNode;
}

/**
 * Sección colapsable estilo editorial: header con título en mayúsculas/mono
 * sobre una línea de regla inferior (como capítulos en un journal).
 */
export function Section({ title, subtitle, defaultOpen = true, className, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={cn("mb-4", className)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between border-b border-rule pb-1.5 pt-4 text-left font-fig text-[10px] uppercase tracking-[0.14em] text-muted"
      >
        <span>
          {title}
          {subtitle && <span className="ml-2 normal-case tracking-normal text-ink-2/70">· {subtitle}</span>}
        </span>
        {open ? (
          <ChevronDown className="h-3 w-3" aria-hidden />
        ) : (
          <ChevronRight className="h-3 w-3" aria-hidden />
        )}
      </button>
      {open && <div className="space-y-3 py-3">{children}</div>}
    </section>
  );
}
