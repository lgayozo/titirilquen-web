import type {
  DemandConfig,
  SimulationConfig,
  StratumConfig,
  StratumId,
} from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";

const baseBetas = (stratum: StratumId): StratumConfig => {
  if (stratum === 1) {
    return {
      prob_teletrabajo: 0.4,
      prob_auto: 0.9,
      betas: {
        asc_auto: 1.5,
        asc_metro: -0.2,
        asc_bici: -0.9,
        asc_caminata: -0.5,
        b_tiempo_viaje: -0.055,
        b_costo: -0.00008,
        b_tiempo_espera: -0.05,
        b_tiempo_caminata: -0.15,
        penalizaciones_fisicas: {
          bici_10: -0.09,
          bici_20: -0.15,
          bici_30: -0.5,
          walk_5: -0.09,
          walk_15: -0.18,
          walk_25: -0.4,
        },
      },
    };
  }
  if (stratum === 2) {
    return {
      prob_teletrabajo: 0.2,
      prob_auto: 0.6,
      betas: {
        asc_auto: 0.7889,
        asc_metro: 0.104,
        asc_bici: -0.6818,
        asc_caminata: 0.1,
        b_tiempo_viaje: -0.0331,
        b_costo: -0.0002,
        b_tiempo_espera: -0.0243,
        b_tiempo_caminata: -0.044,
        penalizaciones_fisicas: {
          bici_10: -0.0634,
          bici_20: -0.1,
          bici_30: -0.4,
          walk_5: -0.05,
          walk_15: -0.09,
          walk_25: -0.2,
        },
      },
    };
  }
  return {
    prob_teletrabajo: 0.05,
    prob_auto: 0.3,
    betas: {
      asc_auto: 0.2,
      asc_metro: 0.25,
      asc_bici: -0.4,
      asc_caminata: 0.4,
      b_tiempo_viaje: -0.015,
      b_costo: -0.0006,
      b_tiempo_espera: -0.015,
      b_tiempo_caminata: -0.025,
      penalizaciones_fisicas: {
        bici_10: -0.03,
        bici_20: -0.05,
        bici_30: -0.7,
        walk_5: -0.025,
        walk_15: -0.04,
        walk_25: -0.08,
      },
    },
  };
};

export const defaultDemandConfig: DemandConfig = {
  globales: {
    v_auto: 31,
    v_metro: 35,
    v_bici: 14,
    v_caminata: 4.8,
    costo_combustible_km: 120,
    costo_tarifa_metro: 800,
    costo_parking: 6000,
    factor_emision_auto: 0.18,
    factor_emision_metro_tren_km: 2.5,
  },
  estratos: {
    1: baseBetas(1),
    2: baseBetas(2),
    3: baseBetas(3),
  },
};

export const defaultSimulationConfig: SimulationConfig = {
  city: {
    n_celdas: 201,
    largo_ciudad_km: 20,
    // 500 hab/km ≈ 50 hogares por cuadra de 100 m; población = 500 × 20 km = 10.000.
    densidad_hab_km: 500,
    pendiente_porcentaje: 0,
    teletrabajo_factor: 1,
    share_estratos: [0.1, 0.4, 0.5],
  },
  supply: {
    bike: {
      v_media_kmh: 14,
      capacidad_pista: 800,
      alpha_bpr: 0.5,
      beta_bpr: 2,
    },
    car: {
      v_max_kmh: 31,
      ancho_pista_m: 3.5,
      largo_vehiculo_m: 5,
      gap_m: 2,
      num_pistas: 2,
      alpha_bpr: 0.8,
      beta_bpr: 2,
    },
    train: {
      v_tren_kmh: 35,
      // Calibrado a la escala de demanda del modelo para que la frecuencia
      // endógena sea responsiva y el efecto Mohring sea visible (antes 1200
      // dejaba f clavada en f_min — ver docs/VERIFICACION_TRANSPORTE.md H1).
      capacidad_tren: 300,
      num_estaciones: 10,
      v_caminata_kmh: 4.8,
      tasa_carga: 6,
      // Rango realista de metro: ~10 min (valle) a ~2 min (punta) de intervalo.
      // El rango amplio fortalece el efecto Mohring (ver DISCREPANCIES D-18).
      frec_min: 6,
      frec_max: 30,
      anden_alpha: 0.5,
      anden_beta: 4,
    },
  },
  demand: defaultDemandConfig,
  // 20 (no 12): margen para la cola lenta ~1/it del MSA en escenarios rígidos
  // (ciclovía saturada / densidad alta); el corte real es por tolerance (D-21/H4).
  max_iter: 20,
  // Criterio de convergencia: corta cuando el máximo cambio de tiempo de viaje
  // (cualquier modo/celda) es < tolerance min en 2 iteraciones consecutivas.
  tolerance: 0.1,
  seed: 42,
  assignment: "montecarlo",
  modos_habilitados: ["Auto", "Metro", "Bici", "Caminata"],
};

export const defaultLandUseConfig: LandUseConfig = {
  H_por_estrato: [1000, 4000, 5000],
  // Unidades físicas (D-26/D-27): α en utiles/min, ρ en utiles/(hogar/km),
  // y en $/mes. Calibración equivalente a la antigua en 201 celdas / 20 km.
  estratos: [
    { y: 3_500_000, lambda: 1, alpha: 6.5, rho: 0.1 },
    { y: 1_500_000, lambda: 1, alpha: 6.0, rho: 0.1 },
    { y: 500_000, lambda: 1, alpha: 5.5, rho: 0.1 },
  ],
  beta: 1,
  solver: "heteroscedastic",
  tol: 1e-8,
  max_iter: 2000,
  forma: "normal",
  oferta_sigma_frac: 0.5,
  forma_param: 0.5,
};
