import { useMemo } from "react";

import { cn } from "@/lib/cn";

interface BidPriceCurveProps {
  p: readonly number[];
  className?: string;
  height?: number;
}

/**
 * Precios implícitos por parcela en el equilibrio. Útil para ver la curva de
 * renta urbana (esperada: forma de "cerro" centrada en el CBD).
 */
export function BidPriceCurve({ p, className, height = 100 }: BidPriceCurveProps) {
  const { path, min, max } = useMemo(() => {
    const finite = p.filter(Number.isFinite);
    const mn = Math.min(...finite);
    const mx = Math.max(...finite);
    const range = Math.max(mx - mn, 1e-6);
    const parts: string[] = [];
    p.forEach((v, i) => {
      const x = (i / Math.max(p.length - 1, 1)) * 100;
      const y = Number.isFinite(v) ? 95 - ((v - mn) / range) * 90 : 100;
      parts.push(`${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`);
    });
    return { path: parts.join(" "), min: mn, max: mx };
  }, [p]);

  return (
    <div className={cn("relative", className)}>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="font-medium text-slate-600 dark:text-slate-300">
          Precio implícito del suelo
        </span>
        <span className="font-mono tabular-nums text-slate-500">
          [{min.toFixed(1)}, {max.toFixed(1)}]
        </span>
      </div>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="block w-full rounded border border-slate-200 dark:border-slate-800"
        style={{ height }}
      >
        <path d={path} fill="none" stroke="#a855f7" strokeWidth={0.8} />
        <line x1={50} y1={0} x2={50} y2={100} stroke="#ef4444" strokeWidth={0.4} strokeDasharray="1 1" opacity={0.6} />
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        <span>0</span>
        <span>CBD</span>
        <span>L</span>
      </div>
    </div>
  );
}
