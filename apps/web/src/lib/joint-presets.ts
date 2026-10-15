/**
 * Presets conjuntos (ciudad + política + uso de suelo) para la página /coupled.
 *
 * Cada preset configura los 3 módulos a la vez, permitiendo al estudiante
 * comparar escenarios coherentes (ej. "Compacta + Tarificación Vial") en
 * lugar de permutar parámetros uno por uno.
 */

import { defaultLandUseConfig } from "@/lib/defaults";
import { defaultSimulationConfig } from "@/lib/defaults";
import { fmtParkingPorViaje } from "@/lib/parking";
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
  /** Hogares del escenario: `applyJointPreset` la escribe en `H_por_estrato`,
   *  que es la única fuente de población (D10d). Difiere entre presets a
   *  propósito: una ciudad larga y auto-dependiente colapsa con menos gente;
   *  una compacta con buen transporte aguanta mucha más (D-24). */
  poblacion: number;
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
    poblacion: 40000,
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
    poblacion: 12000,
  },
  {
    key: "base-probici",
    titleKey: "coupled.presets.base_probici.title",
    descriptionKey: "coupled.presets.base_probici.desc",
    city: "Base",
    policy: "Pro-Bici",
    landUseOverride: { forma: "normal", oferta_sigma_frac: 0.5 },
    poblacion: 30000,
  },
  {
    key: "compact-metro",
    titleKey: "coupled.presets.compact_metro.title",
    descriptionKey: "coupled.presets.compact_metro.desc",
    city: "Compacta",
    policy: "Máx Metro",
    landUseOverride: { forma: "normal", oferta_sigma_frac: 0.32 },
    poblacion: 40000,
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
  /** Línea secundaria, ya formateada. */
  sub?: string;
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
  t: (k: string, o?: Record<string, unknown>) => string,
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
      unit: t("economy_params.por_dia", { ns: "simulator" }),
      sub: fmtParkingPorViaje(sim.demand.globales.costo_parking, t),
      group: "transport",
    },
    {
      key: "bencina",
      labelKey: "coupled.param.bencina",
      value: `$${nf(sim.demand.globales.costo_combustible_km)}`,
      unit: "/km",
      group: "transport",
    },
    {
      key: "peaje",
      labelKey: "coupled.param.peaje",
      value: `$${nf(sim.demand.globales.peaje_km)}`,
      unit: "/km",
      group: "transport",
    },
  ];
}

/** Aplica un preset y retorna el par {sim, landUse} listo para correr.
 *
 *  El preset fija sus palancas (ciudad, oferta, precios, suelo) sobre los
 *  defaults, pero la CALIBRACIÓN viene de `calibrado`: los estratos de la
 *  demanda (betas, penalizaciones, tenencia de auto, teletrabajo) y los cortes
 *  de caminata y bici. Hasta oct-2026 salía todo de `defaultSimulationConfig`
 *  y el preset descartaba la calibración del usuario, y con ella su
 *  λ_h = |b_costo_h| del suelo (D10 de la auditoría). */
export function applyJointPreset(
  preset: JointPreset,
  calibrado: SimulationConfig,
): {
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
      estratos: calibrado.demand.estratos,
      globales: {
        ...defaultSimulationConfig.demand.globales,
        corte_caminata_min: calibrado.demand.globales.corte_caminata_min,
        corte_bici_min: calibrado.demand.globales.corte_bici_min,
        ...(pol.tarifa !== undefined && { costo_tarifa_metro: pol.tarifa }),
        ...(pol.parking !== undefined && { costo_parking: pol.parking }),
        ...(pol.bencina !== undefined && { costo_combustible_km: pol.bencina }),
        ...(pol.peaje !== undefined && { peaje_km: pol.peaje }),
        ...(pol.factor_flota !== undefined && {
          factor_flota_auto: pol.factor_flota,
        }),
      },
    },
  };

  const base: LandUseConfig = {
    ...defaultLandUseConfig,
    ...preset.landUseOverride,
  };
  // La población del preset va a H_por_estrato conservando la composición
  // por estrato. Enteros (`tuple[int, int, int]` en Pydantic) y el tercero
  // absorbe el redondeo para que ΣH dé exacto, como en PresetGallery.
  const [h1, h2, h3] = base.H_por_estrato;
  const k = preset.poblacion / (h1 + h2 + h3 || 1);
  const a = Math.round(h1 * k);
  const b = Math.round(h2 * k);
  const landUse: LandUseConfig = {
    ...base,
    H_por_estrato: [a, b, preset.poblacion - a - b],
  };

  return { sim, landUse };
}
