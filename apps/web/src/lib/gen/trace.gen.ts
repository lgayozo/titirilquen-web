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
  tiempo_medio_min: number;
  costo_generalizado_percibido_clp: number;
  costo_generalizado_social_clp: number;
  vot_por_estrato_clp_hora: Record<"1" | "2" | "3", number>;
  logsum_por_estrato: Record<"1" | "2" | "3", number>;
  excedente_por_estrato_clp: Record<"1" | "2" | "3", number>;
  util_maxima_por_estrato: Record<"1" | "2" | "3", number>;
  excedente_max_por_estrato_clp: Record<"1" | "2" | "3", number>;
  viajeros_por_estrato: Record<"1" | "2" | "3", number>;
  excedente_total_clp: number;
  excedente_max_total_clp: number;
  medida_bienestar: "logsum" | "utilidad_maxima";
  recaudacion_parking_clp: number;
  recaudacion_tarifa_clp: number;
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
  t_tren_acceso: number[];
  t_tren_espera: number[];
  t_tren_viaje: number[];
  frecuencia_metro: number;
  frecuencia_teorica_metro: number;
  /** `None` en la primera iteración, donde el residuo es infinito. */
  residuo: number | null;
}

/** Resultado completo de una corrida de transporte. */
export interface TraceDict {
  converged: boolean;
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
  result: LandUseResultDict;
}

/** Indicadores de un estrato (un "tipo de usuario") en el equilibrio final. */
export interface StratumMetrics {
  /** 1 = alto, 2 = medio, 3 = bajo. */
  estrato: number;
  /** Hogares del estrato (Σ_i S_i·Q[h,i] ≈ H_h). */
  n_hogares: number;
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
   *  Δ excedente del consumidor vs la **red vacía** ((logsum − logsum_0) /
   *  −b_costo), en $. Δ<0 ⇒ costo neto de la congestión; Δ>0 ⇒ domina el efecto
   *  Mohring (frecuencia endógena). Eficiencia/DAP, NO bienestar interpersonal
   *  — ver módulo docstring.
   */
  delta_excedente_clp: number;
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
  /** Residuo ||ΔT||_∞ de la última iteración (min); None si no medible. */
  residual_final_min: number | null;
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
   *  Σ_h n_hogares_h · ΔCS_h ($). Efecto agregado de bienestar de la demanda
   *  sobre la red (congestión vs Mohring), respecto a la red vacía.
   */
  delta_bienestar_total_clp: number;
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
