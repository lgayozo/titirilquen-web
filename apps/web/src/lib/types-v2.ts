/**
 * Tipos V2 — uso de suelo + loop acoplado suelo↔transporte.
 * Espejo de los esquemas Pydantic en `titirilquen_core.land_use` y
 * `titirilquen_core.coupled`.
 */

import type { SimulationConfig, SimulationResult } from "@/lib/types";

export interface LandUseStratumConfig {
  y: number;
  lambda: number;
  alpha: number;
  rho: number;
}

export type FormaOferta =
  | "normal"
  | "uniforme"
  | "exponencial"
  | "meseta"
  | "bimodal"
  | "valle";

export interface LandUseConfig {
  H_por_estrato: [number, number, number];
  estratos: [LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig];
  beta: number;
  solver: "heteroscedastic" | "logit";
  tol: number;
  max_iter: number;
  /** Forma del perfil de oferta de vivienda a lo largo del corredor. */
  forma: FormaOferta;
  /** Ancho/dispersión de la oferta (σ como fracción de la semi‑ciudad).
   *  Menor ⇒ ciudad compacta; mayor ⇒ dispersa. Default 0.5. */
  oferta_sigma_frac: number;
  /** 2º parámetro de la forma (fracción de la semi‑ciudad): radio del anillo
   *  (anular) o separación de picos (bimodal). Ignorado en las demás. */
  forma_param: number;
}

export interface LandUseResult {
  u: number[];
  p: number[];
  Q: number[][];
  converged: boolean;
  iterations: number;
}

export interface LandUseSolveResponse {
  L: number;
  CBD: number;
  S: number[];
  parcelas: number[][];
  result: LandUseResult;
}

/** Categorías del reparto modal reportadas por estrato y sistema (suman 1). */
export interface RepartoModal {
  Auto: number;
  Metro: number;
  Bici: number;
  Caminata: number;
  Teletrabajo: number;
  Varado: number;
}

/** Métricas de un estrato ("tipo de usuario") en el equilibrio. */
export interface StratumMetrics {
  estrato: number;
  n_hogares: number;
  dist_media_cbd_km: number;
  tiempo_medio_min: number;
  reparto_modal: RepartoModal;
  costo_medio_clp: number;
  /** Excedente del consumidor de transporte (logsum / −b_costo), en $.
   *  Eficiencia/DAP, NO bienestar interpersonal (b_costo varía por estrato). */
  excedente_consumidor_clp: number;
  /** Costo de transporte / ingreso del estrato. Lente de equidad. */
  carga_costo_ingreso: number;
}

/** Métricas del equilibrio agregado (todo el sistema). */
export interface SystemMetrics {
  convergio_exterior: boolean;
  iteraciones_exteriores: number;
  residual_final_min: number | null;
  convergio_msa: boolean;
  tiempo_total_pax_min: number;
  tiempo_medio_min: number;
  reparto_modal: RepartoModal;
  frecuencia_metro: number;
  emisiones_total_kg: number;
  emisiones_auto_kg: number;
  emisiones_metro_kg: number;
  segregacion_theil: number;
  bienestar_total_clp: number;
  ratio_tiempo_bajo_alto: number | null;
  ratio_carga_bajo_alto: number | null;
}

export interface EquilibriumMetrics {
  por_estrato: StratumMetrics[];
  sistema: SystemMetrics;
}

export interface OuterIteration {
  outer_iter: number;
  land_use: LandUseResult;
  transport: SimulationResult;
  T_matrix: number[][];
  T_residual: number | null;
  metrics: EquilibriumMetrics;
}

export interface CoupledResult {
  converged: boolean;
  iterations: OuterIteration[];
  final_parcelas: number[][];
  S: number[] | null;
}

export interface CoupledRequest {
  sim: SimulationConfig;
  land_use: LandUseConfig;
  outer_max_iter: number;
  outer_tol: number;
}
