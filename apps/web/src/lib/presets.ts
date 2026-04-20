/**
 * Espejo de `titirilquen_core.presets.CITY_PRESETS` y `POLICY_PRESETS` para uso
 * cliente (cuando se corre con engine=local no queremos depender del API).
 */

export interface CityPresetValues {
  largo_ciudad?: number;
  densidad?: number;
}

export interface PolicyPresetValues {
  tarifa?: number;
  parking?: number;
  num_pistas?: number;
  num_estaciones?: number;
  bencina?: number;
  cap_bici?: number;
  frec_max?: number;
  cap_tren?: number;
}

export const CITY_PRESETS: Record<string, CityPresetValues> = {
  Personalizado: {},
  Compacta: { largo_ciudad: 12, densidad: 250 },
  Base: { largo_ciudad: 20, densidad: 180 },
  Dispersa: { largo_ciudad: 30, densidad: 100 },
};

export const POLICY_PRESETS: Record<string, PolicyPresetValues> = {
  Personalizado: {},
  "TP Gratis": {
    tarifa: 0, parking: 6000, num_pistas: 2, num_estaciones: 10,
    bencina: 120, cap_bici: 800, frec_max: 35, cap_tren: 1200,
  },
  "Tarificación Vial": {
    tarifa: 800, parking: 15000, num_pistas: 2, num_estaciones: 10,
    bencina: 120, cap_tren: 1200, cap_bici: 800, frec_max: 20,
  },
  "Pro-Auto": {
    tarifa: 1000, parking: 3000, num_pistas: 3, num_estaciones: 8,
    bencina: 100, cap_tren: 1000, cap_bici: 500, frec_max: 6,
  },
  "Pro-Bici": {
    tarifa: 800, parking: 6000, num_pistas: 2, cap_bici: 5000,
    frec_max: 20, bencina: 120, cap_tren: 1200, num_estaciones: 10,
  },
  "Vehículos híbridos": {
    num_pistas: 2, bencina: 65, tarifa: 800, parking: 6000,
    frec_max: 20, cap_tren: 1200, num_estaciones: 10, cap_bici: 800,
  },
  "Máx Metro": {
    tarifa: 400, num_estaciones: 20, frec_max: 50, cap_tren: 1200,
    parking: 6000, bencina: 120, num_pistas: 2, cap_bici: 800,
  },
  Ciclorrecreovía: {
    num_pistas: 1, cap_bici: 6000, tarifa: 800, parking: 6000,
    bencina: 120, frec_max: 20, cap_tren: 1200,
  },
};
