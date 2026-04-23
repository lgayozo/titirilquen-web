/**
 * Wrapper de alto nivel sobre el Web Worker de Pyodide. Expone una API
 * simétrica a `api.ts` / `api-v2.ts` para que los stores no necesiten saber
 * qué motor está detrás.
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
  | { id: string; type: "simulateStream"; config: SimulationConfig }
  | {
      id: string;
      type: "landUseSolve";
      req: { L: number; CBD: number; land_use: LandUseConfig };
    }
  | { id: string; type: "coupledStream"; req: CoupledRequest };

class PyodideEngine {
  private worker: Worker | null = null;
  private ready: Promise<void> | null = null;
  private nextId = 0;

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
          worker.removeEventListener("message", onMsg);
          resolve();
        } else if (ev.data.type === "error") {
          worker.removeEventListener("message", onMsg);
          reject(new Error(ev.data.message));
        }
      };
      worker.addEventListener("message", onMsg);
      const req: WorkerInMsg = { id, type: "init" };
      worker.postMessage(req);
    });
    return this.ready;
  }

  async simulate(config: SimulationConfig): Promise<SimulationResult> {
    await this.init();
    const worker = this.ensureWorker();
    const id = String(this.nextId++);
    return new Promise<SimulationResult>((resolve, reject) => {
      const onMsg = (ev: MessageEvent<WorkerOutMsg>) => {
        if (ev.data.id !== id) return;
        if (ev.data.type === "done") {
          worker.removeEventListener("message", onMsg);
          resolve(ev.data.result);
        } else if (ev.data.type === "error") {
          worker.removeEventListener("message", onMsg);
          reject(new Error(ev.data.message));
        }
      };
      worker.addEventListener("message", onMsg);
      const req: WorkerInMsg = { id, type: "simulate", config };
      worker.postMessage(req);
    });
  }

  async simulateStream(
    config: SimulationConfig,
    onIteration: (s: IterationSnapshot) => void
  ): Promise<SimulationResult> {
    await this.init();
    const worker = this.ensureWorker();
    const id = String(this.nextId++);
    return new Promise<SimulationResult>((resolve, reject) => {
      const onMsg = (ev: MessageEvent<WorkerOutMsg>) => {
        if (ev.data.id !== id) return;
        if (ev.data.type === "iteration") {
          onIteration(ev.data.snapshot);
        } else if (ev.data.type === "done") {
          worker.removeEventListener("message", onMsg);
          resolve(ev.data.result);
        } else if (ev.data.type === "error") {
          worker.removeEventListener("message", onMsg);
          reject(new Error(ev.data.message));
        }
      };
      worker.addEventListener("message", onMsg);
      const req: WorkerInMsg = { id, type: "simulateStream", config };
      worker.postMessage(req);
    });
  }

  async solveLandUse(req: {
    L: number;
    CBD: number;
    land_use: LandUseConfig;
  }): Promise<LandUseSolveResponse> {
    await this.init();
    const worker = this.ensureWorker();
    const id = String(this.nextId++);
    return new Promise<LandUseSolveResponse>((resolve, reject) => {
      const onMsg = (ev: MessageEvent<WorkerOutMsg>) => {
        if (ev.data.id !== id) return;
        if (ev.data.type === "landUseDone") {
          worker.removeEventListener("message", onMsg);
          resolve(ev.data.result);
        } else if (ev.data.type === "error") {
          worker.removeEventListener("message", onMsg);
          reject(new Error(ev.data.message));
        }
      };
      worker.addEventListener("message", onMsg);
      const msg: WorkerInMsg = { id, type: "landUseSolve", req };
      worker.postMessage(msg);
    });
  }

  async solveCoupledStream(
    req: CoupledRequest,
    onOuter: (it: OuterIteration) => void
  ): Promise<void> {
    await this.init();
    const worker = this.ensureWorker();
    const id = String(this.nextId++);
    return new Promise<void>((resolve, reject) => {
      const onMsg = (ev: MessageEvent<WorkerOutMsg>) => {
        if (ev.data.id !== id) return;
        if (ev.data.type === "outerIteration") {
          onOuter(ev.data.outer);
        } else if (ev.data.type === "coupledDone") {
          worker.removeEventListener("message", onMsg);
          resolve();
        } else if (ev.data.type === "error") {
          worker.removeEventListener("message", onMsg);
          reject(new Error(ev.data.message));
        }
      };
      worker.addEventListener("message", onMsg);
      const msg: WorkerInMsg = { id, type: "coupledStream", req };
      worker.postMessage(msg);
    });
  }

  terminate(): void {
    this.worker?.terminate();
    this.worker = null;
    this.ready = null;
  }
}

export const pyodideEngine = new PyodideEngine();
