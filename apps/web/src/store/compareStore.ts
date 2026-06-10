import { create } from "zustand";

import type { SimulationConfig, SimulationResult } from "@/lib/types";
import type {
  EquilibriumMetrics,
  LandUseConfig,
  LandUseSolveResponse,
} from "@/lib/types-v2";

export type ScenarioStatus = "empty" | "configured" | "running" | "done" | "error";

/** Qué se compara: cada tipo corre un solver distinto sobre el MISMO escenario
 * (la tarjeta captura transporte + suelo + población; el tipo es la lente). */
export type CompareKind = "transport" | "land_use" | "coupled";

/** Resumen liviano del loop acoplado para comparar (no guardamos las trazas
 * completas: con 4 escenarios serían decenas de MB de snapshots). */
export interface CoupledCompareResult {
  first: EquilibriumMetrics;
  last: EquilibriumMetrics;
  iterations: number;
  converged: boolean;
}

export interface Scenario {
  id: string;
  name: string;
  /** Config de transporte (geometría de la ciudad incluida). */
  config: SimulationConfig | null;
  /** Config de uso de suelo (null ⇒ defaults al correr suelo/acoplado). */
  landUse: LandUseConfig | null;
  /** Población del escenario acoplado (escala H_por_estrato). */
  poblacion: number;
  /** Resultados por tipo de comparación. */
  result: SimulationResult | null;
  luResult: LandUseSolveResponse | null;
  coupledResult: CoupledCompareResult | null;
  status: ScenarioStatus;
  error: string | null;
}

const DEFAULT_POBLACION = 25000;

function emptyScenario(id: string): Scenario {
  return {
    id,
    name: "",
    config: null,
    landUse: null,
    poblacion: DEFAULT_POBLACION,
    result: null,
    luResult: null,
    coupledResult: null,
    status: "empty",
    error: null,
  };
}

/** ¿La tarjeta tiene resultado para el tipo de comparación dado? */
export function hasResultFor(sc: Scenario, kind: CompareKind): boolean {
  if (kind === "transport") return sc.result != null;
  if (kind === "land_use") return sc.luResult != null;
  return sc.coupledResult != null;
}

interface CompareState {
  kind: CompareKind;
  scenarios: Scenario[];

  setKind: (kind: CompareKind) => void;
  addScenario: () => void;
  removeScenario: (id: string) => void;
  setScenario: (
    id: string,
    payload: {
      config: SimulationConfig;
      landUse?: LandUseConfig | null;
      poblacion?: number;
      name?: string;
    },
  ) => void;
  renameScenario: (id: string, name: string) => void;
  setStatus: (id: string, status: ScenarioStatus) => void;
  setTransportResult: (id: string, result: SimulationResult) => void;
  setLuResult: (id: string, result: LandUseSolveResponse) => void;
  setCoupledResult: (id: string, result: CoupledCompareResult) => void;
  setError: (id: string, error: string) => void;
  reset: () => void;
}

// Los nombres por defecto se renderizan vía i18n (compare.scenario_card.untitled)
// cuando `name` está vacío; el usuario puede renombrar cuando quiera.
const INITIAL: Scenario[] = [emptyScenario("A"), emptyScenario("B")];

const MAX_SCENARIOS = 4;

export const useCompareStore = create<CompareState>((set) => ({
  kind: "transport",
  scenarios: INITIAL,

  // Cambiar la lente conserva configs y resultados ya corridos: el estado de
  // cada tarjeta se recalcula según si tiene resultado para el tipo nuevo.
  setKind: (kind) =>
    set((s) => ({
      kind,
      scenarios: s.scenarios.map((sc) => ({
        ...sc,
        error: null,
        status:
          sc.status === "running"
            ? sc.status
            : hasResultFor(sc, kind)
              ? "done"
              : sc.config
                ? "configured"
                : "empty",
      })),
    })),

  addScenario: () =>
    set((s) => {
      if (s.scenarios.length >= MAX_SCENARIOS) return s;
      const letter = String.fromCharCode(65 + s.scenarios.length);
      return {
        scenarios: [...s.scenarios, emptyScenario(letter)],
      };
    }),

  removeScenario: (id) =>
    set((s) => ({ scenarios: s.scenarios.filter((sc) => sc.id !== id) })),

  // Reemplaza el escenario completo: invalida los resultados de TODOS los
  // tipos (corresponden a la config anterior).
  setScenario: (id, payload) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id
          ? {
              ...sc,
              config: payload.config,
              landUse: payload.landUse ?? sc.landUse,
              poblacion: payload.poblacion ?? sc.poblacion,
              ...(payload.name !== undefined ? { name: payload.name } : {}),
              result: null,
              luResult: null,
              coupledResult: null,
              status: "configured",
              error: null,
            }
          : sc,
      ),
    })),

  renameScenario: (id, name) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, name } : sc)),
    })),

  setStatus: (id, status) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id ? { ...sc, status, error: status === "error" ? sc.error : null } : sc,
      ),
    })),

  setTransportResult: (id, result) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id ? { ...sc, result, status: "done", error: null } : sc,
      ),
    })),

  setLuResult: (id, luResult) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id ? { ...sc, luResult, status: "done", error: null } : sc,
      ),
    })),

  setCoupledResult: (id, coupledResult) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id ? { ...sc, coupledResult, status: "done", error: null } : sc,
      ),
    })),

  setError: (id, error) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) =>
        sc.id === id ? { ...sc, error, status: "error" } : sc,
      ),
    })),

  reset: () => set({ kind: "transport", scenarios: INITIAL }),
}));
