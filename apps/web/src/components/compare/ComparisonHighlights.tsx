import { useTranslation } from "react-i18next";

import type { ScenarioKPIs } from "@/lib/kpis";
import type { StratumId } from "@/lib/types";

interface Row {
  id: string;
  name: string;
  kpis: ScenarioKPIs | null;
}

interface ComparisonHighlightsProps {
  scenarios: Row[];
  baseId?: string;
}

const STRATA: StratumId[] = [1, 2, 3];
const STRATUM_KEY: Record<StratumId, string> = {
  1: "alto",
  2: "medio",
  3: "bajo",
};

/**
 * Análisis automático de diferencias de cada escenario respecto a la base:
 * resalta CO₂, reparto auto, y el tiempo de viaje por estrato (tipo de usuario).
 */
export function ComparisonHighlights({
  scenarios,
  baseId,
}: ComparisonHighlightsProps) {
  const { t } = useTranslation("simulator");
  const base =
    scenarios.find((s) => s.id === baseId && s.kpis) ??
    scenarios.find((s) => s.kpis);
  const others = scenarios.filter((s) => s.kpis && s.id !== base?.id);
  if (!base?.kpis || others.length === 0) return null;
  const b = base.kpis;

  return (
    <div className="flex flex-col gap-3">
      <div className="font-fig text-[11px] uppercase tracking-[0.08em] text-muted">
        {t("compare.highlights_vs", { base: base.name })}
      </div>
      {others.map((s) => {
        const k = s.kpis!;
        const co2Pct =
          b.co2_total > 0
            ? ((k.co2_total - b.co2_total) / b.co2_total) * 100
            : 0;
        const autoPp = (k.modal_share.Auto - b.modal_share.Auto) * 100;
        return (
          <div
            key={s.id}
            style={{
              border: "1px solid var(--rule)",
              background: "var(--paper-2)",
              padding: "8px 12px",
            }}
          >
            <div className="mb-1 font-fig text-[12px] font-semibold text-ink">
              {s.name}
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 font-fig text-[11px] tabular-nums">
              <Chip
                label={t("compare.kpi.total") + " CO₂"}
                delta={co2Pct}
                unit="%"
                lowerIsBetter
              />
              <Chip
                label={`% ${t("modes.auto")}`}
                delta={autoPp}
                unit=" pp"
                lowerIsBetter
              />
              {STRATA.map((st) => (
                <Chip
                  key={st}
                  label={`${t("compare.kpi.travel_time")} · ${t(`strata.${STRATUM_KEY[st]}`)}`}
                  delta={
                    k.by_stratum[st].mean_time_min -
                    b.by_stratum[st].mean_time_min
                  }
                  unit=" min"
                  lowerIsBetter
                  decimals={1}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Chip({
  label,
  delta,
  unit,
  lowerIsBetter,
  decimals = 0,
}: {
  label: string;
  delta: number;
  unit: string;
  lowerIsBetter?: boolean;
  decimals?: number;
}) {
  const negligible = Math.abs(delta) < (decimals > 0 ? 0.05 : 0.5);
  const good = lowerIsBetter ? delta < 0 : delta > 0;
  const color = negligible
    ? "var(--muted)"
    : good
      ? "var(--mejora)"
      : "var(--empeora)";
  const arrow = negligible ? "→" : delta > 0 ? "↑" : "↓";
  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-muted">{label}</span>
      <span style={{ color, fontWeight: 600 }}>
        {arrow} {delta >= 0 ? "+" : ""}
        {delta.toFixed(decimals)}
        {unit}
      </span>
    </span>
  );
}
