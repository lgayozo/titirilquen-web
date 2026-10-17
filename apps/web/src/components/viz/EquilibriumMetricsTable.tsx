import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PorQue } from "@/components/ui/PorQue";
import { ModalShareBars } from "@/components/viz/ModalShareBars";
import { cn } from "@/lib/cn";
import { fmtDecimal, fmtEntero, fmtPct, fmtPesos } from "@/lib/modos";
import type { EquilibriumMetrics, StratumMetrics } from "@/lib/types-v2";

interface Props {
  /** Métricas del equilibrio final (última iteración exterior). */
  last: EquilibriumMetrics;
  /** Métricas de la iteración 0 (sin feedback), para mostrar Δ. Opcional. */
  first?: EquilibriumMetrics | null;
  className?: string;
}

// Toda etiqueta va al paso `etiqueta` de la escala (B2), en la sans del
// cuerpo: la mono queda para códigos de figura, como en TransportMetricsTable.
const fig = (color = "var(--muted)"): React.CSSProperties => ({
  fontFamily: "var(--font-body)",
  fontSize: "var(--fs-etiqueta)",
  color,
});

const fmtKm = (v: number) => `${fmtDecimal(v, 2)} km`;
const fmtMin = (v: number) => `${fmtDecimal(v)} min`;
/** Fracción 0–1 → porcentaje. */
const fmtFrac = (v: number) => fmtPct(v * 100);
const fmtRatio = (v: number | null) =>
  v == null ? "—" : `${fmtDecimal(v, 2)}×`;

/**
 * Reporte de métricas del equilibrio "Ciudad en equilibrio" — calculado en el
 * core (`coupled_metrics.py`) y adjuntado a cada OuterIteration. Muestra:
 *   - Un panel **del sistema** (el equilibrio agregado), con su reparto.
 *   - Una tabla **por estrato** (los distintos usuarios), plegada (B4): a la
 *     vista sólo la distancia al CBD, que es el resultado de esta lente —quién
 *     vive dónde—; el resto y el reparto por estrato, tras «Ver por estrato».
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
  const [verEstratos, setVerEstratos] = useState(false);

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
      fmt: fmtEntero,
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
      fmt: fmtPesos,
    },
    {
      key: "carga",
      label: t("eqt.carga"),
      get: (s) => s.carga_costo_ingreso,
      fmt: fmtFrac,
    },
    {
      key: "cs",
      // Qué mide el Δ depende del método de asignación, y lo decide el núcleo
      // (`sistema.medida_bienestar`): logsum bajo logit, utilidad máxima media
      // bajo determinístico. Acá sólo se elige el rótulo.
      label: t(
        sys.medida_bienestar === "utilidad_maxima" ? "eqt.cs_max" : "eqt.cs",
      ),
      get: (s) => s.delta_excedente_hogar_mes_clp,
      fmt: fmtPesos,
    },
  ];

  return (
    <div
      className={cn(className)}
      style={{ border: "1px solid var(--rule)", background: "var(--panel)" }}
    >
      {/* ---- Sistema ---- */}
      <div
        style={{
          padding: "10px 14px 6px",
          borderBottom: "1px solid var(--rule)",
        }}
      >
        <div
          style={{
            ...fig("var(--accent)"),
            fontWeight: 600,
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
          // El acoplado para cuando la brecha exterior cumple aunque el MSA de
          // esa vuelta no haya convergido (coupled.py): ahí «Máx. iter.» era
          // falso, porque el loop exterior no agotó sus vueltas.
          value={
            sys.convergio_exterior
              ? t("eqt.converged")
              : sys.convergio_msa
                ? t("eqt.maxiter")
                : t("eqt.msa_not_converged")
          }
          sub={t("eqt.conv_sub", {
            n: sys.iteraciones_exteriores,
            res:
              sys.residual_final == null ? "—" : fmtDecimal(sys.residual_final),
          })}
          good={sys.convergio_exterior}
          warn={!sys.convergio_exterior}
        />
        <Stat
          label={t("eqt.sys_time")}
          value={fmtMin(sys.tiempo_medio_min)}
          sub={t("eqt.sys_time_sub")}
        />
        <Stat
          label={t("eqt.freq")}
          value={fmtDecimal(sys.frecuencia_metro)}
          sub={t("eqt.freq_sub")}
        />
        <Stat
          label={t("eqt.emissions")}
          value={fmtEntero(sys.emisiones_total_kg)}
          sub={t("eqt.emissions_sub")}
        />
        <Stat
          label={t("eqt.theil")}
          value={fmtDecimal(sys.segregacion_theil, 3)}
          sub={t("eqt.theil_sub")}
        />
        <Stat
          label={t("eqt.welfare_total")}
          value={fmtPesos(sys.delta_bienestar_total_mes_clp)}
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

      {/* ---- Reparto modal (barras anchas, legibles) ---- */}
      <div
        style={{ padding: "10px 14px 6px", borderTop: "1px solid var(--rule)" }}
      >
        <div
          style={{
            ...fig("var(--accent)"),
            fontWeight: 600,
          }}
        >
          {t("eqt.modal")}
        </div>
      </div>
      <div style={{ padding: "4px 14px 12px" }}>
        <ModalShareBars
          rows={[{ label: t("eqt.modal_system"), reparto: sys.reparto_modal }]}
        />
      </div>

      {/* ---- Por estrato ---- */}
      <div
        style={{
          padding: "10px 14px 6px",
          borderTop: "1px solid var(--rule)",
          borderBottom: "1px solid var(--rule)",
        }}
      >
        <div
          style={{
            ...fig("var(--accent)"),
            fontWeight: 600,
          }}
        >
          {t("eqt.per_stratum_header")}
        </div>
        {E0 && (
          <div style={{ ...fig("var(--muted)"), marginTop: 3 }}>
            {t("eqt.delta_note")}
            {verEstratos && ` ${t("eqt.input_note")}`}
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
                  ...fig(),
                  textAlign: "left",
                  padding: "8px 14px",
                }}
              >
                {t("eqt.metric_col")}
              </th>
              {stratumLabels.map((lbl, i) => (
                <th
                  key={i}
                  style={{
                    ...fig("var(--ink)"),
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
            {rows
              .filter((row) => verEstratos || row.key === "dist")
              .map((row) => (
                <tr
                  key={row.key}
                  style={{ borderTop: "1px solid var(--rule)" }}
                >
                  <td
                    style={{
                      ...fig("var(--muted)"),
                      padding: "7px 14px",
                      textAlign: "left",
                    }}
                  >
                    {row.label}
                    {row.noDelta && (
                      <span
                        style={{
                          ...fig("var(--accent)"),
                          marginLeft: 6,
                        }}
                      >
                        {t("eqt.input_badge")}
                      </span>
                    )}
                  </td>
                  {E.map((s, i) => {
                    const v = row.get(s);
                    const base =
                      !row.noDelta && E0?.[i] ? row.get(E0[i]!) : null;
                    return (
                      <td
                        key={i}
                        style={{ padding: "7px 14px", textAlign: "right" }}
                      >
                        <div style={{ ...fig("var(--ink)"), fontWeight: 500 }}>
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

      {verEstratos && (
        <div style={{ padding: "4px 14px 12px" }}>
          <ModalShareBars
            rows={E.map((s, i) => ({
              label: stratumLabels[i] ?? `E${i + 1}`,
              reparto: s.reparto_modal,
            }))}
          />
        </div>
      )}
      <div style={{ padding: "4px 14px 10px" }}>
        <button
          type="button"
          className="btn"
          aria-expanded={verEstratos}
          onClick={() => setVerEstratos((v) => !v)}
        >
          {verEstratos ? t("eqt.ocultar_estratos") : t("eqt.ver_estratos")}
        </button>
      </div>

      {/* ---- Caveat ---- */}
      <div
        style={{
          padding: "10px 14px",
          borderTop: "1px solid var(--rule)",
          ...fig("var(--muted)"),
          lineHeight: 1.5,
        }}
      >
        ⚠ {t("eqt.caveat_corto")}
        <PorQue>{t("eqt.caveat_porque")}</PorQue>
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
  if (Math.abs(d) < 1e-9) return <div style={fig("var(--muted)")}>→</div>;
  const arrow = d > 0 ? "↑" : "↓";
  const signed = (d > 0 ? "+" : "") + fmt(d).replace("$", "$");
  return (
    <div style={fig("var(--ink-2)")}>
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
  const valColor = good
    ? "var(--mejora)"
    : warn
      ? "var(--alerta)"
      : "var(--ink)";
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
          ...fig(),
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "var(--fs-dato)",
          fontWeight: 600,
          color: valColor,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1.2,
          marginTop: 3,
        }}
      >
        {value}
      </div>
      {sub && <div style={{ ...fig(), marginTop: 2 }}>{sub}</div>}
    </div>
  );
}
