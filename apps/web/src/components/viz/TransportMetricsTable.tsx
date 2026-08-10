import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import { downloadCsv } from "@/lib/csv";

/** Reparto modal de un modo: porcentaje y conteo de viajes. */
export interface ModalEntry {
  modo: string;
  label: string;
  pct: number;
  count: number;
  color: string;
}

export interface StratumMetric {
  key: string;
  label: string;
  color: string;
  nHogares: number;
  tiempoMin: number;
  utilidad: number;
  /** Reparto modal del estrato (pct por modo, mismo orden que `reparto`). */
  reparto: { modo: string; pct: number }[];
}

/** Todas las métricas de una corrida de Transporte, ya agregadas. */
export interface TransportMetricsData {
  viajesFisicos: number;
  reparto: ModalEntry[];
  tiempoSistemaMin: number;
  frecuenciaMetro: number;
  residuoMin: number | null;
  co2Total: number;
  co2Auto: number;
  co2Metro: number;
  iteraciones: number;
  totalIteraciones: number;
  converged: boolean;
  capacidadAuto: number;
  /** Carga de la red por modo (flujo o carga / capacidad ofrecida). El metro
   *  usa la frecuencia OPERATIVA (f_op·K), no frec_max: es la capacidad que
   *  realmente circula. >1 ⇒ el modo opera sobre su capacidad. */
  vcAuto: number | null;
  vcBici: number | null;
  vcMetro: number | null;
  tiempoPorModo: { modo: string; label: string; min: number; color: string }[];
  porEstrato: StratumMetric[];
}

interface Props {
  data: TransportMetricsData;
  className?: string;
}

const fig = (size: number, color = "var(--muted)"): React.CSSProperties => ({
  fontFamily: "var(--font-fig)",
  fontSize: size,
  letterSpacing: "0.04em",
  color,
});

const fmtInt = (v: number) => Math.round(v).toLocaleString("es-CL");
const fmtMin = (v: number) => `${v.toFixed(1)}`;
const fmtPct = (v: number) => `${v.toFixed(1)}%`;
const fmtRatio = (v: number | null) => (v == null ? "—" : `${v.toFixed(2)}×`);

/**
 * Tabla-resumen de todas las métricas del equilibrio de Transporte, ordenadas
 * por sistema · reparto modal · por estrato · por modo. Sirve de "ficha" de un
 * escenario y se exporta a CSV para comparar escenarios y estimar
 * beneficios/desbeneficios sociales aguas abajo.
 */
export function TransportMetricsTable({ data, className }: Props) {
  const { t } = useTranslation("simulator");

  const handleExport = () => {
    const rows: (string | number)[][] = [];
    const H = (s: string) => t(`metrics_table.${s}`);
    rows.push([
      H("csv_section"),
      H("csv_metric"),
      H("csv_category"),
      H("csv_value"),
      H("csv_unit"),
    ]);

    // Sistema
    const sys = "sistema";
    rows.push([sys, H("trips"), "", data.viajesFisicos, "viajes"]);
    rows.push([
      sys,
      H("sys_time"),
      "",
      data.tiempoSistemaMin.toFixed(2),
      "min",
    ]);
    rows.push([
      sys,
      H("frequency"),
      "",
      data.frecuenciaMetro.toFixed(2),
      "tph",
    ]);
    rows.push([
      sys,
      H("residual"),
      "",
      data.residuoMin == null ? "" : data.residuoMin.toFixed(3),
      "min",
    ]);
    rows.push([sys, H("co2_total"), "", data.co2Total.toFixed(2), "kg/h"]);
    rows.push([sys, H("co2"), "auto", data.co2Auto.toFixed(2), "kg/h"]);
    rows.push([sys, H("co2"), "metro", data.co2Metro.toFixed(2), "kg/h"]);
    rows.push([
      sys,
      H("cap_auto"),
      "",
      Math.round(data.capacidadAuto),
      "veh/h",
    ]);
    rows.push([
      sys,
      H("vc"),
      "auto",
      data.vcAuto == null ? "" : data.vcAuto.toFixed(3),
      "v/c",
    ]);
    rows.push([
      sys,
      H("vc"),
      "metro",
      data.vcMetro == null ? "" : data.vcMetro.toFixed(3),
      "v/c",
    ]);
    rows.push([
      sys,
      H("vc"),
      "bici",
      data.vcBici == null ? "" : data.vcBici.toFixed(3),
      "v/c",
    ]);
    rows.push([
      sys,
      H("convergence"),
      "",
      data.converged ? H("converged") : H("maxiter"),
      `${data.iteraciones}/${data.totalIteraciones}`,
    ]);

    // Reparto modal del sistema
    for (const m of data.reparto) {
      rows.push(["reparto_modal", m.label, "pct", m.pct.toFixed(2), "%"]);
      rows.push([
        "reparto_modal",
        m.label,
        "viajes",
        Math.round(m.count),
        "viajes",
      ]);
    }

    // Tiempo medio por modo
    for (const m of data.tiempoPorModo) {
      rows.push(["tiempo_por_modo", m.label, "", m.min.toFixed(2), "min"]);
    }

    // Por estrato
    for (const s of data.porEstrato) {
      rows.push([
        "por_estrato",
        H("st_hogares"),
        s.label,
        Math.round(s.nHogares),
        "hogares",
      ]);
      rows.push([
        "por_estrato",
        H("st_time"),
        s.label,
        s.tiempoMin.toFixed(2),
        "min",
      ]);
      rows.push([
        "por_estrato",
        H("st_utility"),
        s.label,
        s.utilidad.toFixed(3),
        "utiles",
      ]);
      for (const r of s.reparto) {
        rows.push([
          "por_estrato",
          `${H("st_share")} ${r.modo}`,
          s.label,
          r.pct.toFixed(2),
          "%",
        ]);
      }
    }

    downloadCsv("transporte-metricas.csv", rows);
  };

  const modos = data.reparto.map((m) => m.label);

  return (
    <div
      className={cn(className)}
      style={{ border: "1px solid var(--rule)", background: "var(--paper)" }}
    >
      {/* ---- Encabezado + export ---- */}
      <div
        style={{
          padding: "10px 14px",
          borderBottom: "1px solid var(--rule)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 10,
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
          {t("metrics_table.title")}
        </div>
        <button
          type="button"
          onClick={handleExport}
          className="export-btn"
          style={{
            ...fig(10, "var(--ink-2)"),
            border: "1px solid var(--rule)",
            padding: "4px 10px",
            background: "var(--paper-2)",
            cursor: "pointer",
          }}
        >
          {`↓ ${t("metrics_table.export_csv")}`}
        </button>
      </div>

      {/* La grilla de stats del sistema se eliminó entera: cada una de sus seis
          cifras vivía ya en otro panel. Viajes, frecuencia y CO₂ están en la
          tira de KPIs —la frecuencia además con el aviso de tope mordiendo, que
          acá no estaba—; residuo y convergencia, en el veredicto; y «tiempo
          medio» es exactamente el `tiempo_medio por viajero` de la tabla de
          agregados. Todas siguen en el CSV, que es un volcado y no una
          superficie de lectura. Queda lo que no se repite en ninguna parte. */}

      {/* ---- Carga de la red: los tres modos con oferta congestionable ----
           Agrupados aparte de los KPI de escenario porque miden otra cosa:
           responden a población, precios y capacidad, NO a la forma urbana (en
           una ciudad monocéntrica el tramo junto al CBD carga ~la mitad de los
           viajes sea cual sea el largo). Antes se mostraban solo auto y bici
           mezclados con el resto, sin el metro y sin esa aclaración. */}
      <SectionHead>{t("metrics_table.network_load")}</SectionHead>
      <div className="eqt-sys-grid">
        <Stat
          label={t("metrics_table.vc_auto")}
          value={fmtRatio(data.vcAuto)}
          sub={t("metrics_table.vc_sub")}
          warn={(data.vcAuto ?? 0) > 1}
        />
        <Stat
          label={t("metrics_table.vc_metro")}
          value={fmtRatio(data.vcMetro)}
          sub={t("metrics_table.vc_metro_sub")}
          warn={(data.vcMetro ?? 0) > 1}
        />
        <Stat
          label={t("metrics_table.vc_bici")}
          value={fmtRatio(data.vcBici)}
          sub={t("metrics_table.vc_sub")}
          warn={(data.vcBici ?? 0) > 1}
        />
      </div>
      <p style={{ ...fig(10), padding: "6px 14px 0", lineHeight: 1.5 }}>
        {t("metrics_table.network_load_note")}
      </p>

      {/* ---- Tiempo medio por modo ----
           Antes esta sección abría con share % y viajes por modo, que son
           exactamente los cinco KPI del encabezado de la página. Queda el
           tiempo medio, que no está en ninguna otra parte. */}
      <SectionHead>{t("metrics_table.time_section")}</SectionHead>
      <div style={{ overflowX: "auto" }}>
        <table style={tableStyle}>
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
                {t("metrics_table.mode_col")}
              </th>
              {data.reparto.map((m) => (
                <th
                  key={m.modo}
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
                        background: m.color,
                        display: "inline-block",
                      }}
                    />
                    {m.label}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderTop: "1px solid var(--rule)" }}>
              <td style={cellLabel}>{t("metrics_table.avg_time_mode")}</td>
              {data.reparto.map((m) => {
                const tm = data.tiempoPorModo.find((x) => x.modo === m.modo);
                return (
                  <td key={m.modo} style={cellVal}>
                    {tm ? `${fmtMin(tm.min)}` : "—"}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      {/* ---- Por estrato ---- */}
      <SectionHead>{t("metrics_table.per_stratum")}</SectionHead>
      <div style={{ overflowX: "auto" }}>
        <table style={tableStyle}>
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
                {t("metrics_table.metric_col")}
              </th>
              {data.porEstrato.map((s) => (
                <th
                  key={s.key}
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
                        background: s.color,
                        display: "inline-block",
                      }}
                    />
                    {s.label}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <StratRow
              label={t("metrics_table.st_hogares")}
              data={data.porEstrato}
              get={(s) => fmtInt(s.nHogares)}
            />
            <StratRow
              label={t("metrics_table.st_time")}
              data={data.porEstrato}
              get={(s) => `${fmtMin(s.tiempoMin)} min`}
            />
            <StratRow
              label={t("metrics_table.st_utility")}
              data={data.porEstrato}
              get={(s) => s.utilidad.toFixed(2)}
            />
            {modos.map((modoLabel, mi) => (
              <StratRow
                key={modoLabel}
                label={`${t("metrics_table.st_share")} ${modoLabel}`}
                data={data.porEstrato}
                get={(s) => fmtPct(s.reparto[mi]?.pct ?? 0)}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* ---- Caveat de utilidad ---- */}
      <div
        style={{
          padding: "10px 14px",
          borderTop: "1px solid var(--rule)",
          ...fig(10.5, "var(--muted)"),
          lineHeight: 1.5,
        }}
      >
        ⚠ {t("sandbox.utility_caveat")}
      </div>
    </div>
  );
}

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontVariantNumeric: "tabular-nums",
};
const cellLabel: React.CSSProperties = {
  ...fig(11, "var(--muted)"),
  padding: "7px 14px",
  textAlign: "left",
};
const cellVal: React.CSSProperties = {
  ...fig(12, "var(--ink)"),
  padding: "7px 14px",
  textAlign: "right",
  fontWeight: 500,
};

function SectionHead({ children }: { children: React.ReactNode }) {
  return (
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
        {children}
      </div>
    </div>
  );
}

function StratRow({
  label,
  data,
  get,
}: {
  label: string;
  data: StratumMetric[];
  get: (s: StratumMetric) => string;
}) {
  return (
    <tr style={{ borderTop: "1px solid var(--rule)" }}>
      <td style={cellLabel}>{label}</td>
      {data.map((s) => (
        <td key={s.key} style={cellVal}>
          {get(s)}
        </td>
      ))}
    </tr>
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
