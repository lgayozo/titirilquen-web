import katex from "katex";
import { useMemo } from "react";

import { cn } from "@/lib/cn";

interface EquationProps {
  tex: string;
  display?: boolean;
  className?: string;
}

export function Equation({ tex, display = false, className }: EquationProps) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(tex, { displayMode: display, throwOnError: false });
    } catch {
      return tex;
    }
  }, [tex, display]);

  return (
    <span
      className={cn(display ? "block my-2 text-center" : "inline-block", className)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
