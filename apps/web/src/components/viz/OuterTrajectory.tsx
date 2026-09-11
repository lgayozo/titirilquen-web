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

interface OuterTrajectoryProps {
  result: CoupledResult;
  className?: string;
}

/**
 * Curva de convergencia del loop acoplado: residuo ‖T_new − T_old‖∞ (min) por
 * iteración exterior. Debe tender a 0 cuando suelo y transporte se reconcilian.
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
              fontSize={10}
              tickLine={{ stroke: "var(--rule)" }}
              axisLine={{ stroke: "var(--rule)" }}
              style={{ fontFamily: "var(--font-fig)" }}
              label={{
                value: t("convergence.iter"),
                position: "insideBottom",
                offset: -2,
                style: {
                  fontFamily: "var(--font-fig)",
                  fontSize: 10,
                  fill: "var(--muted)",
                },
              }}
            />
            <YAxis
              stroke="var(--muted)"
              fontSize={10}
              tickLine={{ stroke: "var(--rule)" }}
              axisLine={{ stroke: "var(--rule)" }}
              style={{ fontFamily: "var(--font-fig)" }}
              width={52}
              label={{
                value: t("convergence.y_min"),
                angle: -90,
                position: "insideLeft",
                offset: 12,
                style: {
                  fontFamily: "var(--font-fig)",
                  fontSize: 10,
                  fill: "var(--muted)",
                  textAnchor: "middle",
                },
              }}
            />
            <Tooltip
              contentStyle={{
                fontFamily: "var(--font-fig)",
                fontSize: 11,
                background: "var(--paper)",
                border: "1px solid var(--rule)",
                borderRadius: 0,
                color: "var(--ink)",
              }}
              labelStyle={{ color: "var(--muted)" }}
              labelFormatter={(v) => `${t("convergence.iter")} ${v}`}
              formatter={(v: number | string) =>
                typeof v === "number" ? `${v.toFixed(3)} min` : String(v)
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
