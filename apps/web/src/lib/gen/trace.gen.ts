// GENERADO por packages/titirilquen_core/tools/genera_contrato.py — NO EDITAR.
// Para cambiar algo de acá, cambiá el núcleo Python y corré `npm run sync:core`.

// La forma de los resultados que el núcleo entrega al frontend, sea por
// HTTP (FastAPI) o por postMessage (worker de Pyodide). Fuente: los
// TypedDict de titirilquen_core/serializacion.py.

/** Un viajero, tal como lo ve el frontend. */
export interface AgenteDict {
  id: number;
  celda_origen: number;
  estrato: number;
  teletrabaja: boolean;
  tiene_auto: boolean;
  modo_elegido: "Auto" | "Metro" | "Bici" | "Caminata" | "Teletrabajo" | null;
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
  viajeros_por_estrato: Record<"1" | "2" | "3", number>;
  excedente_total_clp: number;
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
  demanda_estrato: number[][][] | null;
  iteraciones: SnapshotDict[];
  agentes: AgenteDict[];
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
  parcelas: unknown;
  densidad_celda: number[];
  result: LandUseResultDict;
}

/** Una vuelta del loop exterior suelo ↔ transporte. */
export interface OuterIterationDict {
  outer_iter: number;
  land_use: LandUseResultDict;
  transport: TraceDict;
  T_matrix: number[][];
  T_residual: number | null;
  metrics: Record<string, unknown>;
}

/** Resultado completo del loop acoplado. */
export interface CoupledResultDict {
  converged: boolean;
  iterations: OuterIterationDict[];
  final_parcelas: unknown;
  S: number[] | null;
}
