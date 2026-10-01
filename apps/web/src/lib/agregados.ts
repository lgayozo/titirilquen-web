/**
 * Agregados de ciudad completa — lectura, no cálculo.
 *
 * Este archivo tenía 326 líneas de matemática económica en TypeScript: logsum,
 * excedente del consumidor, costo generalizado en dos versiones, recaudación,
 * costo del operador y bienestar social. Todo apoyado en `utility.ts`, que es
 * una reimplementación a mano de la función de utilidad del núcleo. O sea: los
 * indicadores que el estudiante usa para juzgar una política se calculaban con
 * matemática duplicada y sin un solo test.
 *
 * Ahora los calcula el núcleo (`titirilquen_core/bienestar.py`) y llegan en el
 * resultado de la simulación. Acá quedan las dos cosas que sí son del
 * frontend: adaptar los nombres y decidir cuándo una comparación es válida.
 */

import type { AgregadosDict } from "@/lib/gen/trace.gen";
import type {
  DemandConfig,
  SimulationConfig,
  SimulationResult,
  StratumId,
} from "@/lib/types";

export type { AgregadosDict as Agregados };

/**
 * Los agregados de una corrida, o `null` si el resultado viene de un motor que
 * no los trae (por ejemplo un wheel viejo cacheado en el navegador).
 */
export function agregadosDe(result: SimulationResult): AgregadosDict | null {
  return result.agregados ?? null;
}

/** Valor del tiempo conductual del estrato, en $/hora: β_tiempo/β_costo · 60.
 *
 * Se conserva en TS porque el panel de calibración lo recalcula EN VIVO
 * mientras el usuario mueve los coeficientes, sin correr la simulación. Es una
 * división, no un modelo — y el valor que se muestra tras simular sale del
 * núcleo, en `agregados.vot_por_estrato_clp_hora`.
 */
export function votClpHora(demand: DemandConfig, h: StratumId): number {
  const b = demand.estratos[h].betas;
  if (b.b_costo === 0) return 0;
  return (b.b_tiempo_viaje / b.b_costo) * 60;
}

/**
 * ¿Es válido comparar el excedente de dos configuraciones?
 *
 * Sólo si comparten el conjunto de modos: el logsum tiene cero arbitrario y con
 * distinto choice set cambia de escala, así que la diferencia deja de ser un
 * excedente y pasa a ser un artefacto. Es una regla de interpretación, no un
 * cálculo, y por eso vive del lado que decide qué mostrar.
 */
export function logsumComparable(
  a: SimulationConfig,
  b: SimulationConfig,
): boolean {
  const sa = [...a.modos_habilitados].sort().join(",");
  const sb = [...b.modos_habilitados].sort().join(",");
  return sa === sb;
}
