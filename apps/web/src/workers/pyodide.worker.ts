/// <reference lib="webworker" />
/**
 * Web Worker que hostea una instancia de Pyodide con `titirilquen_core`.
 *
 * Protocolo (main thread → worker):
 *   { id, type: "init" }
 *   { id, type: "simulate", config }
 *   { id, type: "simulateStream", config }
 *
 * Respuestas (worker → main thread):
 *   { id, type: "ready" }
 *   { id, type: "iteration", snapshot }
 *   { id, type: "done", result }
 *   { id, type: "error", message }
 */

import type {
  IterationSnapshot,
  SimulationConfig,
  SimulationResult,
} from "@/lib/types";
import type {
  CoupledRequest,
  LandUseConfig,
  LandUseSolveResponse,
  OuterIteration,
} from "@/lib/types-v2";

type InMsg =
  | { id: string; type: "init" }
  | { id: string; type: "simulate"; config: SimulationConfig }
  | {
      id: string;
      type: "simulateStream";
      config: SimulationConfig;
      /** Opción A: si viene, la población se deriva del uso de suelo
       *  (densidad por estrato → por celda) en vez de la densidad plana. */
      land_use?: LandUseConfig;
      /** Localización de los estratos: "original" = mezcla uniforme π_h (el
       *  equilibrio de pujas no se ha movido); "equilibrio" = producto del
       *  bid-rent. Solo aplica con `land_use`. Default "equilibrio". */
      localizacion?: "equilibrio" | "original";
    }
  | {
      id: string;
      type: "landUseSolve";
      req: { L: number; CBD: number; land_use: LandUseConfig };
    }
  | { id: string; type: "coupledStream"; req: CoupledRequest }
  /** Cancelación cooperativa (F-03): marca la corrida `targetId` para que su
   *  loop de streaming se detenga en el próximo borde de iteración, SIN
   *  terminar el worker (Pyodide sobrevive; no se re-paga el boot). */
  | { id: string; type: "cancel"; targetId: string };

type OutMsg =
  | { id: string; type: "ready" }
  | { id: string; type: "bootStage"; stage: "runtime" | "packages" | "wheel" }
  | { id: string; type: "iteration"; snapshot: IterationSnapshot }
  | { id: string; type: "done"; result: SimulationResult }
  | { id: string; type: "landUseDone"; result: LandUseSolveResponse }
  | { id: string; type: "outerIteration"; outer: OuterIteration }
  | { id: string; type: "coupledDone" }
  | { id: string; type: "error"; message: string };

declare const self: DedicatedWorkerGlobalScope;

const PYODIDE_VERSION = "0.26.4";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

interface PyodideInterface {
  loadPackage: (names: string[]) => Promise<void>;
  pyimport: (name: string) => unknown;
  runPythonAsync: (code: string) => Promise<unknown>;
  globals: { set: (k: string, v: unknown) => void };
}

type LoadPyodide = (opts: { indexURL: string }) => Promise<PyodideInterface>;

let pyodide: PyodideInterface | null = null;
let simulateFn: ((config: unknown) => unknown) | null = null;
let iterFn: ((config: unknown) => unknown) | null = null;
let iterSueloFn: ((req: unknown) => unknown) | null = null;
let lastTraceFn: (() => unknown) | null = null;
let landUseSolveFn: ((req: unknown) => unknown) | null = null;
let coupledIterFn: ((req: unknown) => unknown) | null = null;

function post(msg: OutMsg): void {
  self.postMessage(msg);
}

/** Corridas marcadas para cancelar (F-03). Los loops de streaming ceden el
 * event loop entre iteraciones (yield0) para que el mensaje "cancel" pueda
 * procesarse mientras corren; sin ese yield el loop es síncrono y el mensaje
 * quedaría encolado hasta el final. */
const cancelledIds = new Set<string>();

const yield0 = () => new Promise<void>((r) => setTimeout(r, 0));

async function init(): Promise<void> {
  if (pyodide) return;

  // En module workers no existe `importScripts`. Usamos la build .mjs que
  // Pyodide distribuye para contextos ESM. `@vite-ignore` evita que Vite
  // intente resolver/bundlear la URL remota.
  post({ id: "boot", type: "bootStage", stage: "runtime" });
  const mod = (await import(
    /* @vite-ignore */ `${PYODIDE_CDN}pyodide.mjs`
  )) as {
    loadPyodide: LoadPyodide;
  };
  const py = await mod.loadPyodide({ indexURL: PYODIDE_CDN });
  pyodide = py;

  post({ id: "boot", type: "bootStage", stage: "packages" });
  await py.loadPackage(["micropip", "numpy", "scipy"]);

  // Descargar y registrar el wheel del core.
  post({ id: "boot", type: "bootStage", stage: "wheel" });
  const whlUrl = new URL(
    "/pyodide/titirilquen_core-0.2.0-py3-none-any.whl",
    self.location.origin,
  ).toString();

  await py.runPythonAsync(`
import micropip
await micropip.install("pydantic")
await micropip.install(${JSON.stringify(whlUrl)})

from titirilquen_core import LandUseCity, LandUseConfig, SimulationConfig, run_msa
from titirilquen_core.coupled import iter_coupled
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa, iter_msa_desde_suelo
import json

# La forma del resultado la define el CORE, en titirilquen_core.serializacion.
# Antes estaba reescrita acá dentro, en un string que ninguna herramienta
# revisa; divergió del gemelo de la API y el frontend terminó mostrando ceros.
# Este bloque ya solo es el pegamento entre el worker y el núcleo.
from titirilquen_core.serializacion import (
    iteration_to_dict,
    land_use_city_to_dict,
    outer_iteration_to_dict,
    trace_to_dict,
)

def simulate_from_json(config_json: str):
    cfg = SimulationConfig.model_validate_json(config_json)
    return trace_to_dict(run_msa(cfg), cfg)

# Streaming en una sola corrida: iter_msa popula el trace completo mientras
# emite los snapshots. Tras agotar el generador, last_trace_to_py() devuelve el
# resultado final (agentes/emisiones) SIN volver a correr la simulación.
_LAST_TRACE = {"trace": None, "cfg": None}

def iter_from_json(config_json: str):
    cfg = SimulationConfig.model_validate_json(config_json)
    trace = ConvergenceTrace()
    _LAST_TRACE["trace"] = None
    _LAST_TRACE["cfg"] = cfg
    for snap in iter_msa(cfg, trace):
        yield iteration_to_dict(snap)
    _LAST_TRACE["trace"] = trace

def iter_from_json_suelo(req_json: str):
    # Opción A: la población del transporte se deriva del uso de suelo
    # (densidad por estrato → densidad por celda), no de la densidad plana.
    req = json.loads(req_json)
    cfg = SimulationConfig.model_validate(req["config"])
    lu = LandUseConfig.model_validate(req["land_use"])
    localizacion = req.get("localizacion", "equilibrio")
    trace = ConvergenceTrace()
    _LAST_TRACE["trace"] = None
    _LAST_TRACE["cfg"] = cfg
    for snap in iter_msa_desde_suelo(cfg, lu, trace, localizacion=localizacion):
        yield iteration_to_dict(snap)
    _LAST_TRACE["trace"] = trace

def last_trace_to_py():
    t = _LAST_TRACE["trace"]
    return None if t is None else trace_to_dict(t, _LAST_TRACE["cfg"])

def land_use_solve_from_json(req_json: str):
    req = json.loads(req_json)
    cfg = LandUseConfig.model_validate(req["land_use"])
    L = int(req["L"])
    largo_km = float(req.get("largo_km", 20.0))
    city = LandUseCity.build(L=L, CBD=int(req["CBD"]), cfg=cfg, ancho_celda_km=largo_km / L)
    return land_use_city_to_dict(city)

def coupled_iter_from_json(req_json: str):
    req = json.loads(req_json)
    sim = SimulationConfig.model_validate(req["sim"])
    cfg = LandUseConfig.model_validate(req["land_use"])
    outer_max_iter = int(req.get("outer_max_iter", 3))
    outer_tol = float(req.get("outer_tol", 1.0))
    for outer in iter_coupled(
        sim=sim,
        land_use_config=cfg,
        outer_max_iter=outer_max_iter,
        outer_tol=outer_tol,
    ):
        yield outer_iteration_to_dict(outer)
`);

  const globals = py.pyimport("__main__") as {
    simulate_from_json: unknown;
    iter_from_json: unknown;
    iter_from_json_suelo: unknown;
    last_trace_to_py: unknown;
    land_use_solve_from_json: unknown;
    coupled_iter_from_json: unknown;
  };
  simulateFn = globals.simulate_from_json as (c: unknown) => unknown;
  iterFn = globals.iter_from_json as (c: unknown) => unknown;
  iterSueloFn = globals.iter_from_json_suelo as (r: unknown) => unknown;
  lastTraceFn = globals.last_trace_to_py as () => unknown;
  landUseSolveFn = globals.land_use_solve_from_json as (r: unknown) => unknown;
  coupledIterFn = globals.coupled_iter_from_json as (r: unknown) => unknown;
}

function jsFromPy(value: unknown): unknown {
  if (value && typeof (value as { toJs?: unknown }).toJs === "function") {
    const obj = (
      value as {
        toJs: (opts: { dict_converter: typeof Object.fromEntries }) => unknown;
      }
    ).toJs({
      dict_converter: Object.fromEntries,
    });
    if (typeof (value as { destroy?: unknown }).destroy === "function") {
      (value as { destroy: () => void }).destroy();
    }
    return obj;
  }
  return value;
}

self.addEventListener("message", async (ev: MessageEvent<InMsg>) => {
  const msg = ev.data;
  try {
    // La cancelación no necesita Pyodide y debe procesarse aunque el init
    // esté en curso: antes del await.
    if (msg.type === "cancel") {
      cancelledIds.add(msg.targetId);
      return;
    }
    await init();
    if (msg.type === "init") {
      post({ id: msg.id, type: "ready" });
      return;
    }
    if (msg.type === "simulate") {
      const result = jsFromPy(
        simulateFn!(JSON.stringify(msg.config)),
      ) as SimulationResult;
      post({ id: msg.id, type: "done", result });
      return;
    }
    if (msg.type === "simulateStream") {
      // Opción A: con `land_use`, la población viene del uso de suelo
      // (densidad por estrato → por celda); si no, densidad plana clásica.
      const gen = (
        msg.land_use
          ? iterSueloFn!(
              JSON.stringify({
                config: msg.config,
                land_use: msg.land_use,
                localizacion: msg.localizacion ?? "equilibrio",
              }),
            )
          : iterFn!(JSON.stringify(msg.config))
      ) as {
        [Symbol.iterator](): Iterator<unknown>;
      };
      const iter = gen[Symbol.iterator]();
      try {
        while (true) {
          const { value, done } = iter.next();
          if (done) break;
          const snapshot = jsFromPy(value) as IterationSnapshot;
          post({ id: msg.id, type: "iteration", snapshot });
          // Ceder el event loop: permite procesar un "cancel" en vuelo.
          await yield0();
          if (cancelledIds.delete(msg.id)) return;
        }
      } finally {
        (gen as { destroy?: () => void }).destroy?.();
      }
      // El trace completo (agentes, carga_metro final, emisiones) ya quedó poblado
      // durante el streaming (iter_msa con trace) — lo leemos sin volver a correr.
      const result = jsFromPy(lastTraceFn!()) as SimulationResult;
      post({ id: msg.id, type: "done", result });
      return;
    }
    if (msg.type === "landUseSolve") {
      const result = jsFromPy(
        landUseSolveFn!(JSON.stringify(msg.req)),
      ) as LandUseSolveResponse;
      post({ id: msg.id, type: "landUseDone", result });
      return;
    }
    if (msg.type === "coupledStream") {
      const gen = coupledIterFn!(JSON.stringify(msg.req)) as {
        [Symbol.iterator](): Iterator<unknown>;
      };
      const iter = gen[Symbol.iterator]();
      try {
        while (true) {
          const { value, done } = iter.next();
          if (done) break;
          const outer = jsFromPy(value) as OuterIteration;
          post({ id: msg.id, type: "outerIteration", outer });
          await yield0();
          if (cancelledIds.delete(msg.id)) return;
        }
      } finally {
        (gen as { destroy?: () => void }).destroy?.();
      }
      post({ id: msg.id, type: "coupledDone" });
      return;
    }
  } catch (e) {
    post({
      id: (msg as { id?: string }).id ?? "unknown",
      type: "error",
      message: e instanceof Error ? e.message : String(e),
    });
  }
});
