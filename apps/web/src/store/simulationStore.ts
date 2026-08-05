import { create } from "zustand";

import { defaultSimulationConfig } from "@/lib/defaults";
import type {
  IterationSnapshot,
  SimulationConfig,
  SimulationResult,
} from "@/lib/types";

export type Engine = "api" | "local";

export type RunStage = "idle" | "booting" | "running" | "done" | "error";

interface SimulationState {
  config: SimulationConfig;
  engine: Engine;
  stage: RunStage;
  running: boolean;
  progress: { current: number; total: number } | null;
  result: SimulationResult | null;
  liveIterations: IterationSnapshot[];
  error: string | null;
  /** Snapshot de la config con la que se lanzó la última corrida. Las figuras
   * derivadas del resultado deben usar ESTA config (no la viva) para no mezclar
   * geometrías; comparar con `config` detecta resultados desactualizados. */
  configUsed: SimulationConfig | null;
  /** Instantánea FIJADA como referencia para comparar dentro del módulo: la
   *  config y el resultado de una corrida anterior. Permite «corro un
   *  escenario, lo fijo, corro otro y veo el delta» sin salir de la página ni
   *  reconstruir el escenario en Comparar. */
  reference: { config: SimulationConfig; result: SimulationResult } | null;

  setConfig: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
  replaceConfig: (config: SimulationConfig) => void;
  setEngine: (engine: Engine) => void;
  setStage: (stage: RunStage) => void;
  startRun: (total: number) => void;
  pushIteration: (snap: IterationSnapshot) => void;
  finishRun: (result: SimulationResult) => void;
  failRun: (message: string) => void;
  cancelRun: () => void;
  reset: () => void;
  /** Fija la corrida visible como referencia. No hace nada si no hay resultado
   *  (el snapshot debe corresponder a una config efectivamente corrida). */
  pinReference: () => void;
  clearReference: () => void;
}

const snapshot = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

export const useSimulationStore = create<SimulationState>((set) => ({
  config: defaultSimulationConfig,
  engine: "local",
  stage: "idle",
  running: false,
  progress: null,
  result: null,
  liveIterations: [],
  error: null,
  configUsed: null,
  reference: null,

  setConfig: (updater) => set((s) => ({ config: updater(s.config) })),
  replaceConfig: (config) => set({ config }),
  setEngine: (engine) => set({ engine }),
  setStage: (stage) => set({ stage }),

  startRun: (total) =>
    set((s) => ({
      running: true,
      stage: "booting",
      progress: { current: 0, total },
      result: null,
      liveIterations: [],
      error: null,
      configUsed: snapshot(s.config),
    })),

  pushIteration: (snap) =>
    set((s) => ({
      stage: "running",
      liveIterations: [...s.liveIterations, snap],
      progress: s.progress
        ? { current: snap.iter + 1, total: s.progress.total }
        : null,
    })),

  pinReference: () =>
    set((s) =>
      s.result && s.configUsed
        ? { reference: { config: s.configUsed, result: s.result } }
        : s,
    ),

  clearReference: () => set({ reference: null }),

  finishRun: (result) =>
    set({
      running: false,
      stage: "done",
      result,
      progress: null,
    }),

  failRun: (message) =>
    set({
      running: false,
      stage: "error",
      error: message,
      progress: null,
    }),

  // Cancelación por el usuario: vuelve a idle descartando lo parcial (la
  // corrida del motor se aborta aparte, vía AbortController / cancelAll).
  cancelRun: () =>
    set({
      running: false,
      stage: "idle",
      progress: null,
      result: null,
      liveIterations: [],
      error: null,
      configUsed: null,
    }),

  reset: () =>
    set({
      result: null,
      liveIterations: [],
      progress: null,
      running: false,
      stage: "idle",
      error: null,
      configUsed: null,
    }),
}));

/** ¿El resultado vigente quedó desactualizado respecto de la config viva? */
export function isResultStale(s: {
  stage: RunStage;
  config: SimulationConfig;
  configUsed: SimulationConfig | null;
}): boolean {
  if (s.stage !== "done" || s.configUsed == null) return false;
  return JSON.stringify(s.config) !== JSON.stringify(s.configUsed);
}
