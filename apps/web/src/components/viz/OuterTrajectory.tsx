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
    <div className={cn("space-y-4", className)}>
      <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("land_use.trajectory_residual_title")}
        </h4>
        <p className="mb-2 text-[11px] text-slate-400">
          {t("land_use.trajectory_residual_desc")}
        </p>
        <div style={{ width: "100%", height: 140 }}>
          <ResponsiveContainer>
            <LineChart data={residualData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="iter" stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip contentStyle={{ fontSize: 11, borderRadius: 4 }} />
              <Line
                type="monotone"
                dataKey="residual"
                stroke="#a855f7"
                strokeWidth={2}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <div className="mb-2 flex items-baseline justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t("land_use.trajectory_spatial_title")}
          </h4>
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-slate-400">{t("land_use.trajectory_outer_counter")}</span>
            <span className="font-mono font-semibold tabular-nums">
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
          className="mb-3 w-full accent-slate-900 dark:accent-slate-200"
        />
        <StratumDistribution parcelas={parcelasForSlide} />
        <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
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
    <div className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-900">
      <div className="text-slate-500">{label}</div>
      <div className="font-mono font-semibold tabular-nums">{value}</div>
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
