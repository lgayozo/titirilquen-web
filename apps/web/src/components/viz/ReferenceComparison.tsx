import { useTranslation } from "react-i18next";

import { agregadosDe, logsumComparable, type Agregados } from "@/lib/agregados";
import { VOT_SOCIAL_CLP_HORA } from "@/lib/gen/constantes.gen";
import type {
  SimulationConfig,
  SimulationResult,
  StratumId,
} from "@/lib/types";

/**
 * Comparación contra la corrida FIJADA como referencia, dentro del propio
 * módulo de transporte: «corro un escenario, lo fijo, corro otro y veo el
 * delta» sin salir de la página.
 *
 * Muestra los AGREGADOS de ciudad completa —persona-minutos, tiempo medio,
 * costo generalizado y excedente— que son los únicos con los que se puede
 * afirmar que una política mejora al sistema. Los promedios por modo que ya
 * estaban en la tabla no sirven para eso: un modo puede mejorar mientras el
 * conjunto empeora.
 */

const STRATA: StratumId[] = [1, 2, 3];

interface Props {
  config: SimulationConfig;
  result: SimulationResult;
  reference: { config: SimulationConfig; result: SimulationResult } | null;
}

const fmtMin = (v: number) => `${v.toFixed(1)} min`;
// El signo va ANTES del símbolo: «−$3.331», no «$-3.331».
const fmtMoney = (v: number) =>
  `${v < 0 ? "−" : ""}$${Math.round(Math.abs(v)).toLocaleString("es-CL")}`;
const fmtMiles = (v: number) => `${Math.round(v).toLocaleString("es-CL")}`;

interface FilaAgg {
  label: string;
  actual: number;
  ref: number | null;
  fmt: (v: number) => string;
  /** true ⇒ bajar es mejor (tiempos y costos). Solo colorea, no juzga. */
  menorEsMejor: boolean;
  /** Si `false`, se muestra el valor pero NO el delta. */
  comparable?: boolean;
  nota?: string;
}

export function ReferenceComparison({ config, result, reference }: Props) {
  const { t } = useTranslation("simulator");
  // Los agregados los calcula el núcleo y vienen en el resultado; acá sólo se
  // leen y se restan contra la referencia que el usuario haya fijado.
  const agg = agregadosDe(result);
  const aggRef = reference ? agregadosDe(reference.result) : null;
  if (!agg) return null;

  // El logsum solo es comparable con el MISMO choice set: con distinto conjunto
  // de modos cambia de escala y su diferencia deja de ser un excedente.
  const lsOk = reference ? logsumComparable(config, reference.config) : true;

  // Cuál de las dos medidas de excedente corresponde al método de asignación lo
  // decide el NÚCLEO (`medida_bienestar`): logsum bajo logit, utilidad máxima
  // media bajo determinístico, donde no hay término aleatorio que promediar.
  // Acá sólo se elige el campo y el rótulo; la regla no se reimplementa.
  const usaMax = agg.medida_bienestar === "utilidad_maxima";
  const excedentePorEstrato = usaMax
    ? agg.excedente_max_por_estrato_clp
    : agg.excedente_por_estrato_clp;
  const excedenteRefPorEstrato = usaMax
    ? aggRef?.excedente_max_por_estrato_clp
    : aggRef?.excedente_por_estrato_clp;
  // Dos corridas con métodos distintos miden el excedente con reglas distintas,
  // así que su diferencia no es un delta de bienestar: es la brecha entre dos
  // definiciones. Se muestra el nivel, no el delta.
  const mismaMedida =
    !aggRef || aggRef.medida_bienestar === agg.medida_bienestar;
  const excedenteComparable = lsOk && mismaMedida;

  const filas: FilaAgg[] = [
    {
      label: t("agg.tiempo_total"),
      actual: agg.tiempo_total_min,
      ref: aggRef?.tiempo_total_min ?? null,
      fmt: fmtMiles,
      menorEsMejor: true,
    },
    {
      label: t("agg.tiempo_medio"),
      actual: agg.tiempo_medio_min,
      ref: aggRef?.tiempo_medio_min ?? null,
      fmt: fmtMin,
      menorEsMejor: true,
    },
    {
      label: t("agg.cg_percibido"),
      actual: agg.costo_generalizado_percibido_clp,
      ref: aggRef?.costo_generalizado_percibido_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.cg_percibido_nota"),
    },
    {
      label: t("agg.cg_social"),
      actual: agg.costo_generalizado_social_clp,
      ref: aggRef?.costo_generalizado_social_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.cg_social_nota", { vot: fmtMoney(VOT_SOCIAL_CLP_HORA) }),
    },
    {
      label: t("agg.recaudacion"),
      actual: agg.recaudacion_parking_clp + agg.recaudacion_tarifa_clp,
      ref:
        aggRef == null
          ? null
          : aggRef.recaudacion_parking_clp + aggRef.recaudacion_tarifa_clp,
      fmt: fmtMoney,
      menorEsMejor: false,
      nota: t("agg.recaudacion_nota"),
    },
    {
      label: t("agg.costo_operador"),
      actual: agg.costo_operador_clp,
      ref: aggRef?.costo_operador_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.costo_operador_nota", {
        km: Math.round(agg.tren_km_hora),
        f: config.supply.train.factor_dia_punta,
      }),
    },
    {
      label: t("agg.subsidio"),
      actual: agg.subsidio_metro_clp,
      ref: aggRef?.subsidio_metro_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.subsidio_nota"),
    },
    {
      label: t("agg.bienestar"),
      actual: agg.bienestar_social_clp,
      ref: aggRef?.bienestar_social_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      // Lleva dentro el excedente de la medida emparejada, así que hereda su
      // condición de comparabilidad.
      comparable: excedenteComparable,
      nota: t("agg.bienestar_nota"),
    },
    ...STRATA.map((h) => ({
      label: t(usaMax ? "agg.excedente_estrato_max" : "agg.excedente_estrato", {
        h: t(`strata.${estratoKey(h)}`),
      }),
      actual: excedentePorEstrato[String(h) as "1" | "2" | "3"],
      ref: excedenteRefPorEstrato?.[String(h) as "1" | "2" | "3"] ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: excedenteComparable,
    })),
  ];

  return (
    <div className="overflow-x-auto">
      <p className="mb-2 text-[11px] leading-snug text-[var(--muted)]">
        {reference ? t("agg.intro_con_ref") : t("agg.intro_sin_ref")}
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--rule)] text-[11px] uppercase tracking-wide text-[var(--muted)]">
            <th className="py-1 text-left font-normal">{t("agg.metrica")}</th>
            {reference && (
              <th className="py-1 text-right font-normal">
                {t("agg.referencia")}
              </th>
            )}
            <th className="py-1 text-right font-normal">{t("agg.actual")}</th>
            {reference && <th className="py-1 text-right font-normal">Δ</th>}
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => {
            const d = f.ref == null ? null : f.actual - f.ref;
            const mostrarDelta = d != null && f.comparable !== false;
            const bueno = d == null ? false : f.menorEsMejor ? d < 0 : d > 0;
            return (
              <tr key={f.label} className="border-t border-[var(--rule)]">
                <td className="py-1 pr-2">
                  {f.label}
                  {f.nota && (
                    <span className="ml-1 text-[10px] text-[var(--muted)]">
                      {f.nota}
                    </span>
                  )}
                </td>
                {reference && (
                  <td className="py-1 text-right tabular-nums text-[var(--muted)]">
                    {f.ref == null ? "—" : f.fmt(f.ref)}
                  </td>
                )}
                <td className="py-1 text-right tabular-nums">
                  {f.fmt(f.actual)}
                </td>
                {reference && (
                  <td
                    className="py-1 text-right tabular-nums"
                    style={{
                      color: !mostrarDelta
                        ? "var(--muted)"
                        : Math.abs(d!) < 1e-9
                          ? "var(--muted)"
                          : bueno
                            ? "var(--bici)"
                            : "var(--accent)",
                    }}
                  >
                    {!mostrarDelta
                      ? t("agg.no_comparable")
                      : `${d! > 0 ? "+" : ""}${f.fmt(d!)}`.replace("+−", "−")}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="mt-2 text-[10px] leading-snug text-[var(--muted)]">
        {t("agg.vot_hint", {
          alto: fmtMoney(agg.vot_por_estrato_clp_hora["1"]),
          medio: fmtMoney(agg.vot_por_estrato_clp_hora["2"]),
          bajo: fmtMoney(agg.vot_por_estrato_clp_hora["3"]),
        })}
      </p>
      {usaMax && (
        <p className="mt-1 text-[10px] leading-snug text-[var(--muted)]">
          {t("agg.medida_utilidad_maxima")}
        </p>
      )}
      {!lsOk && (
        <p className="mt-1 text-[10px] leading-snug text-[var(--accent)]">
          {t("agg.logsum_incomparable")}
        </p>
      )}
      {!mismaMedida && (
        <p className="mt-1 text-[10px] leading-snug text-[var(--accent)]">
          {t("agg.medida_incomparable")}
        </p>
      )}
    </div>
  );
}

function estratoKey(h: StratumId): string {
  return h === 1 ? "alto" : h === 2 ? "medio" : "bajo";
}

export type { Agregados };
