import { create } from "zustand";

import type { SimulationConfig, SimulationResult } from "@/lib/types";

export type ScenarioStatus = "empty" | "configured" | "running" | "done" | "error";

export interface Scenario {
  id: string;
  name: string;
  config: SimulationConfig | null;
  result: SimulationResult | null;
  status: ScenarioStatus;
  error: string | null;
}

function emptyScenario(id: string, name: string): Scenario {
  return { id, name, config: null, result: null, status: "empty", error: null };
}

interface CompareState {
  scenarios: Scenario[];

  addScenario: () => void;
  removeScenario: (id: string) => void;
  setConfig: (id: string, config: SimulationConfig, name?: string) => void;
  renameScenario: (id: string, name: string) => void;
  setStatus: (id: string, status: ScenarioStatus) => void;
  setResult: (id: string, result: SimulationResult) => void;
  setError: (id: string, error: string) => void;
  reset: () => void;
}

const INITIAL: Scenario[] = [
  emptyScenario("A", "Escenario A"),
  emptyScenario("B", "Escenario B"),
];

const MAX_SCENARIOS = 4;

export const useCompareStore = create<CompareState>((set) => ({
  scenarios: INITIAL,

  addScenario: () =>
    set((s) => {
      if (s.scenarios.length >= MAX_SCENARIOS) return s;
      const letter = String.fromCharCode(65 + s.scenarios.length);
      return {
        scenarios: [...s.scenarios, emptyScenario(letter, `Escenario ${letter}`)],
      };
    }),

  removeScenario: (id) =>
    set((s) => ({ scenarios: s.scenarios.filter((sc) => sc.id !== id) })),

  setConfig: (id, config, name) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id
          ? {
              ...sc,
              config,
              name: name ?? sc.name,
              status: "configured",
              error: null,
              result: null,
            }
          : sc
      ),
    })),

  renameScenario: (id, name) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, name } : sc)),
    })),

  setStatus: (id, status) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, status } : sc)),
    })),

  setResult: (id, result) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id ? { ...sc, result, status: "done" } : sc
      ),
    })),

  setError: (id, error) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id ? { ...sc, status: "error", error } : sc
      ),
    })),

  reset: () => set({ scenarios: INITIAL }),
}));
