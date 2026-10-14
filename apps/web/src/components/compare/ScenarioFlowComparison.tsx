import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { IterationSnapshot, Modo, SimulationResult } from "@/lib/types";

interface ScenarioFlowComparisonProps {
  scenarios: Array<{
    id: string;
    name: string;
    result: SimulationResult | null;
    config: SimulationConfigSlice | null;
  }>;
  mode: Modo;
  className?: string;
}

type SimulationConfigSlice = {
  city: { n_celdas: number; largo_ciudad_km: number };
};

/**
 * Overlay de perfiles de flujo por celda — varios escenarios en el mismo gráfico
 * para comparar visualmente cómo cambia la distribución espacial de demanda.
 */
export function ScenarioFlowComparison({
  scenarios,
  mode,
  className,
}: ScenarioFlowComparisonProps) {
  const { t } = useTranslation("simulator");
  const modeKey = useMemo(() => {
    if (mode === "Auto") return "demanda_auto";
    if (mode === "Metro") return "demanda_metro";
    if (mode === "Bici") return "demanda_bici";
    return null;
  }, [mode]);

  if (!modeKey) {
    return (
      <div className="rounded border border-[var(--rule)] p-8 text-center text-xs text-[var(--muted)]">
        {t("compare.flow_no_profile", {
          mode: t(`modes.${mode.toLowerCase()}`),
        })}
      </div>
    );
  }

  const curves = scenarios
    .filter(
      (
        s,
      ): s is typeof s & {
        result: SimulationResult;
        config: SimulationConfigSlice;
      } => s.result != null && s.config != null,
    )
    .map((s) => {
      const last = s.result.iteraciones.at(-1);
      if (!last) return null;
      return {
        id: s.id,
        name: s.name,
        data: (last as IterationSnapshot)[
          modeKey as keyof IterationSnapshot
        ] as number[],
      };
    })
    .filter(
      (c): c is { id: string; name: string; data: number[] } => c !== null,
    );

  if (curves.length === 0) {
    return (
      <div className="rounded border border-dashed border-[var(--rule)] p-8 text-center text-xs text-[var(--muted)]">
        {t("compare.flow_empty")}
      </div>
    );
  }

  const max = Math.max(1, ...curves.flatMap((c) => c.data));
  // El escenario no es un modo ni un estrato: se distingue por el trazo, en
  // tinta (B1). Antes eran cuatro colores fijos que no seguían el tema y que
  // chocaban con los de los modos de la misma página.
  const dashes = [undefined, "6 3", "1.5 2.5", "7 2.5 1.5 2.5"];

  return (
    <div className={cn("rounded border border-[var(--rule)] p-3", className)}>
      <div className="mb-2 flex items-center gap-3 text-[11px]">
        <span className="font-medium text-[var(--ink-2)]">
          {t("compare.flow_demand_label", {
            mode: t(`modes.${mode.toLowerCase()}`),
          })}
        </span>
        {curves.map((c, i) => (
          <span key={c.id} className="flex items-center gap-1">
            <svg width={22} height={8} aria-hidden>
              <line
                x1={0}
                y1={4}
                x2={22}
                y2={4}
                stroke="var(--ink)"
                strokeWidth={1.5}
                strokeDasharray={dashes[i % dashes.length]}
              />
            </svg>
            {c.name}
          </span>
        ))}
      </div>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="block w-full"
        style={{ height: 140 }}
      >
        <line
          x1={50}
          y1={0}
          x2={50}
          y2={100}
          stroke="var(--muted)"
          strokeWidth={1}
          strokeDasharray="2 3"
          vectorEffect="non-scaling-stroke"
        />
        {curves.map((c, i) => {
          const N = c.data.length;
          const pts: string[] = [];
          c.data.forEach((v, j) => {
            const x = (j / Math.max(N - 1, 1)) * 100;
            const y = 100 - (v / max) * 95;
            pts.push(`${j === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`);
          });
          return (
            <path
              key={c.id}
              d={pts.join(" ")}
              fill="none"
              stroke="var(--ink)"
              strokeWidth={1.5}
              strokeDasharray={dashes[i % dashes.length]}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
    </div>
  );
}
