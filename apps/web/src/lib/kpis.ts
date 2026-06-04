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
  distCbdKm: number
): number {
  switch (modo) {
    case "Auto":
      return snap.t_auto[celda] ?? 0;
    case "Metro":
      return (snap.t_tren_acceso[celda] ?? 0) + (snap.t_tren_espera[celda] ?? 0) + (snap.t_tren_viaje[celda] ?? 0);
    case "Bici":
      return snap.t_bici[celda] ?? 0;
    case "Caminata":
      return (distCbdKm / 4.8) * 60;
    case "Teletrabajo":
      return 0;
  }
}

export function computeKPIs(result: SimulationResult, largoKm: number, nCeldas: number): ScenarioKPIs {
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
    const t = lastIter ? modeTimeFor(m, a.celda_origen, lastIter, distKm) : 0;

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

  return {
    total_agentes: total,
    viajes_fisicos: viajesFisicos,
    modal_share,
    tiempo_medio_min,
    frecuencia_metro: lastIter?.frecuencia_metro ?? 0,
    residuo_final: lastIter?.residuo ?? null,
    co2_total: result.emisiones_total_kg ?? 0,
    co2_auto: result.emisiones_auto_kg ?? 0,
    co2_metro: result.emisiones_metro_kg ?? 0,
    by_stratum,
  };
}
