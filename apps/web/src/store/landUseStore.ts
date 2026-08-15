import { create } from "zustand";

import { defaultLandUseConfig } from "@/lib/api-v2";
import type { SimulationConfig } from "@/lib/types";
import type {
  LandUseConfig,
  LandUseSolveResponse,
  OuterIteration,
} from "@/lib/types-v2";

export type LandUseStage = "idle" | "running" | "done" | "error";

/** Contexto con el que se lanzó la corrida standalone: la geometría (L, km)
 * viene del módulo de transporte y puede cambiar a espaldas de esta página,
 * así que el resultado debe leerse SIEMPRE contra este snapshot. */
export interface LandUseRunContext {
  L: number;
  CBD: number;
  largoKm: number;
  config: LandUseConfig;
}

/** Snapshot del escenario con el que se lanzó la corrida acoplada. */
export interface CoupledRunSnapshot {
  sim: SimulationConfig;
  landUse: LandUseConfig;
  outerMaxIter: number;
}

interface LandUseState {
  config: LandUseConfig;

  // ---- Corrida standalone (página Uso de suelo) ----
  stage: LandUseStage;
  result: LandUseSolveResponse | null;
  runContext: LandUseRunContext | null;
  error: string | null;

  // ---- Corrida acoplada (página Ciudad en equilibrio) ----
  // Vive en el store (no en useState de la página) para que navegar a mitad de
  // una corrida no deje el stream huérfano e invisible al volver.
  coupledStage: LandUseStage;
  coupledIters: OuterIteration[];
  coupledError: string | null;
  coupledSnapshot: CoupledRunSnapshot | null;
  // Preferencias del escenario acoplado (persisten entre visitas a la página).
  coupledSource: string;
  coupledPoblacion: number;
  coupledOuterMaxIter: number;

  setConfig: (updater: (prev: LandUseConfig) => LandUseConfig) => void;

  startRun: (ctx: LandUseRunContext) => void;
  finishStandalone: (r: LandUseSolveResponse) => void;
  fail: (msg: string) => void;
  reset: () => void;

  setCoupledSource: (s: string) => void;
  setCoupledPoblacion: (n: number) => void;
  setCoupledOuterMaxIter: (n: number) => void;
  startCoupled: (snap: CoupledRunSnapshot) => void;
  pushOuterIter: (it: OuterIteration) => void;
  finishCoupled: () => void;
  failCoupled: (msg: string) => void;
  cancelCoupled: () => void;
  resetCoupled: () => void;
}

const snapshot = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

export const useLandUseStore = create<LandUseState>((set) => ({
  config: defaultLandUseConfig,

  stage: "idle",
  result: null,
  runContext: null,
  error: null,

  coupledStage: "idle",
  coupledIters: [],
  coupledError: null,
  coupledSnapshot: null,
  coupledSource: "custom",
  coupledPoblacion: 25000,
  coupledOuterMaxIter: 12,

  setConfig: (updater) => set((s) => ({ config: updater(s.config) })),

  startRun: (ctx) =>
    set({
      stage: "running",
      result: null,
      runContext: snapshot(ctx),
      error: null,
    }),

  finishStandalone: (r) => set({ stage: "done", result: r }),
  fail: (msg) => set({ stage: "error", error: msg }),
  reset: () =>
    set({
      stage: "idle",
      result: null,
      runContext: null,
      error: null,
    }),

  setCoupledSource: (s) => set({ coupledSource: s }),
  setCoupledPoblacion: (n) => set({ coupledPoblacion: n }),
  setCoupledOuterMaxIter: (n) => set({ coupledOuterMaxIter: n }),

  startCoupled: (snap) =>
    set({
      coupledStage: "running",
      coupledIters: [],
      coupledError: null,
      coupledSnapshot: snapshot(snap),
    }),

  pushOuterIter: (it) =>
    set((s) => ({ coupledIters: [...s.coupledIters, it] })),

  finishCoupled: () => set({ coupledStage: "done" }),
  failCoupled: (msg) => set({ coupledStage: "error", coupledError: msg }),

  // Cancelación por el usuario: descarta lo parcial y vuelve a idle.
  cancelCoupled: () =>
    set({
      coupledStage: "idle",
      coupledIters: [],
      coupledError: null,
      coupledSnapshot: null,
    }),

  resetCoupled: () =>
    set({
      coupledStage: "idle",
      coupledIters: [],
      coupledError: null,
      coupledSnapshot: null,
    }),
}));

/** ¿El resultado standalone quedó desactualizado respecto de la config viva? */
export function isLandUseStale(s: {
  stage: LandUseStage;
  config: LandUseConfig;
  runContext: LandUseRunContext | null;
  liveL: number;
  liveLargoKm: number;
}): boolean {
  if (s.stage !== "done" || s.runContext == null) return false;
  if (s.runContext.L !== s.liveL || s.runContext.largoKm !== s.liveLargoKm)
    return true;
  return JSON.stringify(s.config) !== JSON.stringify(s.runContext.config);
}
