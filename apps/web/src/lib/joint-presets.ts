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
  /** Población total recomendada (escala de demanda) para que el loop converja
   *  sin gridlock. Una ciudad más larga/auto-dependiente colapsa con menos
   *  población; una compacta con buen transporte aguanta mucha más. */
  poblacionDefault: number;
}

export const JOINT_PRESETS: readonly JointPreset[] = [
  {
    key: "compact-toll",
    titleKey: "coupled.presets.compact_toll.title",
    descriptionKey: "coupled.presets.compact_toll.desc",
    city: "Compacta",
    policy: "Tarificación Vial",
    // Ciudad compacta ⇒ oferta de vivienda concentrada cerca del CBD (σ bajo).
    landUseOverride: { forma: "normal", oferta_sigma_frac: 0.32 },
    poblacionDefault: 40000,
  },
  {
    key: "sparse-proauto",
    titleKey: "coupled.presets.sparse_proauto.title",
    descriptionKey: "coupled.presets.sparse_proauto.desc",
    city: "Dispersa",
    policy: "Pro-Auto",
    // Sprawl ⇒ oferta extendida hacia la periferia (σ alto).
    landUseOverride: { forma: "normal", oferta_sigma_frac: 0.85 },
    // Corredor de 30 km auto-dependiente: gridlocka por sobre ~15k (todo el
    // flujo converge al CBD). Población baja para que el equilibrio sea estable.
    poblacionDefault: 12000,
  },
  {
    key: "base-probici",
    titleKey: "coupled.presets.base_probici.title",
    descriptionKey: "coupled.presets.base_probici.desc",
    city: "Base",
    policy: "Pro-Bici",
    landUseOverride: { forma: "normal", oferta_sigma_frac: 0.5 },
    poblacionDefault: 30000,
  },
  {
    key: "compact-metro",
    titleKey: "coupled.presets.compact_metro.title",
    descriptionKey: "coupled.presets.compact_metro.desc",
    city: "Compacta",
    policy: "Máx Metro",
    landUseOverride: { forma: "normal", oferta_sigma_frac: 0.32 },
    poblacionDefault: 40000,
  },
] as const;

/** Un parámetro del escenario, listo para mostrar (la página traduce labelKey). */
export interface PresetParam {
  key: string;
  /** Clave i18n del rótulo (namespace simulator). */
  labelKey: string;
  /** Valor ya formateado. */
  value: string;
  unit?: string;
  /** Grupo: de qué módulo proviene el parámetro. */
  group: "city" | "transport" | "land_use";
}

/**
 * Extrae los parámetros que **definen** el escenario (los que mueve el preset),
 * para que el estudiante vea *por qué* una ciudad es compacta / pro-auto / etc.
 * No es la config completa: solo las palancas pedagógicamente relevantes.
 */
export function describePresetParams(
  sim: SimulationConfig,
  landUse: LandUseConfig,
): PresetParam[] {
  const nf = (v: number) => v.toLocaleString("es-CL");
  return [
    // --- Ciudad / suelo (¿compacta o dispersa?) ---
    {
      key: "largo",
      labelKey: "coupled.param.largo",
      value: nf(sim.city.largo_ciudad_km),
      unit: "km",
      group: "city",
    },
    {
      // Población total = ΣH del uso de suelo. Es la **escala de demanda** real
      // del loop acoplado (a diferencia de `densidad_hab_km`, que no afecta
      // este módulo: la población viene del suelo, no de la densidad de celda).
      key: "poblacion",
      labelKey: "coupled.param.poblacion",
      value: nf(landUse.H_por_estrato.reduce((a, b) => a + b, 0)),
      unit: "hog",
      group: "land_use",
    },
    {
      key: "compacidad",
      labelKey: "coupled.param.compacidad",
      value: landUse.oferta_sigma_frac.toFixed(2),
      unit: "σ",
      group: "land_use",
    },
    // --- Transporte (¿pro-auto, pro-bici, pro-metro?) ---
    {
      key: "pistas",
      labelKey: "coupled.param.pistas",
      value: nf(sim.supply.car.num_pistas),
      group: "transport",
    },
    {
      key: "frec",
      labelKey: "coupled.param.frec",
      value: nf(sim.supply.train.frec_max),
      unit: "tr/h",
      group: "transport",
    },
    {
      key: "estaciones",
      labelKey: "coupled.param.estaciones",
      value: nf(sim.supply.train.num_estaciones),
      group: "transport",
    },
    {
      key: "cap_bici",
      labelKey: "coupled.param.cap_bici",
      value: nf(sim.supply.bike.capacidad_pista),
      group: "transport",
    },
    {
      key: "tarifa",
      labelKey: "coupled.param.tarifa",
      value: `$${nf(sim.demand.globales.costo_tarifa_metro)}`,
      group: "transport",
    },
    {
      key: "parking",
      labelKey: "coupled.param.parking",
      value: `$${nf(sim.demand.globales.costo_parking)}`,
      group: "transport",
    },
    {
      key: "bencina",
      labelKey: "coupled.param.bencina",
      value: `$${nf(sim.demand.globales.costo_combustible_km)}`,
      unit: "/km",
      group: "transport",
    },
  ];
}

/** Aplica un preset y retorna el par {sim, landUse} listo para correr. */
export function applyJointPreset(preset: JointPreset): {
  sim: SimulationConfig;
  landUse: LandUseConfig;
} {
  const city = CITY_PRESETS[preset.city] ?? {};
  const pol = POLICY_PRESETS[preset.policy] ?? {};

  const sim: SimulationConfig = {
    ...defaultSimulationConfig,
    city: {
      ...defaultSimulationConfig.city,
      ...(city.largo_ciudad !== undefined && {
        largo_ciudad_km: city.largo_ciudad,
      }),
      ...(city.densidad !== undefined && { densidad_hab_km: city.densidad }),
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
        ...(pol.num_estaciones !== undefined && {
          num_estaciones: pol.num_estaciones,
        }),
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
        ...(pol.factor_flota !== undefined && {
          factor_flota_auto: pol.factor_flota,
        }),
      },
    },
  };

  const landUse: LandUseConfig = {
    ...defaultLandUseConfig,
    ...preset.landUseOverride,
  };

  return { sim, landUse };
}
