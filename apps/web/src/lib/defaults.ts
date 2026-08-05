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
        asc_bici: -1.19,
        asc_caminata: -0.5,
        b_tiempo_viaje: -0.055,
        b_costo: -0.00053226,
        b_tiempo_espera: -0.11,
        b_tiempo_caminata: -0.0935,
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
        asc_bici: -0.4918,
        asc_caminata: 0.1,
        b_tiempo_viaje: -0.0331,
        b_costo: -0.00064065,
        b_tiempo_espera: -0.0662,
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
    };
  }
  return {
    prob_teletrabajo: 0.05,
    prob_auto: 0.25,
    betas: {
      asc_auto: 0.2,
      asc_metro: 0.25,
      asc_bici: -0.02,
      asc_caminata: 0.4,
      b_tiempo_viaje: -0.015,
      b_costo: -0.0005625,
      b_tiempo_espera: -0.03,
      b_tiempo_caminata: -0.0255,
      penalizaciones_fisicas: {
        bici_10: -0.03,
        bici_20: -0.05,
        bici_30: -0.2,
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
    // 2000: NO es un precio de lista sino un costo ESPERADO (el modelo se lo
    // cobra a todos los viajes en auto, cuando en la realidad buena parte
    // estaciona gratis). Bajó de 4000 al recalibrar el valor del tiempo: con
    // VoT 6.200 $/h, 4000 valían 39 minutos y hundían el auto a 5.7%. Ver el
    // comentario del core.
    costo_parking: 2000,
    // 1 = flota de referencia. Escala la curva COPERT; ver core config.py.
    factor_flota_auto: 1,
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
    // 1800 hab/km = preset «Base» del repo (≈ 180 hogares por cuadra de 100 m);
    // población = 1800 × 20 km = 36.000. Con la escala anterior (500) el corredor
    // operaba a v/c 0.27 y la oferta de auto no movía el equilibrio — ver
    // docs/ANALISIS_SENSIBILIDAD.md S-03 y scripts/sensibilidad.py del core.
    densidad_hab_km: 1800,
    pendiente_porcentaje: 0,
    teletrabajo_factor: 1,
    share_estratos: [0.2, 0.5, 0.3],
  },
  supply: {
    bike: {
      v_media_kmh: 14,
      // 2500 bici/h = flujo de saturación realista; con 800 el modo operaba
      // sobre el techo de caminata (v/c 1.96) y su BPR quedaba inerte.
      capacidad_pista: 2500,
      alpha_bpr: 0.5,
      beta_bpr: 2,
    },
    car: {
      v_max_kmh: 31,
      ancho_pista_m: 3.5,
      largo_vehiculo_m: 5,
      gap_m: 2,
      // 2 => v/c ~1.05. Con 3 (v/c 0.71) la oferta vial quedaba muerta como
      // palanca: la BPR es plana bajo capacidad. Ver el comentario del core.
      num_pistas: 2,
      alpha_bpr: 0.8,
      beta_bpr: 2,
      // null = Greenshields (capacidad acoplada a la velocidad); manual = S-04.
      capacidad_pista: null,
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
      tiempo_detencion_min: 0.5,
      // Rango realista de metro: ~10 min (valle) a ~2 min (punta) de intervalo.
      // El rango amplio fortalece el efecto Mohring (ver DISCREPANCIES D-18).
      frec_min: 6,
      // 40 (antes 30): con 30 la frecuencia quedaba topada y el efecto Mohring
      // agotado en el default. Con 40 queda interior y responde a la demanda.
      frec_max: 40,
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
  // El frontend usa asignación por FLUJOS ESPERADOS (nₐ·prob) en vez de la
  // multinomial Monte Carlo del core: con 201 celdas y demanda baja por celda,
  // el muestreo entero produce perfiles de demanda "dentados" (ruido de
  // muestreo). La esperada es determinista y continua — mejor para la lectura
  // pedagógica de las figuras. Sigue disponible "montecarlo" en el toggle.
  assignment: "expected",
  modos_habilitados: ["Auto", "Metro", "Bici", "Caminata"],
};

export const defaultLandUseConfig: LandUseConfig = {
  // ΣH = 36.000 = 1800 hab/km × 20 km (la «densidad media» default de la UI;
  // shares 20/50/30). En sync con city.share_estratos — la app puebla desde acá.
  H_por_estrato: [7200, 18000, 10800],
  // VESTIGIAL: la densidad por celda ahora es S/Δx (consecuencia de la oferta);
  // estos campos ya no fijan la densidad. Se conservan por compat de
  // serialización. La escala de población la fija H_por_estrato (UI: «densidad media»).
  densidad_max: 800,
  densidad_min: 200,
  // Unidades físicas (D-26/D-27): α en utiles/min, ρ en utiles/(hogar/km),
  // y en $/mes. Calibración equivalente a la antigua en 201 celdas / 20 km.
  estratos: [
    { y: 3_500_000, lambda: 1, alpha: 6.5, rho: 0.1 },
    { y: 1_500_000, lambda: 1, alpha: 6.0, rho: 0.1 },
    { y: 500_000, lambda: 1, alpha: 5.5, rho: 0.1 },
  ],
  beta: 1,
  tol: 1e-8,
  max_iter: 2000,
  forma: "normal",
  oferta_sigma_frac: 0.5,
  forma_param: 0.5,
};
