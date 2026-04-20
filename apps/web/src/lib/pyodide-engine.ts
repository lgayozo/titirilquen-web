/**
 * Wrapper de alto nivel sobre el Web Worker de Pyodide. Expone una API
 * simétrica a `api.ts` (engine=api) para que el store no necesite saber qué
 * motor está detrás.
 */

import type { IterationSnapshot, SimulationConfig, SimulationResult } from "@/lib/types";

type WorkerOutMsg =
  | { id: string; type: "ready" }
  | { id: string; type: "iteration"; snapshot: IterationSnapshot }
  | { id: string; type: "done"; result: SimulationResult }
  | { id: string; type: "error"; message: string };

type WorkerInMsg =
  | { id: string; type: "init" }
  | { id: string; type: "simulate"; config: SimulationConfig }
  | { id: string; type: "simulateStream"; config: SimulationConfig };

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

  terminate(): void {
    this.worker?.terminate();
    this.worker = null;
    this.ready = null;
  }
}

export const pyodideEngine = new PyodideEngine();
