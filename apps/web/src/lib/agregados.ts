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

import { defaultLandUseConfig } from "@/lib/defaults";
import type { AgregadosDict } from "@/lib/gen/trace.gen";
import type { LandUseConfig } from "@/lib/types-v2";
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

/** Por qué el excedente de dos corridas no se puede restar. */
export type RazonIncomparable =
  | "modos"
  | "betas"
  | "umbrales"
  | "teletrabajo"
  | "poblacion"
  | "medida";

/** Lo que hace falta de una corrida para decidir si su excedente se compara. */
export interface CorridaBienestar {
  config: SimulationConfig;
  /** `null` ⇒ el uso de suelo por defecto. */
  landUse: LandUseConfig | null;
  medida: "logsum" | "utilidad_maxima";
}

/**
 * ¿Es válido restar el excedente de dos corridas? `null` si sí; si no, la
 * primera razón que lo impide.
 *
 * El nivel del excedente tiene un cero arbitrario (lo fijan las ASC), y la
 * resta sólo lo cancela si las dos corridas lo comparten. Lo mueven:
 * - el conjunto de modos: con otro choice set el logsum cambia de escala;
 * - los β, ASC incluidas: mueven el cero y λ_h = |b_costo|, la unidad;
 * - la especificación de los umbrales («escalones» o «suaves»): es otra
 *   función de utilidad, con otras penalizaciones en cada distancia;
 * - el teletrabajo y la población: cambian cuántas personas suman un nivel
 *   que no es cero, así que el total se mueve aunque nadie gane ni pierda
 *   (H-E4 de la auditoría de oct-2026);
 * - la medida: logsum y utilidad máxima son definiciones distintas.
 * La tenencia de auto (`prob_auto`) NO está: bajarla es una política, y la
 * pérdida de logsum es lo que se quiere medir. Es una regla de
 * interpretación, no un cálculo, y por eso vive del lado que decide qué
 * mostrar.
 */
export function bienestarComparable(
  a: CorridaBienestar,
  b: CorridaBienestar,
): RazonIncomparable | null {
  const modos = (c: SimulationConfig) =>
    [...c.modos_habilitados].sort().join(",");
  if (modos(a.config) !== modos(b.config)) return "modos";
  const estratos = [1, 2, 3] as const;
  const betas = (c: SimulationConfig) =>
    JSON.stringify(estratos.map((h) => c.demand.estratos[h].betas));
  if (betas(a.config) !== betas(b.config)) return "betas";
  if (a.config.demand.globales.umbrales !== b.config.demand.globales.umbrales)
    return "umbrales";
  const tele = (c: SimulationConfig) =>
    JSON.stringify([
      c.demand.globales.teletrabajo_factor,
      estratos.map((h) => c.demand.estratos[h].prob_teletrabajo),
    ]);
  if (tele(a.config) !== tele(b.config)) return "teletrabajo";
  const h = (lu: LandUseConfig | null) =>
    JSON.stringify((lu ?? defaultLandUseConfig).H_por_estrato);
  if (h(a.landUse) !== h(b.landUse)) return "poblacion";
  if (a.medida !== b.medida) return "medida";
  return null;
}
