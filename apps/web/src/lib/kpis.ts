/**
 * KPIs de un `SimulationResult` para comparar escenarios, por **modo** y por
 * **tipo de usuario (estrato)**.
 *
 * Es un adaptador: el reparto y los tiempos los calcula el núcleo sobre la
 * demanda ESPERADA (`agregados`, `bienestar.py`). Hasta oct-2026 se contaban
 * acá sobre el `modo_elegido` sorteado de cada agente, que con carga esperada
 * sólo agrega ruido de muestreo (~0,2 pp, auditoría C, ítem 9). De los agentes
 * quedan dos conteos exactos: los hogares y quienes teletrabajan.
 */

import { agregadosDe } from "@/lib/agregados";
import type { ModoTransporte, SimulationResult, StratumId } from "@/lib/types";

export interface StratumKPIs {
  /** Hogares del estrato. */
  n: number;
  /** Tiempo de viaje medio (min) de los que viajan. */
  mean_time_min: number;
  /** Reparto modal del estrato, sobre sus viajes físicos. */
  modal_share: Record<ModoTransporte, number>;
}

export interface ScenarioKPIs {
  viajes_fisicos: number;
  /** Reparto modal sobre los viajes FÍSICOS (auditoría C, ítem 10). */
  modal_share: Record<ModoTransporte, number>;
  /** Fracción de los hogares que teletrabaja: no es un modo del reparto. */
  tele_share_hogares: number;
  tiempo_medio_min: Record<ModoTransporte, number>;
  frecuencia_metro: number;
  residuo_final: number | null;
  /** v/c del corredor en el equilibrio (flujo máx acumulado hacia el CBD /
   * capacidad direccional). null si el trace no trae flujos (wheel antiguo). */
  vc_auto: number | null;
  vc_bici: number | null;
  /** Metro: carga máx del tramo / capacidad MÁXIMA (frec_max · capacidad_tren),
   *  la misma cifra que Transporte. Contra la operativa (f_op · K) valía 1 por
   *  construcción, porque el modelo fija f_op = carga/K. */
  vc_metro: number | null;
  co2_total: number;
  co2_auto: number;
  co2_metro: number;
  by_stratum: Record<StratumId, StratumKPIs>;
}

const MODOS: ModoTransporte[] = ["Auto", "Metro", "Bici", "Caminata"];
const STRATA: StratumId[] = [1, 2, 3];

/** Divide cada modo por la suma de los cuatro (0 si no viaja nadie). */
function shares(
  viajes: Record<string, number> | undefined,
): Record<ModoTransporte, number> {
  const total = MODOS.reduce((s, m) => s + (viajes?.[m] ?? 0), 0);
  return Object.fromEntries(
    MODOS.map((m) => [m, total > 0 ? (viajes?.[m] ?? 0) / total : 0]),
  ) as Record<ModoTransporte, number>;
}

/** `null` si el resultado no trae los agregados que hacen falta (un wheel
 *  anterior a la auditoría C): la columna se muestra con «—». */
export function computeKPIs(
  result: SimulationResult,
  // Capacidad de la ciclovía DEL ESCENARIO (config.supply.bike.capacidad_pista),
  // denominador del v/c bici; sin ella el ratio queda null.
  capacidadBici?: number,
  capacidadTren?: number,
  frecMax?: number,
): ScenarioKPIs | null {
  const agg = agregadosDe(result);
  if (!agg?.tiempo_medio_por_modo_min || !agg.tiempo_medio_por_estrato_min)
    return null;
  const lastIter = result.iteraciones.at(-1);

  const hogares: Record<StratumId, number> = { 1: 0, 2: 0, 3: 0 };
  let tele = 0;
  for (const a of result.agentes) {
    hogares[a.estrato as StratumId] += 1;
    if (a.modo_elegido === "Teletrabajo") tele += 1;
  }

  const by_stratum = STRATA.reduce<Record<StratumId, StratumKPIs>>(
    (acc, s) => {
      const h = String(s) as "1" | "2" | "3";
      acc[s] = {
        n: hogares[s],
        mean_time_min: agg.tiempo_medio_por_estrato_min[h] ?? 0,
        modal_share: shares(agg.viajes_por_modo_estrato[h]),
      };
      return acc;
    },
    {} as Record<StratumId, StratumKPIs>,
  );

  // v/c del corredor: flujo acumulado hacia el CBD (no demanda originada).
  const vc_auto =
    result.flujos_auto_veh_h?.length && result.capacidad_auto > 0
      ? Math.max(...result.flujos_auto_veh_h) / result.capacidad_auto
      : null;
  const vc_bici =
    result.flujos_bici_veh_h?.length && capacidadBici && capacidadBici > 0
      ? Math.max(...result.flujos_bici_veh_h) / capacidadBici
      : null;
  const vc_metro =
    result.carga_metro?.length && capacidadTren && frecMax && frecMax > 0
      ? Math.max(...result.carga_metro) / (frecMax * capacidadTren)
      : null;

  return {
    viajes_fisicos: agg.viajeros,
    modal_share: shares(agg.viajes_por_modo),
    tele_share_hogares:
      result.agentes.length > 0 ? tele / result.agentes.length : 0,
    tiempo_medio_min: Object.fromEntries(
      MODOS.map((m) => [m, agg.tiempo_medio_por_modo_min[m] ?? 0]),
    ) as Record<ModoTransporte, number>,
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
