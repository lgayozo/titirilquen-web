/**
 * Configuración inicial de la aplicación.
 *
 * Este archivo era una transcripción a mano de los defaults de Pydantic — unos
 * 130 números, incluidos los 42 coeficientes del logit, que podían
 * desincronizarse del núcleo sin que nada avisara. Hoy es un puente: los
 * valores vienen generados en `lib/gen/defaults.gen.ts` y las diferencias
 * deliberadas del frontend se aplican en `lib/overrides.ts`.
 *
 * Se conserva como módulo para no tocar los imports de media aplicación.
 */

export {
  defaultDemandConfig,
  defaultLandUseConfig,
  defaultSimulationConfig,
} from "@/lib/overrides";
