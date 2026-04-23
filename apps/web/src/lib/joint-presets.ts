/**
 * Presets conjuntos (ciudad + política + uso de suelo) para la página /coupled.
 *
 * Cada preset configura los 3 módulos a la vez, permitiendo al estudiante
 * comparar escenarios coherentes (ej. "Compacta + Tarificación Vial") en
 * lugar de permutar parámetros uno por uno.
 */

import { defaultLandUseConfig } from "@/lib/api-v2";
import { defaultSimulationConfig } from "@/lib/defaults";
import { CITY_PRESETS, POLICY_PRESETS } from "@/lib/presets";
import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";

export interface JointPreset {
  key: string;
  /** Nombre corto para el selector. */
  titleKey: string;
  /** Descripción pedagógica de 1-2 líneas. */
  descriptionKey: string;
  /** Preset de ciudad (nombre en CITY_PRESETS). */
  city: keyof typeof CITY_PRESETS;
  /** Preset de política de transporte. */
  policy: keyof typeof POLICY_PRESETS;
  /** Override parcial del uso de suelo (opcional). */
  landUseOverride?: Partial<LandUseConfig>;
}

export const JOINT_PRESETS: readonly JointPreset[] = [
  {
    key: "compact-toll",
    titleKey: "coupled.presets.compact_toll.title",
    descriptionKey: "coupled.presets.compact_toll.desc",
    city: "Compacta",
    policy: "Tarificación Vial",
  },
  {
    key: "sparse-proauto",
    titleKey: "coupled.presets.sparse_proauto.title",
    descriptionKey: "coupled.presets.sparse_proauto.desc",
    city: "Dispersa",
    policy: "Pro-Auto",
  },
  {
    key: "base-probici",
    titleKey: "coupled.presets.base_probici.title",
    descriptionKey: "coupled.presets.base_probici.desc",
    city: "Base",
    policy: "Pro-Bici",
  },
  {
    key: "compact-metro",
    titleKey: "coupled.presets.compact_metro.title",
    descriptionKey: "coupled.presets.compact_metro.desc",
    city: "Compacta",
    policy: "Máx Metro",
  },
] as const;

/** Aplica un preset y retorna el par {sim, landUse} listo para correr. */
export function applyJointPreset(
  preset: JointPreset
): { sim: SimulationConfig; landUse: LandUseConfig } {
  const city = CITY_PRESETS[preset.city] ?? {};
  const pol = POLICY_PRESETS[preset.policy] ?? {};

  const sim: SimulationConfig = {
    ...defaultSimulationConfig,
    city: {
      ...defaultSimulationConfig.city,
      ...(city.largo_ciudad !== undefined && { largo_ciudad_km: city.largo_ciudad }),
      ...(city.densidad !== undefined && { densidad_por_celda: city.densidad }),
    },
    supply: {
      ...defaultSimulationConfig.supply,
      car: {
        ...defaultSimulationConfig.supply.car,
        ...(pol.num_pistas !== undefined && { num_pistas: pol.num_pistas }),
      },
      bike: {
        ...defaultSimulationConfig.supply.bike,
        ...(pol.cap_bici !== undefined && { capacidad_pista: pol.cap_bici }),
      },
      train: {
        ...defaultSimulationConfig.supply.train,
        ...(pol.num_estaciones !== undefined && { num_estaciones: pol.num_estaciones }),
        ...(pol.frec_max !== undefined && { frec_max: pol.frec_max }),
        ...(pol.cap_tren !== undefined && { capacidad_tren: pol.cap_tren }),
      },
    },
    demand: {
      ...defaultSimulationConfig.demand,
      globales: {
        ...defaultSimulationConfig.demand.globales,
        ...(pol.tarifa !== undefined && { costo_tarifa_metro: pol.tarifa }),
        ...(pol.parking !== undefined && { costo_parking: pol.parking }),
        ...(pol.bencina !== undefined && { costo_combustible_km: pol.bencina }),
      },
    },
  };

  const landUse: LandUseConfig = {
    ...defaultLandUseConfig,
    ...preset.landUseOverride,
  };

  return { sim, landUse };
}
