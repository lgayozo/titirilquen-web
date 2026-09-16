import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { SimulationConfig, SimulationResult } from "@/lib/types";
import type {
  EquilibriumMetrics,
  LandUseConfig,
  LandUseSolveResponse,
} from "@/lib/types-v2";

export type ScenarioStatus =
  | "empty"
  | "configured"
  | "running"
  | "done"
  | "error";

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
  /** Localización de estratos para la lente Transporte (C-02): snapshot de la
   * regla del Sandbox al capturar con «Usar Transporte actual». null ⇒ se
   * decide al correr según si la tarjeta tiene resultado de suelo. */
  localizacion: "equilibrio" | "original" | null;
  /** Población del escenario acoplado (escala H_por_estrato). */
  poblacion: number;
  /** Preset con el que se construyó la tarjeta, o `null` si es a medida
   *  («usar config actual» / importar). Vive en el escenario y no en el
   *  componente para que sobreviva a la recarga: si no, tras un F5 los combos
   *  decían «Personalizado» sobre una tarjeta que sí era un preset. */
  presetCity: string | null;
  presetPolicy: string | null;
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
    localizacion: null,
    poblacion: DEFAULT_POBLACION,
    presetCity: null,
    presetPolicy: null,
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
  /** Escenario contra el que se calculan los deltas. `null` ⇒ el primero con
   *  resultado (el comportamiento implícito anterior, que no era elegible). */
  baseId: string | null;

  setKind: (kind: CompareKind) => void;
  setBaseId: (id: string | null) => void;
  addScenario: () => void;
  removeScenario: (id: string) => void;
  setScenario: (
    id: string,
    payload: {
      config: SimulationConfig;
      landUse?: LandUseConfig | null;
      localizacion?: "equilibrio" | "original" | null;
      poblacion?: number;
      name?: string;
      presetCity?: string | null;
      presetPolicy?: string | null;
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

/** Solo los INPUTS se persisten. Los resultados se descartan a propósito: un
 *  `SimulationResult` trae arreglos de `n_celdas` por iteración y por modo, así
 *  que con 4 escenarios serían megabytes en localStorage para algo que se
 *  recomputa. Al recargar, las tarjetas vuelven a «configured» y basta con
 *  correrlas. */
type CompareInputs = Pick<CompareState, "kind" | "baseId"> & {
  scenarios: Pick<
    Scenario,
    | "id"
    | "name"
    | "config"
    | "landUse"
    | "localizacion"
    | "poblacion"
    | "presetCity"
    | "presetPolicy"
  >[];
};

export const useCompareStore = create<CompareState>()(
  persist(
    (set) => ({
      kind: "transport",
      scenarios: INITIAL,
      baseId: null,

      setBaseId: (baseId) => set({ baseId }),

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
        set((s) => ({
          scenarios: s.scenarios.filter((sc) => sc.id !== id),
          // Si se borra la base, se vuelve a la elección automática en vez de
          // quedar apuntando a un escenario inexistente.
          baseId: s.baseId === id ? null : s.baseId,
        })),

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
                  localizacion:
                    payload.localizacion !== undefined
                      ? payload.localizacion
                      : sc.localizacion,
                  poblacion: payload.poblacion ?? sc.poblacion,
                  presetCity:
                    payload.presetCity !== undefined
                      ? payload.presetCity
                      : null,
                  presetPolicy:
                    payload.presetPolicy !== undefined
                      ? payload.presetPolicy
                      : null,
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
          scenarios: s.scenarios.map((sc) =>
            sc.id === id ? { ...sc, name } : sc,
          ),
        })),

      setStatus: (id, status) =>
        set((s) => ({
          scenarios: s.scenarios.map((sc) =>
            sc.id === id
              ? { ...sc, status, error: status === "error" ? sc.error : null }
              : sc,
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
            sc.id === id
              ? { ...sc, luResult, status: "done", error: null }
              : sc,
          ),
        })),

      setCoupledResult: (id, coupledResult) =>
        set((s) => ({
          scenarios: s.scenarios.map((sc) =>
            sc.id === id
              ? { ...sc, coupledResult, status: "done", error: null }
              : sc,
          ),
        })),

      setError: (id, error) =>
        set((s) => ({
          scenarios: s.scenarios.map((sc) =>
            sc.id === id ? { ...sc, error, status: "error" } : sc,
          ),
        })),

      reset: () => set({ kind: "transport", scenarios: INITIAL, baseId: null }),
    }),
    {
      name: "titirilquen.compare.v1",
      partialize: (s): CompareInputs => ({
        kind: s.kind,
        baseId: s.baseId,
        scenarios: s.scenarios.map(
          ({
            id,
            name,
            config,
            landUse,
            localizacion,
            poblacion,
            presetCity,
            presetPolicy,
          }) => ({
            id,
            name,
            config,
            landUse,
            localizacion,
            poblacion,
            presetCity,
            presetPolicy,
          }),
        ),
      }),
      // Rehidrata los inputs y reconstruye el estado derivado: sin resultados,
      // una tarjeta con config está «configured» y una vacía, «empty».
      merge: (persisted, current) => {
        const p = persisted as Partial<CompareInputs> | undefined;
        if (!p?.scenarios?.length) return current;
        return {
          ...current,
          kind: p.kind ?? current.kind,
          baseId: p.baseId ?? null,
          scenarios: p.scenarios.map((sc) => ({
            ...emptyScenario(sc.id),
            ...sc,
            status: sc.config ? ("configured" as const) : ("empty" as const),
          })),
        };
      },
    },
  ),
);
