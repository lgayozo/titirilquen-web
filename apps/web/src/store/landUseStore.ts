import { create } from "zustand";

import { defaultLandUseConfig } from "@/lib/api-v2";
import type {
  CoupledResult,
  LandUseConfig,
  LandUseSolveResponse,
  OuterIteration,
} from "@/lib/types-v2";

export type LandUseStage = "idle" | "running" | "done" | "error";

interface LandUseState {
  config: LandUseConfig;
  stage: LandUseStage;
  result: LandUseSolveResponse | null;
  coupledResult: CoupledResult | null;
  liveOuterIters: OuterIteration[];
  outerMaxIter: number;
  error: string | null;

  setConfig: (updater: (prev: LandUseConfig) => LandUseConfig) => void;
  setOuterMaxIter: (n: number) => void;
  startRun: () => void;
  pushOuterIter: (it: OuterIteration) => void;
  finishStandalone: (r: LandUseSolveResponse) => void;
  finishCoupled: (r: CoupledResult) => void;
  fail: (msg: string) => void;
  reset: () => void;
}

export const useLandUseStore = create<LandUseState>((set) => ({
  config: defaultLandUseConfig,
  stage: "idle",
  result: null,
  coupledResult: null,
  liveOuterIters: [],
  outerMaxIter: 3,
  error: null,

  setConfig: (updater) => set((s) => ({ config: updater(s.config) })),
  setOuterMaxIter: (n) => set({ outerMaxIter: n }),

  startRun: () =>
    set({
      stage: "running",
      result: null,
      coupledResult: null,
      liveOuterIters: [],
      error: null,
    }),

  pushOuterIter: (it) =>
    set((s) => ({ liveOuterIters: [...s.liveOuterIters, it] })),

  finishStandalone: (r) => set({ stage: "done", result: r }),
  finishCoupled: (r) => set({ stage: "done", coupledResult: r }),
  fail: (msg) => set({ stage: "error", error: msg }),
  reset: () =>
    set({
      stage: "idle",
      result: null,
      coupledResult: null,
      liveOuterIters: [],
      error: null,
    }),
}));
