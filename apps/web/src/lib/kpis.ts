/**
 * KPIs derivados de un `SimulationResult` para comparar escenarios.
 */

import type { AgentRecord, Modo, SimulationResult } from "@/lib/types";

export interface ScenarioKPIs {
  total_agentes: number;
  viajes_fisicos: number;
  modal_share: Record<Modo, number>;
  tiempo_medio_min: Record<Modo, number>;
  frecuencia_metro: number;
  residuo_final: number | null;
}

const MODES: Modo[] = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"];

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
  const modal_share = MODES.reduce<Record<Modo, number>>((acc, m) => {
    acc[m] = 0;
    return acc;
  }, {} as Record<Modo, number>);
  const tiempo_medio_min = { ...modal_share };
  const counts = { ...modal_share };

  const cbdIdx = Math.floor(nCeldas / 2);
  const cellWidthKm = largoKm / nCeldas;

  const agentes: readonly AgentRecord[] = result.agentes;
  for (const a of agentes) {
    const m = (a.modo_elegido ?? "Teletrabajo") as Modo;
    modal_share[m] += 1;
    if (lastIter) {
      const distKm = Math.abs(a.celda_origen - cbdIdx) * cellWidthKm;
      const t = modeTimeFor(m, a.celda_origen, lastIter, distKm);
      tiempo_medio_min[m] += t;
      counts[m] += 1;
    }
  }

  const total = agentes.length;
  const viajesFisicos = total - (modal_share.Teletrabajo ?? 0);
  for (const m of MODES) {
    const n = counts[m];
    tiempo_medio_min[m] = n > 0 ? tiempo_medio_min[m] / n : 0;
    modal_share[m] = total > 0 ? modal_share[m] / total : 0;
  }

  return {
    total_agentes: total,
    viajes_fisicos: viajesFisicos,
    modal_share,
    tiempo_medio_min,
    frecuencia_metro: lastIter?.frecuencia_metro ?? 0,
    residuo_final: lastIter?.residuo ?? null,
  };
}
