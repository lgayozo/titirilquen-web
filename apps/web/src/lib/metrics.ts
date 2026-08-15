/**
 * Métricas de interdependencia suelo ↔ transporte.
 *
 * Tres indicadores agregados computados sobre cada iteración exterior del
 * loop acoplado. Permiten al estudiante ver el efecto de políticas de
 * transporte sobre la estructura social de la ciudad — cosa que las figuras
 * espaciales individuales no revelan directamente.
 */

import type { StratumId } from "@/lib/types";

// ---------------------------------------------------------------------------
// Segregación — índice H de Theil (información mutua relativa)
// ---------------------------------------------------------------------------

/**
 * Entropía de Shannon de una distribución de probabilidades (en nats).
 * Usa convención 0·log(0) = 0.
 */
function entropy(probs: readonly number[]): number {
  let e = 0;
  for (const p of probs) {
    if (p > 0) e -= p * Math.log(p);
  }
  return e;
}

/**
 * Índice de segregación H de Theil sobre la matriz Q (estratos × parcelas).
 * Q[h][i] es el número esperado de hogares de estrato `h` en la parcela `i`
 * (resultado del solver de uso de suelo).
 *
 * H = 1 − (Σ_i (N_i/N) · E_i) / E
 *
 * Donde E es la entropía global por estrato y E_i la entropía en cada parcela.
 *
 * @returns número en [0, 1]. 0 = ciudad integrada (cada parcela = mix global),
 *          1 = segregación perfecta (cada parcela es un solo estrato).
 */
export function theilSegregation(Q: readonly (readonly number[])[]): number {
  const H = Q.length;
  const L = Q[0]?.length ?? 0;
  if (H === 0 || L === 0) return 0;

  // Totales globales por estrato y por parcela.
  const totalPorEstrato = new Array<number>(H).fill(0);
  const totalPorParcela = new Array<number>(L).fill(0);
  let N = 0;
  for (let h = 0; h < H; h++) {
    const row = Q[h] ?? [];
    for (let i = 0; i < L; i++) {
      const v = row[i] ?? 0;
      totalPorEstrato[h]! += v;
      totalPorParcela[i]! += v;
      N += v;
    }
  }
  if (N <= 0) return 0;

  const globalShare = totalPorEstrato.map((x) => x / N);
  const E = entropy(globalShare);
  if (E === 0) return 0; // ciudad monoestrato

  let weighted = 0;
  for (let i = 0; i < L; i++) {
    const Ni = totalPorParcela[i] ?? 0;
    if (Ni <= 0) continue;
    const local = new Array<number>(H);
    for (let h = 0; h < H; h++) {
      local[h] = (Q[h]?.[i] ?? 0) / Ni;
    }
    weighted += (Ni / N) * entropy(local);
  }

  return 1 - weighted / E;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export const STRATUM_NAMES: Record<StratumId, string> = {
  1: "alto",
  2: "medio",
  3: "bajo",
};

/** Formato compacto de un delta con signo (para mostrar Δ entre iteraciones). */
export function formatDelta(curr: number | null, base: number | null): string {
  if (curr == null || base == null) return "—";
  const d = curr - base;
  const sign = d > 0 ? "+" : "";
  const abs = Math.abs(d);
  const fmt =
    abs >= 100 ? d.toFixed(0) : abs >= 1 ? d.toFixed(2) : d.toFixed(3);
  return `${sign}${fmt}`;
}
