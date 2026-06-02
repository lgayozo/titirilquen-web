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
  /** Geometría para reconstruir la oferta S(i) y la distribución por estrato. */
  nCeldas: number;
  totalHogares: number;
  sigmaFrac: number;
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
export function OuterTrajectory({
  result,
  nCeldas,
  totalHogares,
  sigmaFrac,
  className,
}: OuterTrajectoryProps) {
  const { t } = useTranslation("simulator");
  const [selected, setSelected] = useState(result.iterations.length - 1);
  const iter = result.iterations[selected];

  // Oferta S(i) determinista (espejo de land_use/supply.py:generar_oferta_normal_det),
  // constante en el loop. La distribución por estrato se reconstruye como
  // hogares[h,i] = round(S[i]·Q[h,i]) — la asignación esperada del equilibrio.
  const S = useMemo(() => {
    const CBD = Math.floor(nCeldas / 2);
    const sigma = Math.max(sigmaFrac * Math.min(CBD, nCeldas - 1 - CBD), 1e-6);
    const w = new Array(nCeldas).fill(0).map((_, i) => Math.exp(-0.5 * ((i - CBD) / sigma) ** 2));
    w[CBD] = 0;
    const total = w.reduce((a, b) => a + b, 0) || 1;
    const target = w.map((x) => (x / total) * totalHogares);
    const arr = target.map((x) => Math.floor(x));
    const resto = totalHogares - arr.reduce((a, b) => a + b, 0);
    const order = target
      .map((x, i) => ({ frac: i === CBD ? -1 : x - Math.floor(x), i }))
      .sort((a, b) => b.frac - a.frac);
    for (let k = 0; k < resto && k < order.length; k++) {
      const idx = order[k]!.i;
      arr[idx] = (arr[idx] ?? 0) + 1;
    }
    return arr;
  }, [nCeldas, totalHogares, sigmaFrac]);

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
      : reconstructParcelas(iter.land_use.Q, S);

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
 * Reconstruye la distribución espacial de hogares por estrato a partir de la
 * matriz Q y la oferta S: para cada parcela `i`, el estrato `h` aporta
 * `round(S[i]·Q[h,i])` hogares (la asignación esperada del equilibrio logit,
 * dado que Q[:,i] suma 1 y la parcela tiene S[i] lotes). Reproduce la campana
 * con las magnitudes reales, consistente con la vista standalone.
 */
function reconstructParcelas(Q: number[][], S: readonly number[]): number[][] {
  const nStrata = Q.length;
  const I = S.length;
  const parcelas: number[][] = Array.from({ length: I }, () => []);
  for (let i = 0; i < I; i++) {
    for (let h = 0; h < nStrata; h++) {
      const cnt = Math.round((S[i] ?? 0) * (Q[h]?.[i] ?? 0));
      for (let k = 0; k < cnt; k++) parcelas[i]!.push(h + 1);
    }
  }
  return parcelas;
}
