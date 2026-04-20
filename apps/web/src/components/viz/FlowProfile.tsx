import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface FlowProfileProps {
  flows: readonly number[];
  largoKm: number;
  label?: string;
  color?: string;
  capacity?: number | null;
  height?: number;
  className?: string;
}

/**
 * Perfil de flujo (carga) por celda a lo largo de la ciudad.
 * Se muestra como área rellena. Si se pasa `capacity`, se dibuja como línea
 * punteada para comparar la capacidad del modo con la demanda observada.
 */
export function FlowProfile({
  flows,
  largoKm,
  label,
  color = "#0ea5e9",
  capacity = null,
  height = 80,
  className,
}: FlowProfileProps) {
  const { t } = useTranslation("simulator");
  const { path, max } = useMemo(() => {
    const N = flows.length;
    if (N === 0) return { path: "", max: 1 };
    const max = Math.max(...flows, capacity ?? 0, 1);
    const pts: string[] = [];
    pts.push(`M0,100`);
    flows.forEach((f, i) => {
      const x = (i / (N - 1)) * 100;
      const y = 100 - (f / max) * 95;
      pts.push(`L${x.toFixed(2)},${y.toFixed(2)}`);
    });
    pts.push(`L100,100`);
    pts.push(`Z`);
    return { path: pts.join(" "), max };
  }, [flows, capacity]);

  const capY = capacity != null ? 100 - (capacity / max) * 95 : null;

  return (
    <div className={cn("relative", className)}>
      {label && (
        <div className="mb-1 flex items-center justify-between text-[11px]">
          <span className="font-medium text-slate-600 dark:text-slate-300">{label}</span>
          <span className="font-mono tabular-nums text-slate-500">
            {t("flow_profile.max", { value: Math.round(max).toLocaleString() })}
          </span>
        </div>
      )}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="block w-full border border-slate-200 dark:border-slate-800"
        style={{ height }}
      >
        <path d={path} fill={color} opacity={0.25} />
        <path d={path.replace(/M.*?L/, "M").replace(/L100,100 Z$/, "")} fill="none" stroke={color} strokeWidth={0.6} />
        {capY != null && (
          <line
            x1={0}
            y1={capY}
            x2={100}
            y2={capY}
            stroke={color}
            strokeWidth={0.4}
            strokeDasharray="1 1"
          />
        )}
        <line x1={50} y1={0} x2={50} y2={100} stroke="#ef4444" strokeWidth={0.4} strokeDasharray="1 1" opacity={0.5} />
      </svg>
      <div className="flex justify-between text-[10px] text-slate-400">
        <span>0 km</span>
        <span>CBD</span>
        <span>{largoKm.toFixed(0)} km</span>
      </div>
    </div>
  );
}
