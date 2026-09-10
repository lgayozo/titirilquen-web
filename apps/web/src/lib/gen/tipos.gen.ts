// GENERADO por packages/titirilquen_core/tools/genera_contrato.py — NO EDITAR.
// Para cambiar algo de acá, cambiá el núcleo Python y corré `npm run sync:core`.

/** Los tres estratos socioeconómicos. */
export type StratumId = 1 | 2 | 3;

export interface BikeSupplyParams {
  v_media_kmh: number;
  capacidad_pista: number;
  alpha_bpr: number;
  beta_bpr: number;
}

export interface CarSupplyParams {
  v_max_kmh: number;
  ancho_pista_m: number;
  largo_vehiculo_m: number;
  gap_m: number;
  num_pistas: number;
  alpha_bpr: number;
  beta_bpr: number;
  capacidad_pista: number | null;
}

/**
 *  Ciudad lineal: la geometría y nada más. Tres números. `n_celdas` es la
 *  resolución numérica (impar, para que el CBD sea una celda y su centroide
 *  caiga en L/2); `largo_ciudad_km` el tamaño físico; `pendiente_porcentaje`
 *  el terreno, que sólo ve la bicicleta. Hasta sep-2026 traía además
 *  `densidad_hab_km`, `share_estratos` y `teletrabajo_factor`. Los dos
 *  primeros eran la fuente de población de la ruta «transporte solo», que
 *  dejó de existir: la población viene SIEMPRE del uso de suelo
 *  (`LandUseConfig.H_por_estrato` sobre la oferta `S`), así que eran inertes
 *  por la ruta de la app y el schema afirmaba «población = densidad × largo»
 *  sin condición (D-46). El tercero es una palanca de demanda y vive ahora en
 *  `GlobalConfig`. La densidad media es una CONSECUENCIA, ΣH / largo, y así
 *  se reporta.
 */
export interface CityConfig {
  n_celdas: number;
  largo_ciudad_km: number;
  pendiente_porcentaje: number;
}

export interface DemandConfig {
  globales: GlobalConfig;
  estratos: Record<StratumId, StratumConfig>;
}

export interface GlobalConfig {
  v_auto: number;
  v_metro: number;
  v_bici: number;
  v_caminata: number;
  corte_caminata_min: number;
  corte_bici_min: number;
  costo_combustible_km: number;
  costo_tarifa_metro: number;
  costo_parking: number;
  factor_flota_auto: number;
  factor_emision_metro_tren_km: number;
  teletrabajo_factor: number;
}

/**
 *  Penalizaciones aditivas escalonadas (step) para bici y caminata. Ver
 *  docs/DISCREPANCIES.md (D-02) — estas son constantes aditivas, no
 *  multiplicativas como sugiere el Overleaf.
 */
export interface PhysicalPenalties {
  bici_10: number;
  bici_20: number;
  bici_30: number;
  walk_5: number;
  walk_15: number;
  walk_25: number;
}

/** Coeficientes del logit multinomial por estrato. */
export interface StratumBetas {
  asc_auto: number;
  asc_metro: number;
  asc_bici: number;
  asc_caminata: number;
  /** Desutilidad del tiempo en vehículo (utiles/min); negativo */
  b_tiempo_viaje: number;
  /** Desutilidad del dinero (utiles/$); negativo. Es λ en el suelo (D-34) */
  b_costo: number;
  b_tiempo_espera: number;
  b_tiempo_acceso: number;
  b_tiempo_caminata: number;
  penalizaciones_fisicas: PhysicalPenalties;
}

/**
 *  Configuración por estrato: quién es y cómo valora el viaje. Tuvo también
 *  `prob_jornada_flexible`, `prob_part_time` y una `jornada` con horas por
 *  tipo de contrato. Se retiraron en la limpieza de agosto de 2026: ningún
 *  módulo del núcleo los leía (D-07 ya lo declaraba: "sólo afectan metadatos
 *  de agentes"), y ni siquiera eso — `Agente` no tiene campos de jornada.
 *  Eran ocho números por estrato que el frontend mostraba y nadie usaba. Si
 *  algún día la jornada entra al modelo, entra con su ecuación.
 */
export interface StratumConfig {
  prob_teletrabajo: number;
  prob_auto: number;
  betas: StratumBetas;
}

export interface SupplyConfig {
  bike: BikeSupplyParams;
  car: CarSupplyParams;
  train: TrainSupplyParams;
}

export interface TrainSupplyParams {
  v_tren_kmh: number;
  capacidad_tren: number;
  num_estaciones: number;
  v_caminata_kmh: number;
  costo_operacion_tren_km: number;
  factor_dia_punta: number;
  tiempo_detencion_min: number;
  frec_min: number;
  frec_max: number;
  /**
   *  α de la BPR de congestión de andén: t_espera = base·(1 + α·ρ^β), ρ =
   *  carga/(frec_max·K)
   */
  anden_alpha: number;
  /** β de la BPR de congestión de andén */
  anden_beta: number;
}

/**
 *  Configuración completa de una corrida del simulador — el objeto que se
 *  serializa al archivo `.ttrq.json`.
 */
export interface SimulationConfig {
  city: CityConfig;
  supply: SupplyConfig;
  demand: DemandConfig;
  max_iter: number;
  tolerance: number;
  seed: number | null;
  /**
   *  Método de asignación de demanda. 'montecarlo' sortea el modo de cada
   *  agente; 'expected' usa los flujos esperados = probabilidades logit (el
   *  mismo modelo sin ruido de muestreo); 'todo_o_nada' manda al grupo ENTERO
   *  al modo de mayor utilidad. Los tres son el mismo modelo de utilidad
   *  aleatoria: 'todo_o_nada' es el límite del logit cuando la escala de los
   *  coeficientes crece, o sea con varianza cero en la parte no observada. NO
   *  produce igualación de costos entre modos — medido en
   *  scripts/auditoria_wardrop.py: los cuatro modos se usan a la vez con costos
   *  que difieren hasta 32 min. Lo que cambia es que el grupo marginal salta
   *  entero en vez de trasvasar una fracción, y de ahí que sólo con este método
   *  aparezca Downs-Thomson (docs/CONTINUAR.md §5). Se llamó 'wardrop' hasta
   *  agosto de 2026; el nombre prometía una condición de equilibrio de usuario
   *  que este modelo no cumple.
   */
  assignment: "montecarlo" | "expected" | "todo_o_nada";
  /**
   *  Modos disponibles en el set de elección. Los modos excluidos se tratan
   *  como infeasibles (utilidad −∞) y no reciben demanda. Útil para escenarios
   *  estilizados (p.ej. solo Auto vs Metro).
   */
  modos_habilitados: ("Auto" | "Metro" | "Bici" | "Caminata")[];
}

/**
 *  Parámetros de la función de puje (bid function) por estrato. **Unidades
 *  (D-26/D-27/D-34)**: `T` es el logsum mensual de transporte (utiles de
 *  transporte por mes) y la densidad va en hogares/km; `alpha` es
 *  adimensional (1 = la accesibilidad tal cual), `rho` en utiles-mes por
 *  (hogar/km) y `lambda` en utiles por peso (= |b_costo| de transporte), con
 *  lo que el score queda en $/mes. `y` está en $/mes (CLP); no mueve la
 *  asignación (se absorbe en ū, ver D-08) pero sí la métrica de carga mensual
 *  costo/ingreso del acoplado.
 */
export interface LandUseStratumConfig {
  /** Ingreso mensual del estrato ($/mes) */
  y: number;
  /** Utilidad marginal del ingreso (λ_h) */
  lambda: number;
  /**
   *  Multiplicador de la accesibilidad (logsum mensual de transporte); 1 = tal
   *  cual
   */
  alpha: number;
  /** Penalización de densidad (utiles de transporte por mes, por hogar/km) */
  rho: number;
}

/** Configuración del módulo de uso de suelo. */
export interface LandUseConfig {
  /** Número de hogares por estrato (alto, medio, bajo) */
  H_por_estrato: [number, number, number];
  /**
   *  Parámetros de puja de los tres estratos (alto, medio, bajo). Son la
   *  palanca principal del módulo: `alpha` es común y la diferencia de `lambda`
   *  entre estratos fija el valor del tiempo `alpha/lambda` de cada uno, que es
   *  lo que produce el gradiente de Alonso.
   */
  estratos: [LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig];
  /**
   *  Nitidez de la subasta: escala del ruido de la puja = 1/(beta·lambda). 1 =
   *  el ruido de un viaje; 0,15 ≈ 1/√44 = ruido acumulado en el mes
   */
  beta: number;
  tol: number;
  max_iter: number;
  /**
   *  Forma del perfil de oferta de vivienda a lo largo del corredor: normal ·
   *  uniforme · exponencial · meseta · bimodal · valle.
   */
  forma: "normal" | "uniforme" | "exponencial" | "meseta" | "bimodal" | "valle";
  /**
   *  Ancho/dispersión de la oferta como fracción de la semi-ciudad: σ = frac ·
   *  min(CBD, L-1-CBD). Menor ⇒ ciudad compacta (vivienda junto al CBD); mayor
   *  ⇒ dispersa. También controla la pendiente de la exponencial y el ancho de
   *  los picos (bimodal). Default 0.5 = σ ≈ L/4.
   */
  oferta_sigma_frac: number;
  /**
   *  2º parámetro de la forma, como fracción de la semi-ciudad: separación de
   *  los picos (bimodal). Ignorado en las demás formas.
   */
  forma_param: number;
}
