// GENERADO por packages/titirilquen_core/tools/genera_contrato.py — NO EDITAR.
// Para cambiar algo de acá, cambiá el núcleo Python y corré `npm run sync:core`.

// La forma de los resultados que el núcleo entrega al frontend, sea por
// HTTP (FastAPI) o por postMessage (worker de Pyodide). Fuente: los
// TypedDict de titirilquen_core/serializacion.py y las dataclasses de
// coupled_metrics.py, que se serializan con asdict().

/** Un viajero, tal como lo ve el frontend. */
export interface AgenteDict {
  id: number;
  celda_origen: number;
  estrato: number;
  teletrabaja: boolean;
  tiene_auto: boolean;
  /** `None` para un agente varado: ninguno de sus modos resultó factible. */
  modo_elegido: "Auto" | "Metro" | "Bici" | "Caminata" | "Teletrabajo" | null;
  /** Nunca falta — arranca en 0.0 y el teletrabajador se queda en 0.0. */
  utilidad_elegida: number;
}

/** Indicadores de ciudad completa para la tabla de resultados. */
export interface AgregadosDict {
  tiempo_total_min: number;
  viajeros: number;
  varados: number;
  viajes_por_modo: Record<string, number>;
  viajes_por_modo_estrato: Record<"1" | "2" | "3", Record<string, number>>;
  tiempo_medio_min: number;
  tiempo_medio_por_modo_min: Record<string, number>;
  tiempo_medio_por_estrato_min: Record<"1" | "2" | "3", number>;
  costo_generalizado_percibido_clp: number;
  costo_generalizado_social_clp: number;
  recursos_tiempo_clp: number;
  auto_km_hora: number;
  litros_combustible_hora: number;
  recursos_combustible_clp: number;
  pago_combustible_clp: number;
  recursos_otros_operacion_clp: number;
  costo_co2_clp: number;
  inversion_capital_clp: number;
  costo_inversion_clp: number;
  costo_recursos_clp: number;
  vot_por_estrato_clp_hora: Record<"1" | "2" | "3", number>;
  logsum_por_estrato: Record<"1" | "2" | "3", number>;
  excedente_por_estrato_clp: Record<"1" | "2" | "3", number>;
  excedente_social_por_estrato_clp: Record<"1" | "2" | "3", number>;
  excedente_social_total_clp: number;
  viajeros_por_estrato: Record<"1" | "2" | "3", number>;
  excedente_total_clp: number;
  recaudacion_parking_clp: number;
  recaudacion_peaje_clp: number;
  recaudacion_tarifa_clp: number;
  recaudacion_combustible_clp: number;
  tren_km_hora: number;
  costo_operador_clp: number;
  subsidio_metro_clp: number;
  bienestar_social_clp: number;
}

/** Estado de la red al final de una iteración del MSA. */
export interface SnapshotDict {
  iter: number;
  f_msa: number;
  modal_split: Record<string, number>;
  demanda_auto: number[];
  demanda_metro: number[];
  demanda_bici: number[];
  demanda_caminata: number[];
  t_auto: number[];
  t_bici: number[];
  /** Red vacía: sobre este tiempo se evalúan los escalones de la bici (D9). */
  t_bici_libre: number[];
  t_tren_acceso: number[];
  t_tren_espera: number[];
  t_tren_viaje: number[];
  frecuencia_metro: number;
  frecuencia_teorica_metro: number;
  /**
   *  Brecha no amortiguada de la iteración, `max |c(x(t)) − t|` en min (D8).
   *  `None` en la primera iteración, donde es infinita.
   */
  residuo: number | null;
}

/** Resultado completo de una corrida de transporte. */
export interface TraceDict {
  /**
   *  `residuo < tolerance` dos veces seguidas, con `residuo` la brecha no
   *  amortiguada (D8; hasta entonces era el cambio amortiguado, ver D-39).
   */
  converged: boolean;
  /**
   *  Brecha no amortiguada del estado final (min). Es la cifra que acota cuán
   *  lejos del punto fijo quedó la corrida.
   */
  gap_final_min: number;
  capacidad_auto: number;
  v_libre_auto: number;
  alpha_auto_bpr: number;
  beta_auto_bpr: number;
  carga_metro: number[] | null;
  estaciones_km: number[] | null;
  flujos_auto_veh_h: number[] | null;
  flujos_bici_veh_h: number[] | null;
  emisiones_total_kg: number;
  emisiones_auto_kg: number;
  emisiones_metro_kg: number;
  emisiones_perfil_kg: number[] | null;
  /**
   *  Demanda esperada por [estrato, modo, celda] — el cubo que alimenta el
   *  reparto modal espacial por estrato y los agregados de bienestar.
   */
  demanda_estrato: number[][][] | null;
  /**
   *  La `Q[estrato, celda]` con que se pobló la ciudad. Comparar la reenvía
   *  como `Q_dada` para correr otra política con la misma gente (D11c).
   */
  localizacion_Q: number[][] | null;
  iteraciones: SnapshotDict[];
  agentes: AgenteDict[];
  /**
   *  Indicadores de bienestar de la ciudad completa. `None` cuando se serializa
   *  sin la configuración (no se pueden calcular sin ella).
   */
  agregados: AgregadosDict | null;
}

/** Equilibrio de pujas: utilidades, precios y composición por celda. */
export interface LandUseResultDict {
  u: number[];
  p: number[];
  Q: number[][];
  converged: boolean;
  iterations: number;
}

/** Respuesta de resolver el uso de suelo aislado (con su geometría). */
export interface LandUseSolveDict {
  L: number;
  CBD: number;
  S: number[];
  /** Por celda, cuántos hogares de cada estrato quedaron asignados. */
  parcelas: number[][];
  /**
   *  Densidad por celda (hab/km) = S_i/Δx: es CONSECUENCIA de la oferta, no un
   *  parámetro. 0 donde no hay oferta.
   */
  densidad_celda: number[];
  /**
   *  Segregación de Theil POBLACIONAL (N = S·Q), calculada en el núcleo (D-38).
   *  El frontend la muestra; ya no la recalcula sobre Q.
   */
  theil: number;
  /**
   *  Distancia media al CBD por estrato (alto, medio, bajo), ponderada por los
   *  hogares ESPERADOS `S_i·Q_hi` (D-44). La asignación entera `parcelas` es
   *  una realización aleatoria: sirve para dibujar, no para comparar cifras.
   */
  dist_media_km: number[];
  result: LandUseResultDict;
}

/** Indicadores de un estrato (un "tipo de usuario") en el equilibrio final. */
export interface StratumMetrics {
  /** 1 = alto, 2 = medio, 3 = bajo. */
  estrato: number;
  /** Hogares del estrato (Σ_i S_i·Q[h,i] ≈ H_h). */
  n_hogares: number;
  /**
   *  Agentes del estrato que viajan (sin teletrabajo ni varados). Es la
   *  población sobre la que están promediados `tiempo_medio_min` y
   *  `costo_medio_clp`.
   */
  n_viajeros: number;
  /** Distancia media de residencia al CBD, ponderada por hogares (km). */
  dist_media_cbd_km: number;
  /** Tiempo de viaje medio de los agentes que viajan (min). */
  tiempo_medio_min: number;
  /** Share por categoría (Auto/Metro/Bici/Caminata/Teletrabajo/Varado); suma 1. */
  reparto_modal: Record<
    "Auto" | "Metro" | "Bici" | "Caminata" | "Teletrabajo" | "Varado",
    number
  >;
  /** Costo monetario medio del viaje, sobre los que viajan ($). */
  costo_medio_clp: number;
  /**
   *  Δ excedente del consumidor vs la **red vacía**, en $/hogar-mes:
   *  VIAJES_MES·(logsum − logsum_0)/−b_costo por cada hogar que viaja, 0 por
   *  cada hogar que teletrabaja, promediado sobre ambos (los varados quedan
   *  fuera: no tienen medida). Hasta oct-2026 era $/viaje promediado sólo sobre
   *  los que viajan (D11). Δ<0 ⇒ costo neto de la congestión; Δ>0 ⇒ domina el
   *  efecto Mohring (frecuencia endógena). Eficiencia/DAP, NO bienestar
   *  interpersonal, y sin rentas — ver módulo docstring.
   */
  delta_excedente_hogar_mes_clp: number;
  /**
   *  **Nivel** del excedente, en $/hogar-mes: VIAJES_MES·logsum/−b_costo, con
   *  el mismo denominador y la misma medida que
   *  `delta_excedente_hogar_mes_clp`. Su cero lo fijan las ASC: no se lee solo.
   *  Existe para restarlo entre DOS escenarios, que es el cambio de bienestar
   *  entre ellos; el Δ contra la red vacía no sirve para eso, porque los
   *  precios se cancelan dentro de él. Ver módulo docstring.
   */
  excedente_hogar_mes_clp: number;
  /**
   *  Carga **mensual**: (costo medio por viaje · 44 viajes/mes) / ingreso
   *  mensual del estrato ($/mes). Fracción interpretable (~0.02–0.30) — antes
   *  mezclaba costo por viaje en $ con un ingreso adimensional (D-27).
   */
  carga_costo_ingreso: number;
}

/** Indicadores del equilibrio agregado (todo el sistema). */
export interface SystemMetrics {
  /** ¿El loop suelo↔transporte alcanzó `outer_tol`? */
  convergio_exterior: boolean;
  iteraciones_exteriores: number;
  /**
   *  Brecha del loop exterior en la última iteración, `max_h |T_new − T|/λ_h`
   *  en $/hogar-mes (D10); None si no es medible (la primera iteración). Hasta
   *  oct-2026 iba en utiles de transporte por mes.
   */
  residual_final: number | null;
  /** ¿Convergió el MSA interior de la última corrida de transporte? */
  convergio_msa: boolean;
  /** Σ sobre agentes del tiempo de viaje (pax·min). */
  tiempo_total_pax_min: number;
  /** Tiempo de viaje medio del sistema (min). */
  tiempo_medio_min: number;
  /** Reparto modal global (mismas categorías que por estrato; suma 1). */
  reparto_modal: Record<
    "Auto" | "Metro" | "Bici" | "Caminata" | "Teletrabajo" | "Varado",
    number
  >;
  /** Frecuencia operativa del metro en el equilibrio (trenes/h). */
  frecuencia_metro: number;
  emisiones_total_kg: number;
  emisiones_auto_kg: number;
  emisiones_metro_kg: number;
  /** Índice H de Theil sobre Q ∈ [0,1]. 0 = integrada, 1 = segregación total. */
  segregacion_theil: number;
  /**
   *  Σ sobre los hogares de ΔCS mensual ($/mes) — D-35, D11. Efecto agregado de
   *  bienestar de la demanda sobre la red (congestión vs Mohring), respecto a
   *  la red vacía. Sólo transporte: cota inferior en el sentido de Martínez p.
   *  264.
   */
  delta_bienestar_total_mes_clp: number;
  /**
   *  **Nivel** del excedente de la ciudad, en $/mes: la misma suma que
   *  `delta_bienestar_total_mes_clp` sin restar la red vacía. Sólo su
   *  diferencia con otro escenario es interpretable, y sólo si comparten β,
   *  modos habilitados y teletrabajo (ver `excedente_hogar_mes_clp`).
   */
  excedente_total_mes_clp: number;
  /** Tiempo medio bajo / alto. >1 ⇒ los pobres viajan más (regresivo). */
  ratio_tiempo_bajo_alto: number | null;
  /** Carga (costo/ingreso) bajo / alto. >1 ⇒ el transporte pesa más al pobre. */
  ratio_carga_bajo_alto: number | null;
}

/** Reporte completo del equilibrio de Ciudad en equilibrio. */
export interface EquilibriumMetrics {
  por_estrato: StratumMetrics[];
  sistema: SystemMetrics;
}

/** Una vuelta del loop exterior suelo ↔ transporte. */
export interface OuterIterationDict {
  outer_iter: number;
  land_use: LandUseResultDict;
  transport: TraceDict;
  T_matrix: number[][];
  T_residual: number | null;
  /**
   *  Los indicadores del equilibrio. El alias es `dict[str, Any]`, así que del
   *  lado TypeScript el tipo se restituye desde las dataclasses de
   *  `coupled_metrics` — ver `TIPOS_RESTITUIDOS` en el generador.
   */
  metrics: EquilibriumMetrics;
}

/** Resultado completo del loop acoplado. */
export interface CoupledResultDict {
  converged: boolean;
  iterations: OuterIterationDict[];
  final_parcelas: number[][];
  S: number[] | null;
}

/** Lo que resume una ventana de días. */
export interface VentanaDict {
  desde: number;
  hasta: number;
  s: number;
  phi: number;
  invertidos: number;
}

/** Los tres horizontes de análisis. */
export interface VentanasDict {
  corto: VentanaDict;
  medio: VentanaDict;
  largo: VentanaDict;
}

/** El caso binario del que salió el experimento. */
export interface CasoDict {
  estrato: number;
  celda: number;
  modos: string[];
  mejor: string;
  tau: number[];
  v_ref: number[];
  beta: number;
  dv: number;
  ventaja_min: number;
  p_verdadera: number;
  margen_phi: number;
}

/** El umbral analítico y su contraste con la simulación. Sólo con tratamiento. */
export interface ShockDict {
  w_k: number;
  delta_critico_min: number;
  p_post_analitica: number;
  p_post_simulada: number | null;
  llegan_a_k: number;
}

/** Los tiempos de UNA celda, tal como los trae el snapshot del equilibrio. */
export interface TiemposCeldaDict {
  auto_total: number;
  bici_total: number;
  bici_libre: number;
  tren_acceso: number;
  tren_espera: number;
  tren_viaje: number;
}

/** El resultado completo de un experimento de una persona. */
export interface AprendizajeDict {
  caso: CasoDict;
  dias: number;
  replicas: number;
  ventanas: VentanasDict;
  s_por_dia: number[];
  p_replicas: number[][];
  shock: ShockDict | null;
}

/** Lo que la interfaz necesita saber de un escenario ya preparado. */
export interface EscenarioResumenDict {
  clave: string;
  k_modos: number;
  n_agentes: number;
  eligen: number;
  modos: string[];
  split_equilibrio: number[];
}

/** Φ en los tres horizontes. */
export interface PhiVentanasDict {
  corto: number;
  medio: number;
  largo: number;
}

/** Un grupo de la población, separado por cuál es SU modo mejor. */
export interface GrupoDict {
  modo: string;
  n: number;
  lleva_ruido: boolean;
  p_estrella: number;
  uniforme: number;
  phi: PhiVentanasDict;
}

/** El resultado de un experimento sobre la ciudad. */
export interface CiudadDict {
  n_agentes: number;
  eligen: number;
  modos: string[];
  dias: number;
  escala: number;
  split_equilibrio: number[];
  split_ultimos: number[];
  split_por_dia: number[][];
  phi: PhiVentanasDict;
  por_mejor: GrupoDict[];
  dispersion_iguales: number;
  abandono_auto: number;
  abandono_metro: number;
  suerte_mala_auto: number;
  suerte_buena_auto: number;
  brecha_percepcion_min: number;
}
