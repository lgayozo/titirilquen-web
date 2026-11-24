import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { cn } from "@/lib/cn";
import type { CoupledResult } from "@/lib/types-v2";
import { fmtDecimal, localeCifras } from "@/lib/modos";

interface OuterTrajectoryProps {
  result: CoupledResult;
  className?: string;
}

/**
 * Curva de convergencia del loop acoplado: residuo max|T_new − T_old|/λ_h
 * ($/hogar-mes, `coupled.py`) por iteración exterior. Debe tender a 0 cuando suelo y transporte se reconcilian.
 *
 * La distribución espacial por estrato vive en los paneles "Sin/Con feedback"
 * (Comparison) — acá no se repite para evitar redundancia.
 */
export function OuterTrajectory({ result, className }: OuterTrajectoryProps) {
  const { t } = useTranslation("simulator");

  const residualData = useMemo(
    () =>
      result.iterations.map((it) => ({
        iter: it.outer_iter + 1,
        residual: it.T_residual == null ? null : it.T_residual,
      })),
    [result.iterations],
  );

  if (result.iterations.length === 0) {
    return null;
  }

  return (
    <div className={cn(className)}>
      <div style={{ width: "100%", height: 200 }}>
        <ResponsiveContainer>
          <LineChart
            data={residualData}
            margin={{ top: 8, right: 16, bottom: 4, left: 4 }}
          >
            <CartesianGrid
              strokeDasharray="2 3"
              stroke="var(--rule)"
              opacity={0.6}
            />
            <XAxis
              dataKey="iter"
              stroke="var(--muted)"
              fontSize={12}
              tickLine={{ stroke: "var(--rule)" }}
              axisLine={{ stroke: "var(--rule)" }}
              style={{ fontFamily: "var(--font-fig)" }}
              label={{
                value: t("convergence.iter"),
                position: "insideBottom",
                offset: -2,
                style: {
                  fontFamily: "var(--font-body)",
                  fontSize: 12,
                  fill: "var(--muted)",
                },
              }}
            />
            <YAxis
              stroke="var(--muted)"
              fontSize={12}
              tickLine={{ stroke: "var(--rule)" }}
              axisLine={{ stroke: "var(--rule)" }}
              style={{ fontFamily: "var(--font-fig)" }}
              width={52}
              tickFormatter={(v: number) => v.toLocaleString(localeCifras())}
              label={{
                value: t("convergence.y_clp_mes"),
                angle: -90,
                position: "insideLeft",
                offset: 12,
                style: {
                  fontFamily: "var(--font-body)",
                  fontSize: 12,
                  fill: "var(--muted)",
                  textAnchor: "middle",
                },
              }}
            />
            <Tooltip
              contentStyle={{
                fontFamily: "var(--font-fig)",
                fontSize: 12,
                background: "var(--panel)",
                border: "1px solid var(--rule)",
                borderRadius: 7,
                color: "var(--ink)",
              }}
              labelStyle={{ color: "var(--muted)" }}
              labelFormatter={(v) => `${t("convergence.iter")} ${v}`}
              formatter={(v: number | string) =>
                typeof v === "number"
                  ? `${fmtDecimal(v)} $/hogar-mes`
                  : String(v)
              }
            />
            <Line
              type="monotone"
              dataKey="residual"
              stroke="var(--accent)"
              strokeWidth={2}
              dot={{ r: 3, fill: "var(--accent)" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
