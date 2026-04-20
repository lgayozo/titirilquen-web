import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { ScenarioKPIs } from "@/lib/kpis";
import type { Modo } from "@/lib/types";

interface KPITableProps {
  scenarios: Array<{ id: string; name: string; kpis: ScenarioKPIs | null }>;
  baseId?: string;
}

const MODES: Modo[] = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"];

/**
 * Tabla KPI comparativa. La primera columna con datos es la base; las demás
 * muestran delta absoluto en porcentaje o minutos.
 */
export function KPITable({ scenarios, baseId }: KPITableProps) {
  const { t } = useTranslation("simulator");

  const base = scenarios.find((s) => s.id === baseId && s.kpis) ?? scenarios.find((s) => s.kpis);
  const withKpis = scenarios.filter((s) => s.kpis);
  if (withKpis.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full text-xs">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr className="border-b border-slate-200 dark:border-slate-800">
            <th className="px-3 py-2 text-left font-semibold">{t("compare.kpi.metric")}</th>
            {scenarios.map((s) => (
              <th key={s.id} className="px-3 py-2 text-right font-semibold">
                {s.name}{" "}
                {base?.id === s.id && (
                  <span className="text-slate-400">{t("compare.kpi.base")}</span>
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
              formatter={(v) => v.toLocaleString()}
              deltaFormatter={(d) => `${d >= 0 ? "+" : ""}${Math.round(d).toLocaleString()}`}
            />
          </Section>
        </tbody>
      </table>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <tr>
        <td
          colSpan={99}
          className="bg-slate-100/50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-900/50"
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

function KPIRow({ label, scenarios, valueOf, baseKpis, formatter, deltaFormatter, invertedSign }: KPIRowProps) {
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50/50 dark:border-slate-900 dark:hover:bg-slate-900/50">
      <td className="px-3 py-1.5 text-slate-600 dark:text-slate-300">{label}</td>
      {scenarios.map((s) => {
        if (!s.kpis) {
          return (
            <td key={s.id} className="px-3 py-1.5 text-right text-slate-300">
              —
            </td>
          );
        }
        const v = valueOf(s.kpis);
        const base = baseKpis ? valueOf(baseKpis) : null;
        const delta = base != null ? v - base : null;
        const isBase = baseKpis === s.kpis;
        return (
          <td key={s.id} className="px-3 py-1.5 text-right font-mono tabular-nums">
            <div>{formatter(v)}</div>
            {delta != null && !isBase && (
              <div
                className={cn(
                  "text-[10px]",
                  deltaColor(delta, invertedSign)
                )}
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
  if (Math.abs(delta) < 1e-3) return "text-slate-400";
  const good = positiveIsGood ? delta > 0 : delta < 0;
  return good
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400";
}
