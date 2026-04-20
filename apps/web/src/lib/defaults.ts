import type {
  DemandConfig,
  SimulationConfig,
  StratumConfig,
  StratumId,
} from "@/lib/types";

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
    factor_emision_metro: 0.04,
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
    densidad_por_celda: 50,
    pendiente_porcentaje: 0,
    teletrabajo_factor: 1,
    share_estratos: [0.1, 0.4, 0.5],
    ingresos_estratos: [120, 50, 10],
  },
  supply: {
    bike: { v_media_kmh: 14, capacidad_pista: 800, alpha_bpr: 0.5, beta_bpr: 2 },
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
      capacidad_tren: 1200,
      num_estaciones: 10,
      v_caminata_kmh: 4.8,
      tasa_carga: 6,
      frec_min: 10,
      frec_max: 20,
    },
  },
  demand: defaultDemandConfig,
  max_iter: 10,
  tolerance: 0,
  seed: 42,
};
