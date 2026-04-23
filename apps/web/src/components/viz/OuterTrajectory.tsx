import { useMemo, useState } from "react";
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

import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { cn } from "@/lib/cn";
import type { CoupledResult } from "@/lib/types-v2";

interface OuterTrajectoryProps {
  result: CoupledResult;
  className?: string;
}

/**
 * Muestra la trayectoria completa del loop acoplado:
 *   - Residuo ||T_new - T_old|| por iteración exterior (line chart).
 *   - Distribución espacial de hogares por estrato en cada iteración (slider).
 *
 * Permite al estudiante ver cómo la ciudad "se reacomoda" mientras suelo y
 * transporte convergen mutuamente.
 */
export function OuterTrajectory({ result, className }: OuterTrajectoryProps) {
  const { t } = useTranslation("simulator");
  const [selected, setSelected] = useState(result.iterations.length - 1);
  const iter = result.iterations[selected];

  const residualData = useMemo(
    () =>
      result.iterations.map((it) => ({
        iter: it.outer_iter + 1,
        residual: it.T_residual == null ? null : it.T_residual,
      })),
    [result.iterations]
  );

  if (result.iterations.length === 0 || !iter) {
    return null;
  }

  // Para la última iteración preferimos `final_parcelas` (asignación real);
  // para las intermedias, o si streaming no incluye la asignación final,
  // reconstruimos desde la matriz Q.
  const isLast = selected === result.iterations.length - 1;
  const parcelasForSlide =
    isLast && result.final_parcelas.length > 0
      ? result.final_parcelas
      : approximateParcelasFromQ(iter.land_use.Q);

  return (
    <div className={cn(className)} style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
      <div style={{ border: "1px solid var(--rule)", padding: 12, background: "var(--paper)" }}>
        <h4
          style={{
            margin: 0,
            fontFamily: "var(--font-fig)",
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--muted)",
          }}
        >
          {t("land_use.trajectory_residual_title")}
        </h4>
        <p
          style={{
            margin: "4px 0 10px",
            fontFamily: "var(--font-fig)",
            fontSize: 10,
            color: "var(--muted)",
            letterSpacing: "0.04em",
          }}
        >
          {t("land_use.trajectory_residual_desc")}
        </p>
        <div style={{ width: "100%", height: 160 }}>
          <ResponsiveContainer>
            <LineChart data={residualData} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="2 3" stroke="var(--rule)" opacity={0.6} />
              <XAxis
                dataKey="iter"
                stroke="var(--muted)"
                fontSize={10}
                tickLine={{ stroke: "var(--rule)" }}
                axisLine={{ stroke: "var(--rule)" }}
                style={{ fontFamily: "var(--font-fig)" }}
              />
              <YAxis
                stroke="var(--muted)"
                fontSize={10}
                tickLine={{ stroke: "var(--rule)" }}
                axisLine={{ stroke: "var(--rule)" }}
                style={{ fontFamily: "var(--font-fig)" }}
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

      <div style={{ border: "1px solid var(--rule)", padding: 12, background: "var(--paper)" }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: 10,
          }}
        >
          <h4
            style={{
              margin: 0,
              fontFamily: "var(--font-fig)",
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            {t("land_use.trajectory_spatial_title")}
          </h4>
          <div
            style={{
              fontFamily: "var(--font-fig)",
              fontSize: 11,
              letterSpacing: "0.04em",
              color: "var(--muted)",
            }}
          >
            {t("land_use.trajectory_outer_counter")}{" "}
            <span
              style={{
                color: "var(--ink)",
                fontWeight: 600,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {selected + 1} / {result.iterations.length}
            </span>
          </div>
        </div>
        <input
          type="range"
          min={0}
          max={result.iterations.length - 1}
          step={1}
          value={selected}
          onChange={(e) => setSelected(Number(e.target.value))}
          style={{ width: "100%", marginBottom: 14 }}
        />
        <StratumDistribution parcelas={parcelasForSlide} />
        <div
          style={{
            marginTop: 12,
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 8,
          }}
        >
          <Stat
            label={t("equilibrium.residual")}
            value={iter.T_residual == null ? "—" : `${iter.T_residual.toFixed(2)} min`}
          />
          <Stat
            label={t("land_use.logit_converged")}
            value={iter.land_use.converged ? t("land_use.yes") : t("land_use.no")}
          />
          <Stat label={t("land_use.logit_iterations")} value={String(iter.land_use.iterations)} />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        border: "1px solid var(--rule)",
        padding: "6px 10px",
        background: "var(--paper-2)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-fig)",
          fontSize: 9,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--muted)",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-fig)",
          fontSize: 13,
          fontWeight: 600,
          color: "var(--ink)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
      </div>
    </div>
  );
}

/**
 * Aproxima la distribución espacial a partir de la matriz Q: para cada parcela
 * `i`, sortea el estrato con más masa en Q[:, i]. Es una reconstrucción
 * determinista — no captura la aleatoriedad del algoritmo original — pero
 * sirve para ilustrar cómo la ciudad evoluciona entre iteraciones.
 */
function approximateParcelasFromQ(Q: number[][]): number[][] {
  const nStrata = Q.length;
  const I = Q[0]?.length ?? 0;
  const parcelas: number[][] = Array.from({ length: I }, () => []);
  for (let i = 0; i < I; i++) {
    let bestH = -1;
    let bestV = -Infinity;
    for (let h = 0; h < nStrata; h++) {
      const v = Q[h]?.[i] ?? 0;
      if (v > bestV) {
        bestV = v;
        bestH = h;
      }
    }
    if (bestH >= 0 && bestV > 0) {
      parcelas[i]!.push(bestH + 1);
    }
  }
  return parcelas;
}
