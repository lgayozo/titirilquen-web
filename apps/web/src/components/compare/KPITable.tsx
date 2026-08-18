import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { ScenarioKPIs } from "@/lib/kpis";
import type { Modo, StratumId } from "@/lib/types";

interface KPITableProps {
  scenarios: Array<{ id: string; name: string; kpis: ScenarioKPIs | null }>;
  baseId?: string;
}

const MODES: Modo[] = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"];
const STRATA: StratumId[] = [1, 2, 3];
const STRATUM_KEY: Record<StratumId, string> = {
  1: "alto",
  2: "medio",
  3: "bajo",
};
const TRAVEL_MODES: Modo[] = ["Auto", "Metro", "Bici", "Caminata"];

/**
 * Tabla KPI comparativa. La primera columna con datos es la base; las demás
 * muestran delta absoluto en porcentaje o minutos.
 */
export function KPITable({ scenarios, baseId }: KPITableProps) {
  const { t } = useTranslation("simulator");

  const base =
    scenarios.find((s) => s.id === baseId && s.kpis) ??
    scenarios.find((s) => s.kpis);
  const withKpis = scenarios.filter((s) => s.kpis);
  if (withKpis.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded-lg border border-[var(--rule)]">
      <table className="w-full text-xs">
        <thead className="bg-[var(--paper-2)]">
          <tr className="border-b border-[var(--rule)]">
            <th className="px-3 py-2 text-left font-semibold">
              {t("compare.kpi.metric")}
            </th>
            {scenarios.map((s) => (
              <th key={s.id} className="px-3 py-2 text-right font-semibold">
                {s.name}{" "}
                {base?.id === s.id && (
                  <span className="text-[var(--muted)]">
                    {t("compare.kpi.base")}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <Section label={t("compare.kpi.modal_share")}>
            {MODES.map((m) => (
              <KPIRow
                key={m}
                label={t(`modes.${m.toLowerCase()}`)}
                scenarios={scenarios}
                valueOf={(kpi) => kpi.modal_share[m] * 100}
                baseKpis={base?.kpis ?? null}
                formatter={(v) => `${v.toFixed(1)}%`}
                deltaFormatter={(d) => `${d >= 0 ? "+" : ""}${d.toFixed(1)} pp`}
              />
            ))}
          </Section>

          <Section label={t("compare.kpi.mean_time")}>
            {MODES.slice(0, 4).map((m) => (
              <KPIRow
                key={m}
                label={t(`modes.${m.toLowerCase()}`)}
                scenarios={scenarios}
                valueOf={(kpi) => kpi.tiempo_medio_min[m]}
                baseKpis={base?.kpis ?? null}
                formatter={(v) => (v > 0 ? `${v.toFixed(1)}` : "—")}
                deltaFormatter={(d) => `${d >= 0 ? "+" : ""}${d.toFixed(1)}`}
                invertedSign
              />
            ))}
          </Section>

          <Section label={t("compare.kpi.operation")}>
            <KPIRow
              label={t("compare.kpi.metro_freq")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.frecuencia_metro}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => v.toFixed(1)}
              deltaFormatter={(d) => `${d >= 0 ? "+" : ""}${d.toFixed(1)}`}
            />
            <KPIRow
              label={t("compare.kpi.final_residual")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.residuo_final ?? 0}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => v.toFixed(3)}
              deltaFormatter={(d) => `${d >= 0 ? "+" : ""}${d.toFixed(3)}`}
              invertedSign
            />
            <KPIRow
              label={t("compare.kpi.physical_trips")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.viajes_fisicos}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => v.toLocaleString("es-CL")}
              deltaFormatter={(d) =>
                `${d >= 0 ? "+" : ""}${Math.round(d).toLocaleString("es-CL")}`
              }
            />
          </Section>

          {/* v/c del corredor (flujo máx acumulado/capacidad) — recién posible
              desde que el trace expone los flujos (S-01). NaN ⇒ "—" (wheel
              antiguo o resultado importado sin flujos). */}
          <Section label={t("compare.kpi.congestion")}>
            <KPIRow
              label={t("metrics_table.vc_auto")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.vc_auto ?? NaN}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => (Number.isFinite(v) ? `${v.toFixed(2)}×` : "—")}
              deltaFormatter={(d) =>
                Number.isFinite(d) ? `${d >= 0 ? "+" : ""}${d.toFixed(2)}` : ""
              }
              invertedSign
            />
            <KPIRow
              label={t("metrics_table.vc_metro")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.vc_metro ?? NaN}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => (Number.isFinite(v) ? `${v.toFixed(2)}×` : "—")}
              deltaFormatter={(d) =>
                Number.isFinite(d) ? `${d >= 0 ? "+" : ""}${d.toFixed(2)}` : ""
              }
              invertedSign
            />
            <KPIRow
              label={t("metrics_table.vc_bici")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.vc_bici ?? NaN}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => (Number.isFinite(v) ? `${v.toFixed(2)}×` : "—")}
              deltaFormatter={(d) =>
                Number.isFinite(d) ? `${d >= 0 ? "+" : ""}${d.toFixed(2)}` : ""
              }
              invertedSign
            />
          </Section>

          <Section label={t("compare.kpi.emissions")}>
            <KPIRow
              label={t("compare.kpi.total")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.co2_total}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => Math.round(v).toLocaleString("es-CL")}
              deltaFormatter={(d) =>
                `${d >= 0 ? "+" : ""}${Math.round(d).toLocaleString("es-CL")}`
              }
              invertedSign
            />
            <KPIRow
              label={t("modes.auto")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.co2_auto}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => Math.round(v).toLocaleString("es-CL")}
              deltaFormatter={(d) =>
                `${d >= 0 ? "+" : ""}${Math.round(d).toLocaleString("es-CL")}`
              }
              invertedSign
            />
            <KPIRow
              label={t("modes.metro")}
              scenarios={scenarios}
              valueOf={(kpi) => kpi.co2_metro}
              baseKpis={base?.kpis ?? null}
              formatter={(v) => Math.round(v).toLocaleString("es-CL")}
              deltaFormatter={(d) =>
                `${d >= 0 ? "+" : ""}${Math.round(d).toLocaleString("es-CL")}`
              }
              invertedSign
            />
          </Section>

          {STRATA.map((s) => (
            <Section
              key={s}
              label={`${t("compare.kpi.stratum")} · ${t(`strata.${STRATUM_KEY[s]}`)}`}
            >
              <KPIRow
                label={t("compare.kpi.travel_time")}
                scenarios={scenarios}
                valueOf={(kpi) => kpi.by_stratum[s].mean_time_min}
                baseKpis={base?.kpis ?? null}
                formatter={(v) => (v > 0 ? v.toFixed(1) : "—")}
                deltaFormatter={(d) => `${d >= 0 ? "+" : ""}${d.toFixed(1)}`}
                invertedSign
              />
              <KPIRow
                label={t("compare.kpi.utility")}
                scenarios={scenarios}
                valueOf={(kpi) => kpi.by_stratum[s].mean_utility}
                baseKpis={base?.kpis ?? null}
                formatter={(v) => v.toFixed(2)}
                deltaFormatter={(d) => `${d >= 0 ? "+" : ""}${d.toFixed(2)}`}
              />
              {TRAVEL_MODES.map((m) => (
                <KPIRow
                  key={m}
                  label={`% ${t(`modes.${m.toLowerCase()}`)}`}
                  scenarios={scenarios}
                  valueOf={(kpi) => kpi.by_stratum[s].modal_share[m] * 100}
                  baseKpis={base?.kpis ?? null}
                  formatter={(v) => `${v.toFixed(1)}%`}
                  deltaFormatter={(d) =>
                    `${d >= 0 ? "+" : ""}${d.toFixed(1)} pp`
                  }
                />
              ))}
            </Section>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <tr>
        <td
          colSpan={99}
          className="bg-[var(--paper-2)] px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]"
        >
          {label}
        </td>
      </tr>
      {children}
    </>
  );
}

interface KPIRowProps {
  label: string;
  scenarios: KPITableProps["scenarios"];
  valueOf: (kpi: ScenarioKPIs) => number;
  baseKpis: ScenarioKPIs | null;
  formatter: (v: number) => string;
  deltaFormatter: (d: number) => string;
  /** si true, delta negativo es "bueno" (verde) — ej. tiempos. */
  invertedSign?: boolean;
}

function KPIRow({
  label,
  scenarios,
  valueOf,
  baseKpis,
  formatter,
  deltaFormatter,
  invertedSign,
}: KPIRowProps) {
  return (
    <tr className="border-b border-[var(--rule)] hover:bg-[var(--paper-2)]">
      <td className="px-3 py-1.5 text-[var(--ink-2)]">{label}</td>
      {scenarios.map((s) => {
        if (!s.kpis) {
          return (
            <td
              key={s.id}
              className="px-3 py-1.5 text-right text-[var(--muted)]"
            >
              —
            </td>
          );
        }
        const v = valueOf(s.kpis);
        const base = baseKpis ? valueOf(baseKpis) : null;
        const delta = base != null ? v - base : null;
        const isBase = baseKpis === s.kpis;
        return (
          <td
            key={s.id}
            className="px-3 py-1.5 text-right font-mono tabular-nums"
          >
            <div>{formatter(v)}</div>
            {delta != null && !isBase && (
              <div
                className={cn("text-[10px]", deltaColor(delta, invertedSign))}
              >
                {deltaFormatter(delta)}
              </div>
            )}
          </td>
        );
      })}
    </tr>
  );
}

function deltaColor(delta: number, inverted?: boolean): string {
  const positiveIsGood = !inverted;
  if (Math.abs(delta) < 1e-3) return "text-[var(--muted)]";
  const good = positiveIsGood ? delta > 0 : delta < 0;
  return good ? "text-[var(--mejora)]" : "text-[var(--empeora)]";
}
