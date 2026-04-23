import { create } from "zustand";

import { defaultSimulationConfig } from "@/lib/defaults";
import type { IterationSnapshot, SimulationConfig, SimulationResult } from "@/lib/types";

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

  setConfig: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
  replaceConfig: (config: SimulationConfig) => void;
  setEngine: (engine: Engine) => void;
  setStage: (stage: RunStage) => void;
  startRun: (total: number) => void;
  pushIteration: (snap: IterationSnapshot) => void;
  finishRun: (result: SimulationResult) => void;
  failRun: (message: string) => void;
  reset: () => void;
}

export const useSimulationStore = create<SimulationState>((set) => ({
  config: defaultSimulationConfig,
  engine: "local",
  stage: "idle",
  running: false,
  progress: null,
  result: null,
  liveIterations: [],
  error: null,

  setConfig: (updater) => set((s) => ({ config: updater(s.config) })),
  replaceConfig: (config) => set({ config }),
  setEngine: (engine) => set({ engine }),
  setStage: (stage) => set({ stage }),

  startRun: (total) =>
    set({
      running: true,
      stage: "booting",
      progress: { current: 0, total },
      result: null,
      liveIterations: [],
      error: null,
    }),

  pushIteration: (snap) =>
    set((s) => ({
      stage: "running",
      liveIterations: [...s.liveIterations, snap],
      progress: s.progress ? { current: snap.iter + 1, total: s.progress.total } : null,
    })),

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

  reset: () =>
    set({
      result: null,
      liveIterations: [],
      progress: null,
      running: false,
      stage: "idle",
      error: null,
    }),
}));
