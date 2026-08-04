/**
 * KPIs derivados de un `SimulationResult` para comparar escenarios.
 * Incluye desgloses por **modo** y por **tipo de usuario (estrato)**.
 */

import type { AgentRecord, Modo, SimulationResult, StratumId } from "@/lib/types";

export interface StratumKPIs {
  /** Agentes del estrato. */
  n: number;
  /** Tiempo de viaje medio (min), excluyendo teletrabajo. */
  mean_time_min: number;
  /** Utilidad media de los que viajan (excluye teletrabajo). */
  mean_utility: number;
  /** Reparto modal dentro del estrato (fracción sobre el total del estrato). */
  modal_share: Record<Modo, number>;
}

export interface ScenarioKPIs {
  total_agentes: number;
  viajes_fisicos: number;
  modal_share: Record<Modo, number>;
  tiempo_medio_min: Record<Modo, number>;
  frecuencia_metro: number;
  residuo_final: number | null;
  /** v/c del corredor en el equilibrio (flujo máx acumulado hacia el CBD /
   * capacidad direccional). null si el trace no trae flujos (wheel antiguo). */
  vc_auto: number | null;
  vc_bici: number | null;
  /** Metro: carga máx del tramo / capacidad operativa (f_op · capacidad_tren). */
  vc_metro: number | null;
  co2_total: number;
  co2_auto: number;
  co2_metro: number;
  by_stratum: Record<StratumId, StratumKPIs>;
}

const MODES: Modo[] = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"];
const STRATA: StratumId[] = [1, 2, 3];

function zeroModes(): Record<Modo, number> {
  return { Auto: 0, Metro: 0, Bici: 0, Caminata: 0, Teletrabajo: 0 };
}

function modeTimeFor(
  modo: Modo,
  celda: number,
  snap: SimulationResult["iteraciones"][number],
  distCbdKm: number,
  vCaminata: number
): number {
  switch (modo) {
    case "Auto":
      return snap.t_auto[celda] ?? 0;
    case "Metro":
      return (snap.t_tren_acceso[celda] ?? 0) + (snap.t_tren_espera[celda] ?? 0) + (snap.t_tren_viaje[celda] ?? 0);
    case "Bici":
      return snap.t_bici[celda] ?? 0;
    case "Caminata":
      return (distCbdKm / vCaminata) * 60;
    case "Teletrabajo":
      return 0;
  }
}

export function computeKPIs(
  result: SimulationResult,
  largoKm: number,
  nCeldas: number,
  // Velocidad de caminata DEL ESCENARIO (config.demand.globales.v_caminata):
  // antes estaba hardcodeada en 4.8 y los KPIs de Comparar la ignoraban.
  vCaminata = 4.8,
  // Capacidad de la ciclovía DEL ESCENARIO (config.supply.bike.capacidad_pista),
  // denominador del v/c bici; sin ella el ratio queda null.
  capacidadBici?: number,
  capacidadTren?: number,
): ScenarioKPIs {
  const lastIter = result.iteraciones.at(-1);
  const modal_share = zeroModes();
  const tiempo_medio_min = zeroModes();
  const counts = zeroModes();

  const cbdIdx = Math.floor(nCeldas / 2);
  const cellWidthKm = largoKm / nCeldas;

  // Acumuladores por estrato.
  const stratumAgg: Record<StratumId, { n: number; timeSum: number; utilSum: number; travelN: number; modes: Record<Modo, number> }> = {
    1: { n: 0, timeSum: 0, utilSum: 0, travelN: 0, modes: zeroModes() },
    2: { n: 0, timeSum: 0, utilSum: 0, travelN: 0, modes: zeroModes() },
    3: { n: 0, timeSum: 0, utilSum: 0, travelN: 0, modes: zeroModes() },
  };

  const agentes: readonly AgentRecord[] = result.agentes;
  for (const a of agentes) {
    const m = (a.modo_elegido ?? "Teletrabajo") as Modo;
    const distKm = Math.abs(a.celda_origen - cbdIdx) * cellWidthKm;
    const t = lastIter ? modeTimeFor(m, a.celda_origen, lastIter, distKm, vCaminata) : 0;

    modal_share[m] += 1;
    if (lastIter) {
      tiempo_medio_min[m] += t;
      counts[m] += 1;
    }

    const sg = stratumAgg[a.estrato as StratumId];
    if (sg) {
      sg.n += 1;
      sg.modes[m] += 1;
      if (m !== "Teletrabajo") {
        sg.timeSum += t;
        sg.utilSum += a.utilidad_elegida;
        sg.travelN += 1;
      }
    }
  }

  const total = agentes.length;
  const viajesFisicos = total - (modal_share.Teletrabajo ?? 0);
  for (const m of MODES) {
    const n = counts[m];
    tiempo_medio_min[m] = n > 0 ? tiempo_medio_min[m] / n : 0;
    modal_share[m] = total > 0 ? modal_share[m] / total : 0;
  }

  const by_stratum = STRATA.reduce<Record<StratumId, StratumKPIs>>((acc, s) => {
    const sg = stratumAgg[s];
    const share = zeroModes();
    for (const m of MODES) share[m] = sg.n > 0 ? sg.modes[m] / sg.n : 0;
    acc[s] = {
      n: sg.n,
      mean_time_min: sg.travelN > 0 ? sg.timeSum / sg.travelN : 0,
      mean_utility: sg.travelN > 0 ? sg.utilSum / sg.travelN : 0,
      modal_share: share,
    };
    return acc;
  }, {} as Record<StratumId, StratumKPIs>);

  // v/c del corredor: flujo acumulado hacia el CBD (no demanda originada).
  const vc_auto =
    result.flujos_auto_veh_h?.length && result.capacidad_auto > 0
      ? Math.max(...result.flujos_auto_veh_h) / result.capacidad_auto
      : null;
  const vc_bici =
    result.flujos_bici_veh_h?.length && capacidadBici && capacidadBici > 0
      ? Math.max(...result.flujos_bici_veh_h) / capacidadBici
      : null;
  const fOp = lastIter?.frecuencia_metro ?? 0;
  const vc_metro =
    result.carga_metro?.length && capacidadTren && fOp > 0
      ? Math.max(...result.carga_metro) / (fOp * capacidadTren)
      : null;

  return {
    total_agentes: total,
    viajes_fisicos: viajesFisicos,
    modal_share,
    tiempo_medio_min,
    frecuencia_metro: lastIter?.frecuencia_metro ?? 0,
    residuo_final: lastIter?.residuo ?? null,
    vc_auto,
    vc_bici,
    vc_metro,
    co2_total: result.emisiones_total_kg ?? 0,
    co2_auto: result.emisiones_auto_kg ?? 0,
    co2_metro: result.emisiones_metro_kg ?? 0,
    by_stratum,
  };
}
