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

export function Section({ title, subtitle, defaultOpen = true, className, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section
      className={cn(
        "rounded-lg border border-slate-200 dark:border-slate-800",
        className
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        aria-expanded={open}
      >
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
          )}
        </div>
        {open ? (
          <ChevronDown className="h-4 w-4 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-400" />
        )}
      </button>
      {open && <div className="space-y-3 border-t border-slate-200 px-4 py-3 dark:border-slate-800">{children}</div>}
    </section>
  );
}
