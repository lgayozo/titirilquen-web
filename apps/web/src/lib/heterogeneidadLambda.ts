/**
 * «Heterogeneidad de λ»: un solo parámetro `s` que mueve los tres `b_costo`
 * a lo largo de una curva que pasa por la calibración vigente.
 *
 *     λ_h(s) = λ_medio · (λ_h^cal / λ_medio^cal)^s,   b_costo_h = −λ_h(s)
 *
 * s = 0 ⇒ los tres λ iguales al del medio · s = 1 ⇒ la calibración exacta ·
 * s = 2 ⇒ el doble de dispersión en escala logarítmica. El estrato medio queda
 * fijo: una escala común de λ no mueve la asignación (D-41), así que el control
 * mueve sólo lo que importa, la DIFERENCIA de valor del tiempo entre estratos.
 * Se interpola en logaritmos porque los λ se comparan por razones.
 *
 * Es aritmética de presentación sobre la config (no matemática del modelo):
 * el núcleo sigue derivando λ_h = |b_costo_h| de lo que esto escriba.
 */

import { defaultSimulationConfig } from "@/lib/defaults";
import type { SimulationConfig } from "@/lib/types";

const lamCal = (h: 1 | 2 | 3) =>
  -defaultSimulationConfig.demand.estratos[h].betas.b_costo;

/** Razones calibradas λ_h/λ_medio de los estratos alto (1) y bajo (3). */
const RAZON = { 1: lamCal(1) / lamCal(2), 3: lamCal(3) / lamCal(2) } as const;

/** `s` de la demanda viva, o `null` si sus `b_costo` no caen en la curva
 *  (p. ej. editados a mano): en ese caso el control dice «personalizado». */
export function sDeDemanda(demand: SimulationConfig["demand"]): number | null {
  const lam = (h: 1 | 2 | 3) => -demand.estratos[h].betas.b_costo;
  const m = lam(2);
  if (!(lam(1) > 0 && m > 0 && lam(3) > 0)) return null;
  const sA = Math.log(lam(1) / m) / Math.log(RAZON[1]);
  const sB = Math.log(lam(3) / m) / Math.log(RAZON[3]);
  return Math.abs(sA - sB) < 1e-6 ? sA : null;
}

/** Escribe los `b_costo` del alto y el bajo para el `s` dado, con el λ del
 *  medio vigente como ancla. */
export function conHeterogeneidad(
  c: SimulationConfig,
  s: number,
): SimulationConfig {
  const m = -c.demand.estratos[2].betas.b_costo;
  const conBeta = (h: 1 | 3) => ({
    ...c.demand.estratos[h],
    betas: {
      ...c.demand.estratos[h].betas,
      b_costo: -m * Math.pow(RAZON[h], s),
    },
  });
  return {
    ...c,
    demand: {
      ...c.demand,
      estratos: { ...c.demand.estratos, 1: conBeta(1), 3: conBeta(3) },
    },
  };
}
