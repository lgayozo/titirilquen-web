/**
 * Tipos del dominio del frontend.
 *
 * Las formas que vienen del núcleo —configuración, presets, resultados— se
 * GENERAN desde Pydantic en `lib/gen/` y se re-exportan acá para no tocar los
 * imports de media aplicación. Este archivo era una transcripción a mano de
 * 14 interfaces; lo que queda escrito son los tipos que sólo existen en el
 * frontend.
 */

export type {
  BikeSupplyParams,
  CarSupplyParams,
  CityConfig,
  DemandConfig,
  GlobalConfig,
  LandUseConfig,
  PhysicalPenalties,
  SimulationConfig,
  StratumBetas,
  StratumConfig,
  StratumId,
  SupplyConfig,
  TrainSupplyParams,
} from "@/lib/gen/tipos.gen";

export type {
  AgenteDict as AgentRecord,
  SnapshotDict as IterationSnapshot,
  TraceDict as SimulationResult,
} from "@/lib/gen/trace.gen";

/** Todos los modos, incluido el teletrabajo (que no es elegible: se decide
 *  antes de la elección de modo). */
export type Modo = "Auto" | "Metro" | "Bici" | "Caminata" | "Teletrabajo";

export type ModoTransporte = Exclude<Modo, "Teletrabajo">;
