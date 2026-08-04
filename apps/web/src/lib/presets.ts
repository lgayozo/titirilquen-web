/**
 * Espejo de `titirilquen_core.presets.CITY_PRESETS` y `POLICY_PRESETS` para uso
 * cliente (cuando se corre con engine=local no queremos depender del API).
 */

export interface CityPresetValues {
  largo_ciudad?: number;
  /** Densidad física en hab/km (D-28). A iso-población es la CONSECUENCIA
   *  (ΣH/largo), no un input: la app puebla desde ΣH del uso de suelo. */
  densidad?: number;
  /** Concentración de la oferta de vivienda (σ): la otra dimensión de la forma
   *  urbana — dónde vive la gente dentro de la ciudad. */
  sigma?: number;
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
  /** Multiplicador de la emisión por km del auto (composición de la flota). */
  factor_flota?: number;
}

// Calibración ISO-POBLACIÓN (ΣH = 36.000): comparan FORMA urbana —extensión y
// concentración— con la misma gente; la densidad es la consecuencia. Rango
// ampliado respecto del original (12/20/30 sin σ), que a iso-población movía la
// mitad del efecto. Espejo de presets.py — ver ahí la justificación medida.
export const CITY_PRESETS: Record<string, CityPresetValues> = {
  Personalizado: {},
  Compacta: { largo_ciudad: 8, densidad: 4500, sigma: 0.3 },
  Base: { largo_ciudad: 20, densidad: 1800, sigma: 0.5 },
  Dispersa: { largo_ciudad: 40, densidad: 900, sigma: 0.9 },
};

export const POLICY_PRESETS: Record<string, PolicyPresetValues> = {
  Personalizado: {},
  "TP Gratis": {
    tarifa: 0,
    parking: 4000,
    num_pistas: 2,
    num_estaciones: 10,
    bencina: 120,
    cap_bici: 2500,
    frec_max: 50,
    cap_tren: 300,
  },
  "Tarificación Vial": {
    tarifa: 800,
    parking: 10000,
    num_pistas: 2,
    num_estaciones: 10,
    bencina: 120,
    cap_tren: 300,
    cap_bici: 2500,
    frec_max: 40,
  },
  "Pro-Auto": {
    tarifa: 1000,
    parking: 2000,
    num_pistas: 3,
    num_estaciones: 8,
    bencina: 100,
    cap_tren: 250,
    cap_bici: 1250,
    frec_max: 6,
  },
  "Pro-Bici": {
    tarifa: 800,
    parking: 4000,
    num_pistas: 2,
    cap_bici: 5000,
    frec_max: 40,
    bencina: 120,
    cap_tren: 300,
    num_estaciones: 10,
  },
  "Vehículos híbridos": {
    num_pistas: 2,
    bencina: 65,
    tarifa: 800,
    parking: 4000,
    frec_max: 40,
    cap_tren: 300,
    num_estaciones: 10,
    cap_bici: 2500,
    // AHORA sí reduce la emisión por km: antes solo abarataba la bencina, o sea
    // abarataba el auto y terminaba SUBIENDO el CO₂ (+1,6% medido).
    factor_flota: 0.7,
  },
  "Máx Metro": {
    tarifa: 400,
    num_estaciones: 20,
    frec_max: 50,
    cap_tren: 300,
    parking: 4000,
    bencina: 120,
    num_pistas: 2,
    cap_bici: 2500,
  },
  Ciclorrecreovía: {
    num_pistas: 1,
    cap_bici: 6000,
    tarifa: 800,
    parking: 4000,
    bencina: 120,
    frec_max: 40,
    cap_tren: 300,
    // Faltaba (7 de 8 claves): sin esto la política heredaba el valor vigente y
    // no era reproducible. 10 = default. Espejo de presets.py.
    num_estaciones: 10,
  },
};
