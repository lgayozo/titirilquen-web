/**
 * Derivados PUROS de una corrida, para las figuras.
 *
 * `SandboxPage` había llegado a 1.438 líneas en una sola función. La intención
 * era mudar acá sus cuatro bloques de cálculo, pero al mirarlos de cerca sólo
 * uno es realmente puro: los otros arman etiquetas con i18n mientras calculan,
 * así que dependen del idioma activo y sacarlos obligaría a pasarles la función
 * de traducción — cambiar un problema de tamaño por uno de acoplamiento.
 *
 * Acá vive lo que sí entra y sale como dato. Lo que mezcla cálculo con rótulos
 * se queda en la página, marcado como presentación.
 *
 * Nada de esto es MODELO: eso vive en el núcleo Python. Acá se reordena lo que
 * el núcleo ya entregó para que una figura lo pueda dibujar.
 */

import type {
  IterationSnapshot,
  SimulationConfig,
  SimulationResult,
} from "@/lib/types";

/** Perfil de carga del corredor por modo, y si es flujo acumulado u origen. */
export function calcularFlujo(
  result: SimulationResult | null,
  lastIter: IterationSnapshot | null | undefined,
  cfgRes: SimulationConfig,
  flowMode: "auto" | "bici" | "metro" | "caminata",
) {
  if (!lastIter || !result) return null;
  const N = cfgRes.city.n_celdas;
  const largo = cfgRes.city.largo_ciudad_km;

  // `carga_metro` viene por TRAMO interestación (n_estaciones − 1 valores),
  // no por celda. Se remuestrea a la grilla para dibujarlo en el mismo eje de
  // km; queda como escalón, que es exactamente lo que es.
  const cargaMetroPorCelda = (): number[] | null => {
    const carga = result.carga_metro;
    const est = result.estaciones_km;
    if (!carga?.length || !est?.length) return null;
    return Array.from({ length: N }, (_, i) => {
      const km = ((i + 0.5) / N) * largo;
      let j = 0;
      while (j < carga.length - 1 && km >= (est[j + 1] ?? largo)) j++;
      return carga[j] ?? 0;
    });
  };

  const fOp = lastIter.frecuencia_metro;
  const capTren = cfgRes.supply.train.capacidad_tren;
  const capBici = cfgRes.supply.bike.capacidad_pista;

  const porModo: Record<
    "auto" | "bici" | "metro" | "caminata",
    {
      flujo: number[];
      // Solo se anima donde el flujo ES el cumsum por celda de la demanda
      // (auto y bici, verificado con error 0). La carga del metro se acumula
      // por estación, no por celda, así que animarla mentiría.
      demanda: number[] | null;
      capacidad: number | null;
      capacidadLabel?: string;
      color: string;
      esCorredor: boolean;
    }
  > = {
    auto: {
      flujo: result.flujos_auto_veh_h ?? lastIter.demanda_auto,
      demanda: result.flujos_auto_veh_h ? lastIter.demanda_auto : null,
      capacidad: result.capacidad_auto > 0 ? result.capacidad_auto : null,
      capacidadLabel: "veh/h",
      color: "var(--auto)",
      esCorredor: !!result.flujos_auto_veh_h,
    },
    bici: {
      flujo: result.flujos_bici_veh_h ?? lastIter.demanda_bici,
      demanda: result.flujos_bici_veh_h ? lastIter.demanda_bici : null,
      capacidad: capBici > 0 ? capBici : null,
      capacidadLabel: "bici/h",
      color: "var(--bici)",
      esCorredor: !!result.flujos_bici_veh_h,
    },
    metro: {
      flujo: cargaMetroPorCelda() ?? lastIter.demanda_metro,
      demanda: null,
      capacidad: fOp > 0 && capTren > 0 ? fOp * capTren : null,
      capacidadLabel: "pax/h",
      color: "var(--metro)",
      esCorredor: !!result.carga_metro?.length,
    },
    // La caminata no usa un corredor con capacidad compartida: la única serie
    // con sentido es dónde nacen los viajes, y va rotulada como tal.
    caminata: {
      flujo: lastIter.demanda_caminata,
      demanda: null,
      capacidad: null,
      color: "var(--walk)",
      esCorredor: false,
    },
  };
  return porModo[flowMode];
}
