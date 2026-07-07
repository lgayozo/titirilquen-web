/**
 * Wrapper de alto nivel sobre el Web Worker de Pyodide. Expone una API
 * simétrica a `api.ts` / `api-v2.ts` para que los stores no necesiten saber
 * qué motor está detrás.
 *
 * Cancelación: Pyodide no puede interrumpirse a mitad de un cómputo, así que
 * cancelar (vía `AbortSignal` o `cancelAll()`) **termina el worker** y rechaza
 * todas las promesas pendientes con `AbortError`; el próximo uso re-inicializa
 * Pyodide (la UI ya tiene estado "booting" para ese caso).
 */

import type { IterationSnapshot, SimulationConfig, SimulationResult } from "@/lib/types";
import type {
  CoupledRequest,
  LandUseConfig,
  LandUseSolveResponse,
  OuterIteration,
} from "@/lib/types-v2";

type WorkerOutMsg =
  | { id: string; type: "ready" }
  | { id: string; type: "iteration"; snapshot: IterationSnapshot }
  | { id: string; type: "done"; result: SimulationResult }
  | { id: string; type: "landUseDone"; result: LandUseSolveResponse }
  | { id: string; type: "outerIteration"; outer: OuterIteration }
  | { id: string; type: "coupledDone" }
  | { id: string; type: "error"; message: string };

type WorkerInMsg =
  | { id: string; type: "init" }
  | { id: string; type: "simulate"; config: SimulationConfig }
  | {
      id: string;
      type: "simulateStream";
      config: SimulationConfig;
      land_use?: LandUseConfig;
      localizacion?: "equilibrio" | "original";
    }
  | {
      id: string;
      type: "landUseSolve";
      req: { L: number; CBD: number; largo_km: number; land_use: LandUseConfig };
    }
  | { id: string; type: "coupledStream"; req: CoupledRequest };

function abortError(): Error {
  return new DOMException("Corrida cancelada", "AbortError");
}

/** Omit distributivo: aplica Omit a cada miembro de la unión (el Omit normal
 * colapsa la unión y pierde los campos específicos de cada mensaje). */
type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;

class PyodideEngine {
  private worker: Worker | null = null;
  private ready: Promise<void> | null = null;
  private nextId = 0;
  /** Corridas en vuelo: cómo rechazarlas y desuscribir sus listeners. */
  private pending = new Map<string, { reject: (e: Error) => void; cleanup: () => void }>();

  private ensureWorker(): Worker {
    if (!this.worker) {
      this.worker = new Worker(new URL("../workers/pyodide.worker.ts", import.meta.url), {
        type: "module",
      });
    }
    return this.worker;
  }

  async init(): Promise<void> {
    if (this.ready) return this.ready;
    const worker = this.ensureWorker();
    this.ready = new Promise<void>((resolve, reject) => {
      const id = String(this.nextId++);
      const onMsg = (ev: MessageEvent<WorkerOutMsg>) => {
        if (ev.data.id !== id) return;
        if (ev.data.type === "ready") {
          cleanup();
          resolve();
        } else if (ev.data.type === "error") {
          cleanup();
          reject(new Error(ev.data.message));
        }
      };
      const cleanup = () => {
        worker.removeEventListener("message", onMsg);
        this.pending.delete(id);
      };
      this.pending.set(id, { reject, cleanup });
      worker.addEventListener("message", onMsg);
      const req: WorkerInMsg = { id, type: "init" };
      worker.postMessage(req);
    });
    return this.ready;
  }

  /**
   * Registra una corrida contra el worker. `onMessage` devuelve `true` cuando
   * el mensaje es terminal (resolve/reject ya llamado) para desuscribir.
   */
  private async request<T>(
    msg: DistributiveOmit<WorkerInMsg, "id">,
    handle: (
      data: WorkerOutMsg,
      resolve: (v: T) => void,
      reject: (e: Error) => void,
    ) => boolean,
    signal?: AbortSignal,
  ): Promise<T> {
    if (signal?.aborted) throw abortError();
    await this.init();
    if (signal?.aborted) throw abortError();
    const worker = this.ensureWorker();
    const id = String(this.nextId++);
    return new Promise<T>((resolve, reject) => {
      const onAbort = () => this.cancelAll();
      const cleanup = () => {
        worker.removeEventListener("message", onMsg);
        signal?.removeEventListener("abort", onAbort);
        this.pending.delete(id);
      };
      const onMsg = (ev: MessageEvent<WorkerOutMsg>) => {
        if (ev.data.id !== id) return;
        const terminal = handle(ev.data, resolve, reject);
        if (terminal) cleanup();
      };
      this.pending.set(id, { reject, cleanup });
      signal?.addEventListener("abort", onAbort, { once: true });
      worker.addEventListener("message", onMsg);
      worker.postMessage({ ...msg, id } as WorkerInMsg);
    });
  }

  async simulate(config: SimulationConfig, signal?: AbortSignal): Promise<SimulationResult> {
    return this.request<SimulationResult>(
      { type: "simulate", config },
      (data, resolve, reject) => {
        if (data.type === "done") {
          resolve(data.result);
          return true;
        }
        if (data.type === "error") {
          reject(new Error(data.message));
          return true;
        }
        return false;
      },
      signal,
    );
  }

  async simulateStream(
    config: SimulationConfig,
    onIteration: (s: IterationSnapshot) => void,
    signal?: AbortSignal,
    landUse?: LandUseConfig,
    localizacion?: "equilibrio" | "original",
  ): Promise<SimulationResult> {
    return this.request<SimulationResult>(
      { type: "simulateStream", config, land_use: landUse, localizacion },
      (data, resolve, reject) => {
        if (data.type === "iteration") {
          onIteration(data.snapshot);
          return false;
        }
        if (data.type === "done") {
          resolve(data.result);
          return true;
        }
        if (data.type === "error") {
          reject(new Error(data.message));
          return true;
        }
        return false;
      },
      signal,
    );
  }

  async solveLandUse(
    req: { L: number; CBD: number; largo_km: number; land_use: LandUseConfig },
    signal?: AbortSignal,
  ): Promise<LandUseSolveResponse> {
    return this.request<LandUseSolveResponse>(
      { type: "landUseSolve", req },
      (data, resolve, reject) => {
        if (data.type === "landUseDone") {
          resolve(data.result);
          return true;
        }
        if (data.type === "error") {
          reject(new Error(data.message));
          return true;
        }
        return false;
      },
      signal,
    );
  }

  async solveCoupledStream(
    req: CoupledRequest,
    onOuter: (it: OuterIteration) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return this.request<void>(
      { type: "coupledStream", req },
      (data, resolve, reject) => {
        if (data.type === "outerIteration") {
          onOuter(data.outer);
          return false;
        }
        if (data.type === "coupledDone") {
          resolve();
          return true;
        }
        if (data.type === "error") {
          reject(new Error(data.message));
          return true;
        }
        return false;
      },
      signal,
    );
  }

  /** Aborta TODO: rechaza las corridas pendientes y mata el worker. El próximo
   * uso re-inicializa Pyodide desde cero. */
  cancelAll(): void {
    const inflight = [...this.pending.values()];
    this.pending.clear();
    for (const p of inflight) {
      p.cleanup();
      p.reject(abortError());
    }
    this.terminate();
  }

  terminate(): void {
    this.worker?.terminate();
    this.worker = null;
    this.ready = null;
  }
}

export const pyodideEngine = new PyodideEngine();
