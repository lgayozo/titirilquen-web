/**
 * El valor del tiempo entre estratos, dicho como se enseña: cuántas VECES vale
 * el del medio y el del alto respecto del bajo. Por defecto 2 y 4.
 *
 * Hasta nov-2026 el control era un deslizador sobre un exponente `s`
 * (λ_h = λ_medio·(λ_h/λ_medio calibrado)^s). No tenía unidad ni aparecía en
 * ninguna tabla: para saber qué había hecho había que ir a mirar los VoT.
 *
 * El VoT de un estrato es β_tiempo/β_costo·60 y β_tiempo es común a los tres,
 * así que la razón de VoT es la inversa de la razón de `b_costo`: ahí vive
 * toda la heterogeneidad, y es lo único que esto escribe.
 *
 * **El estrato medio queda fijo.** Al cambiar un múltiplo se mueven el bajo y
 * el alto: una escala común de λ no mueve la asignación (D-41), y con el medio
 * de ancla «Iguales» deja a los tres en el valor del medio.
 *
 * Es aritmética de presentación sobre la config (no matemática del modelo):
 * el núcleo sigue derivando λ_h = |b_costo_h| de lo que esto escriba.
 */

import { defaultSimulationConfig } from "@/lib/defaults";
import type { SimulationConfig } from "@/lib/types";

/** Cuántas veces vale el tiempo del medio y del alto respecto del bajo. */
export interface MultiplosVot {
  medio: number;
  alto: number;
}

const lam = (demand: SimulationConfig["demand"], h: 1 | 2 | 3) =>
  -demand.estratos[h].betas.b_costo;

/** Los múltiplos de la demanda viva, o `null` si algún `b_costo` no es
 *  negativo (el VoT no está definido). */
export function multiplosDe(
  demand: SimulationConfig["demand"],
): MultiplosVot | null {
  const [a, m, b] = [lam(demand, 1), lam(demand, 2), lam(demand, 3)];
  if (!(a > 0 && m > 0 && b > 0)) return null;
  return { medio: b / m, alto: b / a };
}

/** Los de fábrica: salen del núcleo (`presets.py`), no de este archivo. */
export const MULTIPLOS_CALIBRADOS: MultiplosVot = multiplosDe(
  defaultSimulationConfig.demand,
) ?? { medio: 1, alto: 1 };

/** Escribe los `b_costo` del bajo y del alto para los múltiplos dados, con el
 *  del medio vigente como ancla. */
export function conMultiplos(
  c: SimulationConfig,
  { medio, alto }: MultiplosVot,
): SimulationConfig {
  const m = lam(c.demand, 2);
  // VoT_bajo = VoT_medio / medio ⇒ λ_bajo = λ_medio · medio;
  // VoT_alto = alto · VoT_bajo  ⇒ λ_alto = λ_bajo / alto.
  const lamBajo = m * medio;
  const conLambda = (h: 1 | 3, valor: number) => ({
    ...c.demand.estratos[h],
    betas: { ...c.demand.estratos[h].betas, b_costo: -valor },
  });
  return {
    ...c,
    demand: {
      ...c.demand,
      estratos: {
        ...c.demand.estratos,
        1: conLambda(1, lamBajo / alto),
        3: conLambda(3, lamBajo),
      },
    },
  };
}
