// GENERADO por packages/titirilquen_core/tools/genera_contrato.py — NO EDITAR.
// Para cambiar algo de acá, cambiá el núcleo Python y corré `npm run sync:core`.

import type { SimulationConfig, LandUseConfig } from "./tipos.gen";

/** Defaults del NÚCLEO. El frontend aplica encima sus divergencias
 *  intencionales — ver `lib/overrides.ts`. */
export const DEFAULTS_CORE: SimulationConfig = {
  city: {
    n_celdas: 1001,
    largo_ciudad_km: 20.0,
    densidad_hab_km: 500.0,
    pendiente_porcentaje: 0.0,
    teletrabajo_factor: 1.0,
    share_estratos: [0.2, 0.5, 0.3],
  },
  supply: {
    bike: {
      v_media_kmh: 14,
      capacidad_pista: 2500,
      alpha_bpr: 0.5,
      beta_bpr: 2.0,
    },
    car: {
      v_max_kmh: 31,
      ancho_pista_m: 3.5,
      largo_vehiculo_m: 5.0,
      gap_m: 2.0,
      num_pistas: 2,
      alpha_bpr: 0.8,
      beta_bpr: 2.0,
      capacidad_pista: null,
    },
    train: {
      v_tren_kmh: 35,
      capacidad_tren: 1000,
      num_estaciones: 10,
      v_caminata_kmh: 4.8,
      costo_operacion_tren_km: 12000,
      factor_dia_punta: 2.0,
      tiempo_detencion_min: 0.5,
      frec_min: 2,
      frec_max: 40,
      anden_alpha: 0.5,
      anden_beta: 4.0,
    },
  },
  demand: {
    globales: {
      v_auto: 31,
      v_metro: 35,
      v_bici: 14,
      v_caminata: 4.8,
      corte_caminata_min: 30.0,
      corte_bici_min: 45.0,
      costo_combustible_km: 120,
      costo_tarifa_metro: 800,
      costo_parking: 2000,
      factor_flota_auto: 1.0,
      factor_emision_metro_tren_km: 2.5,
    },
    estratos: {
      "1": {
        prob_teletrabajo: 0.4,
        prob_auto: 0.9,
        betas: {
          asc_auto: 0.54164,
          asc_metro: -0.12036,
          asc_bici: -0.71616,
          asc_caminata: -0.12036,
          b_tiempo_viaje: -0.0331,
          b_costo: -0.000320323,
          b_tiempo_espera: -0.0662,
          b_tiempo_acceso: -0.0662,
          b_tiempo_caminata: -0.05627,
          penalizaciones_fisicas: {
            bici_10: -0.054164,
            bici_20: -0.090273,
            bici_30: -0.30091,
            walk_5: -0.054164,
            walk_15: -0.10833,
            walk_25: -0.24073,
          },
        },
      },
      "2": {
        prob_teletrabajo: 0.2,
        prob_auto: 0.6,
        betas: {
          asc_auto: 0.766,
          asc_metro: 0.104,
          asc_bici: -0.4918,
          asc_caminata: 0.104,
          b_tiempo_viaje: -0.0331,
          b_costo: -0.00064065,
          b_tiempo_espera: -0.0662,
          b_tiempo_acceso: -0.0662,
          b_tiempo_caminata: -0.05627,
          penalizaciones_fisicas: {
            bici_10: -0.0634,
            bici_20: -0.1,
            bici_30: -0.4,
            walk_5: -0.05,
            walk_15: -0.09,
            walk_25: -0.2,
          },
        },
      },
      "3": {
        prob_teletrabajo: 0.05,
        prob_auto: 0.25,
        betas: {
          asc_auto: 1.2137,
          asc_metro: 0.55167,
          asc_bici: -0.044133,
          asc_caminata: 0.55167,
          b_tiempo_viaje: -0.0331,
          b_costo: -0.00124125,
          b_tiempo_espera: -0.0662,
          b_tiempo_acceso: -0.0662,
          b_tiempo_caminata: -0.05627,
          penalizaciones_fisicas: {
            bici_10: -0.0662,
            bici_20: -0.11033,
            bici_30: -0.44133,
            walk_5: -0.055167,
            walk_15: -0.088267,
            walk_25: -0.17653,
          },
        },
      },
    },
  },
  max_iter: 20,
  tolerance: 0.1,
  seed: null,
  assignment: "montecarlo",
  modos_habilitados: ["Auto", "Metro", "Bici", "Caminata"],
} as const;

export const DEFAULTS_LAND_USE_CORE: LandUseConfig = {
  H_por_estrato: [33300, 33300, 33300],
  estratos: [
    {
      y: 3500000.0,
      lambda: 0.000320323,
      alpha: 1.0,
      rho: 0.0052,
    },
    {
      y: 1500000.0,
      lambda: 0.00064065,
      alpha: 1.0,
      rho: 0.0052,
    },
    {
      y: 500000.0,
      lambda: 0.00124125,
      alpha: 1.0,
      rho: 0.0052,
    },
  ],
  beta: 1.0,
  tol: 1e-8,
  max_iter: 10000,
  forma: "normal",
  oferta_sigma_frac: 0.5,
  forma_param: 0.5,
} as const;

/** Calibración vigente de los tres estratos (los 42 coeficientes del
 *  logit). Era la mayor duplicación a mano del repo y la única sin test
 *  de contrato. */
export const ESTRATOS_CALIBRADOS = {
  "1": {
    prob_teletrabajo: 0.4,
    prob_auto: 0.9,
    betas: {
      asc_auto: 0.54164,
      asc_metro: -0.12036,
      asc_bici: -0.71616,
      asc_caminata: -0.12036,
      b_tiempo_viaje: -0.0331,
      b_costo: -0.000320323,
      b_tiempo_espera: -0.0662,
      b_tiempo_acceso: -0.0662,
      b_tiempo_caminata: -0.05627,
      penalizaciones_fisicas: {
        bici_10: -0.054164,
        bici_20: -0.090273,
        bici_30: -0.30091,
        walk_5: -0.054164,
        walk_15: -0.10833,
        walk_25: -0.24073,
      },
    },
  },
  "2": {
    prob_teletrabajo: 0.2,
    prob_auto: 0.6,
    betas: {
      asc_auto: 0.766,
      asc_metro: 0.104,
      asc_bici: -0.4918,
      asc_caminata: 0.104,
      b_tiempo_viaje: -0.0331,
      b_costo: -0.00064065,
      b_tiempo_espera: -0.0662,
      b_tiempo_acceso: -0.0662,
      b_tiempo_caminata: -0.05627,
      penalizaciones_fisicas: {
        bici_10: -0.0634,
        bici_20: -0.1,
        bici_30: -0.4,
        walk_5: -0.05,
        walk_15: -0.09,
        walk_25: -0.2,
      },
    },
  },
  "3": {
    prob_teletrabajo: 0.05,
    prob_auto: 0.25,
    betas: {
      asc_auto: 1.2137,
      asc_metro: 0.55167,
      asc_bici: -0.044133,
      asc_caminata: 0.55167,
      b_tiempo_viaje: -0.0331,
      b_costo: -0.00124125,
      b_tiempo_espera: -0.0662,
      b_tiempo_acceso: -0.0662,
      b_tiempo_caminata: -0.05627,
      penalizaciones_fisicas: {
        bici_10: -0.0662,
        bici_20: -0.11033,
        bici_30: -0.44133,
        walk_5: -0.055167,
        walk_15: -0.088267,
        walk_25: -0.17653,
      },
    },
  },
} as const;
