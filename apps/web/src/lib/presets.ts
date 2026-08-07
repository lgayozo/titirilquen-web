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
  /** Población total (ΣH). Solo en los presets que fijan la ESCALA; si falta,
   *  el preset conserva la población vigente (iso-población). */
  poblacion?: number;
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
  Base: { largo_ciudad: 20, densidad: 1800, sigma: 0.5, poblacion: 36_000 },
  Dispersa: { largo_ciudad: 40, densidad: 900, sigma: 0.9 },
  // ESCALA, no forma: misma geometría que Base con 4× la población. Único
  // preset que rompe la iso-población, y a propósito. Régimen opuesto al
  // default: espera = 30K/L_max cae de ~5 a ~1 min, el Mohring se aplana y
  // Downs-Thomson desaparece; lo que muerde es el andén. Ver presets.py.
  "Metrópolis": { largo_ciudad: 20, densidad: 7200, sigma: 0.5, poblacion: 144_000 },
};

export const POLICY_PRESETS: Record<string, PolicyPresetValues> = {
  Personalizado: {},
  // Política de referencia: todos los parámetros en su default. A diferencia de
  // «Personalizado» (dict vacío, hereda lo vigente), «Base» es reproducible.
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
    // AHORA sí reduce la emisión por km: antes solo abarataba la bencina, o sea
    // abarataba el auto y terminaba SUBIENDO el CO₂ (+1,6% medido).
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
  },
  Ciclorrecreovía: {
    num_pistas: 1,
    cap_bici: 6000,
    tarifa: 800,
    parking: 2000,
    bencina: 120,
    frec_max: 40,
    cap_tren: 1000,
    // Faltaba (7 de 8 claves): sin esto la política heredaba el valor vigente y
    // no era reproducible. 10 = default. Espejo de presets.py.
    num_estaciones: 10,
  },
};
