/**
 * Tipos espejo de los esquemas Pydantic de `titirilquen_core/config.py`.
 *
 * TODO (fase posterior): reemplazar por generación automática vía
 * `datamodel-codegen` o `pydantic-to-typescript` en el package shared-types.
 */

export type StratumId = 1 | 2 | 3;
export type Modo = "Auto" | "Metro" | "Bici" | "Caminata" | "Teletrabajo";

export interface PhysicalPenalties {
  bici_10: number;
  bici_20: number;
  bici_30: number;
  walk_5: number;
  walk_15: number;
  walk_25: number;
}

export interface StratumBetas {
  asc_auto: number;
  asc_metro: number;
  asc_bici: number;
  asc_caminata: number;
  b_tiempo_viaje: number;
  b_costo: number;
  b_tiempo_espera: number;
  b_tiempo_caminata: number;
  penalizaciones_fisicas: PhysicalPenalties;
}

export interface StratumConfig {
  prob_teletrabajo: number;
  prob_auto: number;
  prob_jornada_flexible?: number;
  prob_part_time?: number;
  jornada?: { horas_rigido: number; horas_flexible: number; horas_part_time: number };
  betas: StratumBetas;
}

export interface GlobalConfig {
  v_auto: number;
  v_metro: number;
  v_bici: number;
  v_caminata: number;
  costo_combustible_km: number;
  costo_tarifa_metro: number;
  costo_parking: number;
  factor_emision_auto: number;
  factor_emision_metro: number;
}

export interface DemandConfig {
  globales: GlobalConfig;
  estratos: Record<StratumId, StratumConfig>;
}

export interface CityConfig {
  n_celdas: number;
  largo_ciudad_km: number;
  densidad_por_celda: number;
  pendiente_porcentaje: number;
  teletrabajo_factor: number;
  share_estratos: [number, number, number];
  ingresos_estratos: [number, number, number];
}

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
}

export interface TrainSupplyParams {
  v_tren_kmh: number;
  capacidad_tren: number;
  num_estaciones: number;
  v_caminata_kmh: number;
  tasa_carga: number;
  frec_min: number;
  frec_max: number;
}

export interface SupplyConfig {
  bike: BikeSupplyParams;
  car: CarSupplyParams;
  train: TrainSupplyParams;
}

export interface SimulationConfig {
  city: CityConfig;
  supply: SupplyConfig;
  demand: DemandConfig;
  max_iter: number;
  tolerance: number;
  seed: number | null;
}

export interface IterationSnapshot {
  iter: number;
  f_msa: number;
  modal_split: Record<string, number>;
  t_auto: number[];
  t_bici: number[];
  t_tren_acceso: number[];
  t_tren_espera: number[];
  t_tren_viaje: number[];
  demanda_auto: number[];
  demanda_metro: number[];
  demanda_bici: number[];
  frecuencia_metro: number;
  residuo: number | null;
}

export interface AgentRecord {
  id: number;
  celda_origen: number;
  estrato: StratumId;
  teletrabaja: boolean;
  tiene_auto: boolean;
  modo_elegido: Modo | null;
  utilidad_elegida: number;
}

export interface SimulationResult {
  converged: boolean;
  capacidad_auto: number;
  v_libre_auto: number;
  alpha_auto_bpr: number;
  beta_auto_bpr: number;
  carga_metro: number[] | null;
  estaciones_km: number[] | null;
  iteraciones: IterationSnapshot[];
  agentes: AgentRecord[];
}
