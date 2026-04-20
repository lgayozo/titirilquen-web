import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { IterationSnapshot } from "@/lib/types";

interface ConvergenceTraceProps {
  iterations: readonly IterationSnapshot[];
  className?: string;
}

const MODE_COLORS = {
  Auto: "#FF8C00",
  Metro: "#FF0000",
  Bici: "#228B22",
  Caminata: "#0000FF",
  Teletrabajo: "#A9A9A9",
} as const;

const MODE_ORDER = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"] as const;

export function ConvergenceTrace({ iterations, className }: ConvergenceTraceProps) {
  const { t } = useTranslation("simulator");

  const data = useMemo(
    () =>
      iterations.map((it) => ({
        iter: it.iter + 1,
        residuo: it.residuo ?? null,
        Auto: it.modal_split.Auto ?? 0,
        Metro: it.modal_split.Metro ?? 0,
        Bici: it.modal_split.Bici ?? 0,
        Caminata: it.modal_split.Caminata ?? 0,
        Teletrabajo: it.modal_split.Teletrabajo ?? 0,
        frec: it.frecuencia_metro,
      })),
    [iterations]
  );

  if (data.length === 0) return null;

  return (
    <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-2", className)}>
      <div className="rounded border border-slate-200 p-3 dark:border-slate-800">
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("equilibrium.residual")}
        </h4>
        <p className="mb-2 text-[11px] text-slate-400">
          ‖T<sub>n</sub> − T<sub>n−1</sub>‖<sub>∞</sub> (min) — debe tender a 0
        </p>
        <div style={{ width: "100%", height: 160 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="iter" stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip
                contentStyle={{ fontSize: 11, borderRadius: 4 }}
                formatter={(v: number | string) => (typeof v === "number" ? v.toFixed(3) : String(v))}
              />
              <Line
                type="monotone"
                dataKey="residuo"
                stroke="#0ea5e9"
                strokeWidth={2}
                dot={{ r: 2 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded border border-slate-200 p-3 dark:border-slate-800">
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Modal split por iteración
        </h4>
        <p className="mb-2 text-[11px] text-slate-400">
          Evolución del reparto modal mientras el MSA suaviza
        </p>
        <div style={{ width: "100%", height: 160 }}>
          <ResponsiveContainer>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="iter" stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip contentStyle={{ fontSize: 11, borderRadius: 4 }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {MODE_ORDER.map((m) => (
                <Area
                  key={m}
                  type="monotone"
                  dataKey={m}
                  stackId="1"
                  stroke={MODE_COLORS[m]}
                  fill={MODE_COLORS[m]}
                  fillOpacity={0.6}
                  isAnimationActive={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
