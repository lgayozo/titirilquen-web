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
  solver: "heteroscedastic" | "logit" | "frechet";
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

export interface OuterIteration {
  outer_iter: number;
  land_use: LandUseResult;
  transport: SimulationResult;
  T_matrix: number[][];
  T_residual: number | null;
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
