/**
 * Tipos de uso de suelo y del loop acoplado suelo ↔ transporte.
 *
 * Este archivo **era** un espejo escrito a mano de los esquemas Pydantic, y fue
 * el último que quedó en pie. La cirugía de arquitectura de agosto de 2026
 * generó el contrato desde Python, pero se detuvo en `SimulationConfig`: acá
 * seguían declarados a mano `LandUseConfig` y `LandUseStratumConfig` —los
 * mismos que el generador ya emitía en `gen/tipos.gen.ts`, o sea DOS veces— y
 * las siete formas de resultado del acoplado.
 *
 * Nada fallaba: los campos coincidían. Pero siete archivos importaban la copia
 * de acá y ninguna herramienta obligaba a que siguiera coincidiendo, que es la
 * definición del problema que toda la cirugía vino a resolver.
 *
 * Hoy no queda ninguna declaración propia: sólo alias. Los nombres se conservan
 * porque son los que usa la aplicación —el núcleo llama `…Dict` a lo que el
 * frontend llama `LandUseResult`— y renombrarlos habría sido un diff enorme sin
 * ganancia.
 */

export type { LandUseConfig, LandUseStratumConfig } from "@/lib/gen/tipos.gen";

export type {
  CoupledResultDict as CoupledResult,
  EquilibriumMetrics,
  LandUseResultDict as LandUseResult,
  LandUseSolveDict as LandUseSolveResponse,
  OuterIterationDict as OuterIteration,
  StratumMetrics,
  SystemMetrics,
} from "@/lib/gen/trace.gen";

import type { LandUseConfig, SimulationConfig } from "@/lib/types";
import type { StratumMetrics } from "@/lib/gen/trace.gen";

/**
 * Las formas de la oferta de vivienda. Se deriva del campo en vez de
 * re-escribir la lista: si el núcleo agrega una forma nueva, ésta la hereda.
 */
export type FormaOferta = LandUseConfig["forma"];

/**
 * Categorías del reparto modal. También derivada — las claves las fija
 * `constantes.CategoriaModal` en Python.
 */
export type RepartoModal = StratumMetrics["reparto_modal"];

/**
 * Entrada del loop acoplado.
 *
 * Es la única forma de este archivo que no viene del generador, porque no es
 * una salida del núcleo sino la petición que se le arma: vive como modelo
 * Pydantic en `apps/api/src/api/main.py` y como argumento del worker. No es un
 * espejo: sus dos campos con estructura son tipos generados, así que un cambio
 * en el esquema llega solo. Los otros dos son números.
 */
export interface CoupledRequest {
  sim: SimulationConfig;
  land_use: LandUseConfig;
  outer_max_iter: number;
  /** Tolerancia del loop exterior, en minutos. */
  outer_tol: number;
}
