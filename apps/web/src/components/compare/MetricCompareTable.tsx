import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

export interface MetricRow {
  key: string;
  label: string;
  fmt: (v: number) => string;
  /** Formato del delta (default: fmt con signo). */
  fmtDelta?: (d: number) => string;
  /** Dirección "buena" del delta para colorear (verde/rojo); sin definir = neutro. */
  betterWhen?: "down" | "up";
}

export interface MetricCol {
  id: string;
  name: string;
  values: Record<string, number | null> | null;
}

interface MetricCompareTableProps {
  cols: MetricCol[];
  rows: MetricRow[];
  baseId?: string;
}

/**
 * Tabla comparativa genérica: una columna por escenario, la base muestra el
 * valor y las demás valor + delta vs base. La usan las comparaciones de suelo
 * y de ciudad en equilibrio (la de transporte tiene su KPITable específica).
 */
export function MetricCompareTable({
  cols,
  rows,
  baseId,
}: MetricCompareTableProps) {
  const { t } = useTranslation("simulator");

  const base =
    cols.find((c) => c.id === baseId && c.values) ?? cols.find((c) => c.values);
  if (!cols.some((c) => c.values)) return null;

  return (
    <div className="overflow-x-auto rounded-lg border border-[var(--rule)]">
      <table
        className="w-full text-xs"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        <thead className="bg-[var(--paper-2)]">
          <tr className="border-b border-[var(--rule)]">
            <th className="px-3 py-2 text-left font-semibold">
              {t("compare.kpi.metric")}
            </th>
            {cols.map((c) => (
              <th key={c.id} className="px-3 py-2 text-right font-semibold">
                {c.name}{" "}
                {base?.id === c.id && (
                  <span className="text-[var(--muted)]">
                    {t("compare.kpi.base")}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.key}
              className="border-b border-[var(--rule)] hover:bg-[var(--paper-2)]"
            >
              <td className="px-3 py-1.5 text-[var(--ink-2)]">{row.label}</td>
              {cols.map((c) => {
                const v = c.values?.[row.key];
                if (v == null) {
                  return (
                    <td
                      key={c.id}
                      className="px-3 py-1.5 text-right text-[var(--muted)]"
                    >
                      —
                    </td>
                  );
                }
                const baseV =
                  base && base.id !== c.id ? base.values?.[row.key] : null;
                const delta = baseV != null ? v - baseV : null;
                return (
                  <td key={c.id} className="px-3 py-1.5 text-right">
                    <span className="font-medium">{row.fmt(v)}</span>
                    {delta != null && Math.abs(delta) > 1e-9 && (
                      <span
                        className={cn(
                          "ml-1.5",
                          deltaColor(delta, row.betterWhen),
                        )}
                      >
                        {delta > 0 ? "+" : ""}
                        {(row.fmtDelta ?? row.fmt)(delta)}
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function deltaColor(delta: number, betterWhen?: "down" | "up"): string {
  if (!betterWhen) return "text-[var(--muted)]";
  const good = betterWhen === "down" ? delta < 0 : delta > 0;
  return good ? "text-[var(--bici)]" : "text-[var(--metro)]";
}
