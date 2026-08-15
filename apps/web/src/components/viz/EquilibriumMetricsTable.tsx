import { useTranslation } from "react-i18next";

import { ModalShareBars } from "@/components/viz/ModalShareBars";
import { cn } from "@/lib/cn";
import type { EquilibriumMetrics, StratumMetrics } from "@/lib/types-v2";

interface Props {
  /** Métricas del equilibrio final (última iteración exterior). */
  last: EquilibriumMetrics;
  /** Métricas de la iteración 0 (sin feedback), para mostrar Δ. Opcional. */
  first?: EquilibriumMetrics | null;
  className?: string;
}

const fig = (size: number, color = "var(--muted)"): React.CSSProperties => ({
  fontFamily: "var(--font-fig)",
  fontSize: size,
  letterSpacing: "0.04em",
  color,
});

const fmtMoney = (v: number) => `$${Math.round(v).toLocaleString("es-CL")}`;
const fmtInt = (v: number) => Math.round(v).toLocaleString("es-CL");
const fmtKm = (v: number) => `${v.toFixed(2)} km`;
const fmtMin = (v: number) => `${v.toFixed(1)} min`;
const fmtPct = (v: number) => `${(v * 100).toFixed(1)}%`;
const fmtRatio = (v: number | null) => (v == null ? "—" : `${v.toFixed(2)}×`);

/**
 * Reporte de métricas del equilibrio "Ciudad en equilibrio" — calculado en el
 * core (`coupled_metrics.py`) y adjuntado a cada OuterIteration. Muestra:
 *   - Una tabla **por estrato** (los distintos usuarios).
 *   - Un panel **del sistema** (el equilibrio agregado).
 *
 * Caveat de interpretación (replicado de la discusión λ/y): el Δ excedente del
 * consumidor (vs flujo libre — costo de bienestar de la congestión, ≤ 0) en $
 * es comparable como *eficiencia/DAP*, no como bienestar interpersonal. La
 * lectura distributiva va por la carga (costo/ingreso) y el tiempo.
 */
export function EquilibriumMetricsTable({ last, first, className }: Props) {
  const { t } = useTranslation("simulator");
  const E = last.por_estrato;
  const sys = last.sistema;
  const E0 = first?.por_estrato ?? null;

  const stratumLabels = [t("strata.alto"), t("strata.medio"), t("strata.bajo")];

  // Filas de la tabla por estrato: (label, accessor, formato).
  // `noDelta`: la métrica es un **input** del escenario (no cambia con el
  // feedback), así que no se muestra Δ vs. iter 0 — sería ruido. Hogares por
  // estrato es ~constante (se conserva = H_por_estrato, la población dada);
  // lo que el equilibrio mueve es *dónde* viven (distancia), no cuántos son.
  const rows: {
    key: string;
    label: string;
    get: (s: StratumMetrics) => number;
    fmt: (v: number) => string;
    noDelta?: boolean;
  }[] = [
    {
      key: "hogares",
      label: t("eqt.hogares"),
      get: (s) => s.n_hogares,
      fmt: fmtInt,
      noDelta: true,
    },
    {
      key: "dist",
      label: t("eqt.dist"),
      get: (s) => s.dist_media_cbd_km,
      fmt: fmtKm,
    },
    {
      key: "tiempo",
      label: t("eqt.tiempo"),
      get: (s) => s.tiempo_medio_min,
      fmt: fmtMin,
    },
    {
      key: "costo",
      label: t("eqt.costo"),
      get: (s) => s.costo_medio_clp,
      fmt: fmtMoney,
    },
    {
      key: "carga",
      label: t("eqt.carga"),
      get: (s) => s.carga_costo_ingreso,
      fmt: fmtPct,
    },
    {
      key: "cs",
      label: t("eqt.cs"),
      get: (s) => s.delta_excedente_clp,
      fmt: fmtMoney,
    },
  ];

  return (
    <div
      className={cn(className)}
      style={{ border: "1px solid var(--rule)", background: "var(--paper)" }}
    >
      {/* ---- Por estrato ---- */}
      <div
        style={{
          padding: "10px 14px 6px",
          borderBottom: "1px solid var(--rule)",
        }}
      >
        <div
          style={{
            ...fig(10, "var(--accent)"),
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
          }}
        >
          {t("eqt.per_stratum_header")}
        </div>
        {E0 && (
          <div style={{ ...fig(9.5, "var(--muted)"), marginTop: 3 }}>
            {t("eqt.delta_note")}
          </div>
        )}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  ...fig(10),
                  textAlign: "left",
                  padding: "8px 14px",
                  textTransform: "uppercase",
                }}
              >
                {t("eqt.metric_col")}
              </th>
              {stratumLabels.map((lbl, i) => (
                <th
                  key={i}
                  style={{
                    ...fig(11, "var(--ink)"),
                    textAlign: "right",
                    padding: "8px 14px",
                    fontWeight: 600,
                  }}
                >
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 5,
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        background: `var(--s${i + 1})`,
                        display: "inline-block",
                      }}
                    />
                    {lbl}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} style={{ borderTop: "1px solid var(--rule)" }}>
                <td
                  style={{
                    ...fig(11, "var(--muted)"),
                    padding: "7px 14px",
                    textAlign: "left",
                  }}
                >
                  {row.label}
                  {row.noDelta && (
                    <span
                      style={{
                        ...fig(8.5, "var(--accent)"),
                        marginLeft: 6,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      {t("eqt.input_badge")}
                    </span>
                  )}
                </td>
                {E.map((s, i) => {
                  const v = row.get(s);
                  const base = !row.noDelta && E0?.[i] ? row.get(E0[i]!) : null;
                  return (
                    <td
                      key={i}
                      style={{ padding: "7px 14px", textAlign: "right" }}
                    >
                      <div
                        style={{ ...fig(12, "var(--ink)"), fontWeight: 500 }}
                      >
                        {row.fmt(v)}
                      </div>
                      {base != null && (
                        <DeltaTag curr={v} base={base} fmt={row.fmt} />
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ---- Reparto modal (barras anchas, legibles) ---- */}
      <div
        style={{ padding: "10px 14px 6px", borderTop: "1px solid var(--rule)" }}
      >
        <div
          style={{
            ...fig(10, "var(--accent)"),
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
          }}
        >
          {t("eqt.modal")}
        </div>
      </div>
      <div style={{ padding: "4px 14px 12px" }}>
        <ModalShareBars
          rows={[
            ...E.map((s, i) => ({
              label: stratumLabels[i] ?? `E${i + 1}`,
              reparto: s.reparto_modal,
            })),
            { label: t("eqt.modal_system"), reparto: sys.reparto_modal },
          ]}
        />
      </div>

      {/* ---- Sistema ---- */}
      <div
        style={{
          padding: "10px 14px 6px",
          borderTop: "1px solid var(--rule)",
          borderBottom: "1px solid var(--rule)",
        }}
      >
        <div
          style={{
            ...fig(10, "var(--accent)"),
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
          }}
        >
          {t("eqt.system_header")}
        </div>
      </div>
      {/* Grilla fija 4×2 (8 stats): balanceada siempre — con auto-fill, en
          anchos intermedios quedaba una fila de 7 + 1 huérfano. */}
      <div className="eqt-sys-grid">
        <Stat
          label={t("eqt.convergence")}
          value={sys.convergio_exterior ? t("eqt.converged") : t("eqt.maxiter")}
          sub={t("eqt.conv_sub", {
            n: sys.iteraciones_exteriores,
            res:
              sys.residual_final_min == null
                ? "—"
                : sys.residual_final_min.toFixed(2),
          })}
          good={sys.convergio_exterior}
        />
        <Stat
          label={t("eqt.sys_time")}
          value={fmtMin(sys.tiempo_medio_min)}
          sub={t("eqt.sys_time_sub")}
        />
        <Stat
          label={t("eqt.freq")}
          value={`${sys.frecuencia_metro.toFixed(1)}`}
          sub={t("eqt.freq_sub")}
        />
        <Stat
          label={t("eqt.emissions")}
          value={`${fmtInt(sys.emisiones_total_kg)}`}
          sub={t("eqt.emissions_sub")}
        />
        <Stat
          label={t("eqt.theil")}
          value={sys.segregacion_theil.toFixed(3)}
          sub={t("eqt.theil_sub")}
        />
        <Stat
          label={t("eqt.welfare_total")}
          value={fmtMoney(sys.delta_bienestar_total_clp)}
          sub={t("eqt.welfare_total_sub")}
        />
        <Stat
          label={t("eqt.regress_time")}
          value={fmtRatio(sys.ratio_tiempo_bajo_alto)}
          sub={t("eqt.regress_time_sub")}
          warn={(sys.ratio_tiempo_bajo_alto ?? 0) > 1}
        />
        <Stat
          label={t("eqt.regress_burden")}
          value={fmtRatio(sys.ratio_carga_bajo_alto)}
          sub={t("eqt.regress_burden_sub")}
          warn={(sys.ratio_carga_bajo_alto ?? 0) > 1}
        />
      </div>

      {/* ---- Caveat ---- */}
      <div
        style={{
          padding: "10px 14px",
          borderTop: "1px solid var(--rule)",
          ...fig(10.5, "var(--muted)"),
          lineHeight: 1.5,
        }}
      >
        ⚠ {t("eqt.caveat")}
      </div>
    </div>
  );
}

function DeltaTag({
  curr,
  base,
  fmt,
}: {
  curr: number;
  base: number;
  fmt: (v: number) => string;
}) {
  const d = curr - base;
  if (Math.abs(d) < 1e-9) return <div style={fig(10, "var(--muted)")}>→</div>;
  const arrow = d > 0 ? "↑" : "↓";
  const signed = (d > 0 ? "+" : "") + fmt(d).replace("$", "$");
  return (
    <div style={fig(10, "var(--ink-2)")}>
      {arrow} {signed}
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  good,
  warn,
}: {
  label: string;
  value: string;
  sub?: string;
  good?: boolean;
  warn?: boolean;
}) {
  const valColor = good ? "var(--bici)" : warn ? "var(--accent)" : "var(--ink)";
  return (
    <div
      style={{
        padding: "12px 14px",
        borderRight: "1px solid var(--rule)",
        borderTop: "1px solid var(--rule)",
      }}
    >
      <div
        style={{
          ...fig(9.5),
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 19,
          fontWeight: 600,
          color: valColor,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1.2,
          marginTop: 3,
        }}
      >
        {value}
      </div>
      {sub && <div style={{ ...fig(9.5), marginTop: 2 }}>{sub}</div>}
    </div>
  );
}
