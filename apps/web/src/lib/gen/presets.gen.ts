// GENERADO por packages/titirilquen_core/tools/genera_contrato.py — NO EDITAR.
// Para cambiar algo de acá, cambiá el núcleo Python y corré `npm run sync:core`.

/** Presets de ciudad y de política. Declaran valores ABSOLUTOS, no
 *  diferencias contra el default: al recalibrar hay que moverlos, o
 *  aplicar una política revierte ese parámetro en silencio. */

/** Parámetros de forma urbana. */
export interface CityPresetValues {
  largo_ciudad?: number;
  densidad?: number;
  sigma?: number;
  poblacion?: number;
}

/** Parámetros de política. */
export interface PolicyPresetValues {
  tarifa?: number;
  parking?: number;
  num_pistas?: number;
  num_estaciones?: number;
  bencina?: number;
  cap_bici?: number;
  frec_max?: number;
  cap_tren?: number;
  factor_flota?: number;
}

export const CITY_PRESETS: Record<string, CityPresetValues> = {
  Personalizado: {},
  Compacta: {
    largo_ciudad: 8,
    densidad: 4500,
    sigma: 0.3,
  },
  Base: {
    largo_ciudad: 20,
    densidad: 1800,
    sigma: 0.5,
    poblacion: 36000,
  },
  Dispersa: {
    largo_ciudad: 40,
    densidad: 900,
    sigma: 0.9,
  },
  Metrópolis: {
    largo_ciudad: 20,
    densidad: 7200,
    sigma: 0.5,
    poblacion: 144000,
  },
};

export const POLICY_PRESETS: Record<string, PolicyPresetValues> = {
  Personalizado: {},
  Base: {
    tarifa: 800,
    parking: 2000,
    num_pistas: 2,
    num_estaciones: 10,
    bencina: 120,
    cap_bici: 2500,
    frec_max: 40,
    cap_tren: 1000,
    factor_flota: 1.0,
  },
  "TP Gratis": {
    tarifa: 0,
    parking: 2000,
    num_pistas: 2,
    num_estaciones: 10,
    bencina: 120,
    cap_bici: 2500,
    frec_max: 50,
    cap_tren: 1000,
    factor_flota: 1.0,
  },
  "Tarificación Vial": {
    tarifa: 800,
    parking: 5000,
    num_pistas: 2,
    num_estaciones: 10,
    bencina: 120,
    cap_tren: 1000,
    cap_bici: 2500,
    frec_max: 40,
    factor_flota: 1.0,
  },
  "Pro-Auto": {
    tarifa: 1000,
    parking: 1000,
    num_pistas: 3,
    num_estaciones: 8,
    bencina: 100,
    cap_tren: 800,
    cap_bici: 1250,
    frec_max: 6,
    factor_flota: 1.0,
  },
  "Pro-Bici": {
    tarifa: 800,
    parking: 2000,
    num_pistas: 2,
    cap_bici: 5000,
    frec_max: 40,
    bencina: 120,
    cap_tren: 1000,
    num_estaciones: 10,
    factor_flota: 1.0,
  },
  "Vehículos híbridos": {
    num_pistas: 2,
    bencina: 65,
    tarifa: 800,
    parking: 2000,
    frec_max: 40,
    cap_tren: 1000,
    num_estaciones: 10,
    cap_bici: 2500,
    factor_flota: 0.7,
  },
  "Máx Metro": {
    tarifa: 400,
    num_estaciones: 20,
    frec_max: 50,
    cap_tren: 1000,
    parking: 2000,
    bencina: 120,
    num_pistas: 2,
    cap_bici: 2500,
    factor_flota: 1.0,
  },
  Ciclorrecreovía: {
    num_pistas: 1,
    cap_bici: 6000,
    tarifa: 800,
    parking: 2000,
    bencina: 120,
    frec_max: 40,
    cap_tren: 1000,
    num_estaciones: 10,
    factor_flota: 1.0,
  },
};

export type CityPresetName = keyof typeof CITY_PRESETS;
export type PolicyPresetName = keyof typeof POLICY_PRESETS;
