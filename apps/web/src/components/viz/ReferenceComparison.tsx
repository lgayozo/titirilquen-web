import { useTranslation } from "react-i18next";

import {
  calcularAgregados,
  logsumComparable,
  VOT_SOCIAL_CLP_HORA,
  type Agregados,
} from "@/lib/agregados";
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
  const votSocial = VOT_SOCIAL_CLP_HORA;
  const agg = calcularAgregados(result, config, votSocial);
  const aggRef = reference
    ? calcularAgregados(reference.result, reference.config, votSocial)
    : null;
  if (!agg) return null;

  // El logsum solo es comparable con el MISMO choice set: con distinto conjunto
  // de modos cambia de escala y su diferencia deja de ser un excedente.
  const lsOk = reference ? logsumComparable(config, reference.config) : true;

  const filas: FilaAgg[] = [
    {
      label: t("agg.tiempo_total"),
      actual: agg.tiempoTotalMin,
      ref: aggRef?.tiempoTotalMin ?? null,
      fmt: fmtMiles,
      menorEsMejor: true,
    },
    {
      label: t("agg.tiempo_medio"),
      actual: agg.tiempoMedioMin,
      ref: aggRef?.tiempoMedioMin ?? null,
      fmt: fmtMin,
      menorEsMejor: true,
    },
    {
      label: t("agg.cg_percibido"),
      actual: agg.costoGeneralizadoPercibidoClp,
      ref: aggRef?.costoGeneralizadoPercibidoClp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.cg_percibido_nota"),
    },
    {
      label: t("agg.cg_social"),
      actual: agg.costoGeneralizadoSocialClp,
      ref: aggRef?.costoGeneralizadoSocialClp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.cg_social_nota", { vot: fmtMoney(votSocial) }),
    },
    {
      label: t("agg.recaudacion"),
      actual: agg.recaudacionParkingClp + agg.recaudacionTarifaClp,
      ref:
        aggRef == null
          ? null
          : aggRef.recaudacionParkingClp + aggRef.recaudacionTarifaClp,
      fmt: fmtMoney,
      menorEsMejor: false,
      nota: t("agg.recaudacion_nota"),
    },
    {
      label: t("agg.bienestar"),
      actual: agg.bienestarSocialClp,
      ref: aggRef?.bienestarSocialClp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: lsOk,
      nota: t("agg.bienestar_nota"),
    },
    ...STRATA.map((h) => ({
      label: t("agg.excedente_estrato", { h: t(`strata.${estratoKey(h)}`) }),
      actual: agg.excedentePorEstratoClp[h],
      ref: aggRef?.excedentePorEstratoClp[h] ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: lsOk,
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
          alto: fmtMoney(agg.votPorEstratoClpHora[1]),
          medio: fmtMoney(agg.votPorEstratoClpHora[2]),
          bajo: fmtMoney(agg.votPorEstratoClpHora[3]),
        })}
      </p>
      {!lsOk && (
        <p className="mt-1 text-[10px] leading-snug text-[var(--accent)]">
          {t("agg.logsum_incomparable")}
        </p>
      )}
    </div>
  );
}

function estratoKey(h: StratumId): string {
  return h === 1 ? "alto" : h === 2 ? "medio" : "bajo";
}

export type { Agregados };
