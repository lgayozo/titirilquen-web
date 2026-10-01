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
import { COLOR_MODO, ORDEN_MODOS } from "@/lib/modos";

interface ConvergenceTraceProps {
  iterations: readonly IterationSnapshot[];
  className?: string;
}

const AXIS_STYLE = {
  fontFamily: "var(--font-fig)",
  fontSize: 10,
  letterSpacing: "0.04em",
};

const PANEL_STYLE: React.CSSProperties = {
  border: "1px solid var(--rule)",
  background: "var(--paper)",
  padding: 12,
};

const PANEL_TITLE: React.CSSProperties = {
  margin: 0,
  fontFamily: "var(--font-fig)",
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: "var(--muted)",
};

const PANEL_SUB: React.CSSProperties = {
  margin: "4px 0 10px",
  fontFamily: "var(--font-fig)",
  fontSize: 10,
  letterSpacing: "0.04em",
  color: "var(--muted)",
};

const TOOLTIP_STYLE: React.CSSProperties = {
  fontFamily: "var(--font-fig)",
  fontSize: 11,
  background: "var(--paper)",
  border: "1px solid var(--rule)",
  borderRadius: 0,
  color: "var(--ink)",
};

export function ConvergenceTrace({
  iterations,
  className,
}: ConvergenceTraceProps) {
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
    [iterations],
  );

  if (data.length === 0) return null;

  const fmtMin = (v: number | string) =>
    typeof v === "number" ? `${v.toFixed(3)} min` : String(v);
  // Ticks del residuo: hasta 3 decimales pero sin ceros sobrantes (12.000 → 12,
  // 0.030 → 0.03) para que no invadan la etiqueta rotada del eje Y.
  const fmtResidualTick = (v: number) => String(Number(v.toFixed(3)));
  const fmtTrips = (v: number | string) =>
    typeof v === "number"
      ? `${v.toLocaleString("es-CL")} ${t("convergence.trips_unit")}`
      : String(v);
  // Ticks compactos (10000 → "10k") para que no invadan la etiqueta del eje Y.
  const fmtTickCompact = (v: number) =>
    Math.abs(v) >= 1000
      ? `${(v / 1000).toFixed(v % 1000 === 0 ? 0 : 1)}k`
      : `${v}`;

  return (
    <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-2", className)}>
      <div style={PANEL_STYLE}>
        <h4 style={PANEL_TITLE}>{t("equilibrium.residual")}</h4>
        <p style={PANEL_SUB}>
          ‖T<sub>n</sub> − T<sub>n−1</sub>‖<sub>∞</sub> · min · debe tender a 0
        </p>
        <div style={{ width: "100%", height: 180 }}>
          <ResponsiveContainer>
            <LineChart
              data={data}
              margin={{ top: 8, right: 16, bottom: 4, left: 8 }}
            >
              <CartesianGrid
                strokeDasharray="2 3"
                stroke="var(--rule)"
                opacity={0.6}
              />
              <XAxis
                dataKey="iter"
                stroke="var(--muted)"
                tickLine={{ stroke: "var(--rule)" }}
                axisLine={{ stroke: "var(--rule)" }}
                style={AXIS_STYLE}
              />
              <YAxis
                stroke="var(--muted)"
                tickLine={{ stroke: "var(--rule)" }}
                axisLine={{ stroke: "var(--rule)" }}
                style={AXIS_STYLE}
                width={52}
                tickFormatter={fmtResidualTick}
                label={{
                  value: t("convergence.y_min"),
                  angle: -90,
                  position: "insideLeft",
                  offset: 0,
                  style: {
                    ...AXIS_STYLE,
                    fill: "var(--muted)",
                    textAnchor: "middle",
                  },
                }}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelStyle={{ color: "var(--muted)" }}
                labelFormatter={(v) => `${t("convergence.iter")} ${v}`}
                formatter={fmtMin}
              />
              <Line
                type="monotone"
                dataKey="residuo"
                name={t("equilibrium.residual")}
                stroke="var(--accent)"
                strokeWidth={2}
                dot={{ r: 2, fill: "var(--accent)" }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={PANEL_STYLE}>
        <h4 style={PANEL_TITLE}>{t("convergence.modal_split_title")}</h4>
        <p style={PANEL_SUB}>{t("convergence.modal_split_sub")}</p>
        <div style={{ width: "100%", height: 180 }}>
          <ResponsiveContainer>
            <AreaChart
              data={data}
              margin={{ top: 8, right: 16, bottom: 4, left: 8 }}
            >
              <CartesianGrid
                strokeDasharray="2 3"
                stroke="var(--rule)"
                opacity={0.6}
              />
              <XAxis
                dataKey="iter"
                stroke="var(--muted)"
                tickLine={{ stroke: "var(--rule)" }}
                axisLine={{ stroke: "var(--rule)" }}
                style={AXIS_STYLE}
              />
              <YAxis
                stroke="var(--muted)"
                tickLine={{ stroke: "var(--rule)" }}
                axisLine={{ stroke: "var(--rule)" }}
                style={AXIS_STYLE}
                width={52}
                tickFormatter={fmtTickCompact}
                label={{
                  value: t("convergence.y_trips"),
                  angle: -90,
                  position: "insideLeft",
                  offset: 12,
                  style: {
                    ...AXIS_STYLE,
                    fill: "var(--muted)",
                    textAnchor: "middle",
                  },
                }}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelStyle={{ color: "var(--muted)" }}
                labelFormatter={(v) => `${t("convergence.iter")} ${v}`}
                formatter={fmtTrips}
              />
              <Legend
                wrapperStyle={{
                  fontFamily: "var(--font-fig)",
                  fontSize: 10,
                  letterSpacing: "0.04em",
                }}
              />
              {ORDEN_MODOS.map((m) => (
                <Area
                  key={m}
                  type="monotone"
                  dataKey={m}
                  stackId="1"
                  stroke={COLOR_MODO[m]}
                  fill={COLOR_MODO[m]}
                  fillOpacity={0.7}
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
