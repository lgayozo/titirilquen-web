import { pyodideEngine } from "@/lib/pyodide-engine";
import { useSimulationStore } from "@/store/simulationStore";
import type {
  CoupledRequest,
  CoupledResult,
  LandUseConfig,
  LandUseSolveResponse,
  OuterIteration,
} from "@/lib/types-v2";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

function engineIsLocal(): boolean {
  return useSimulationStore.getState().engine === "local";
}

export async function solveLandUse(
  req: {
    L: number;
    CBD: number;
    /** Largo físico de la ciudad (km): T y densidad usan unidades físicas (D-26). */
    largo_km: number;
    land_use: LandUseConfig;
  },
  signal?: AbortSignal,
): Promise<LandUseSolveResponse> {
  if (engineIsLocal()) return pyodideEngine.solveLandUse(req, signal);
  const r = await fetch(`${API_BASE}/land-use/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  if (!r.ok)
    throw new Error(`land-use/solve failed (${r.status}): ${await r.text()}`);
  return (await r.json()) as LandUseSolveResponse;
}

export async function solveCoupled(
  req: CoupledRequest,
): Promise<CoupledResult> {
  if (engineIsLocal()) {
    const collected: OuterIteration[] = [];
    await pyodideEngine.solveCoupledStream(req, (it) => collected.push(it));
    const last = collected[collected.length - 1];
    return {
      converged:
        last != null &&
        last.T_residual != null &&
        last.T_residual < req.outer_tol,
      iterations: collected,
      final_parcelas: [],
      S: null,
    };
  }
  const r = await fetch(`${API_BASE}/coupled/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok)
    throw new Error(`coupled/solve failed (${r.status}): ${await r.text()}`);
  return (await r.json()) as CoupledResult;
}

export async function solveCoupledStream(
  req: CoupledRequest,
  onOuter: (it: OuterIteration) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (engineIsLocal()) return pyodideEngine.solveCoupledStream(req, onOuter, signal);
  const r = await fetch(`${API_BASE}/coupled/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  if (!r.ok || !r.body) throw new Error(`coupled/stream failed (${r.status})`);

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      if (part.startsWith("event: done")) return;
      const dataLine = part.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const json = dataLine.slice(5).trim();
      if (!json) continue;
      onOuter(JSON.parse(json) as OuterIteration);
    }
  }
}

// Re-export: la definición vive en defaults.ts (módulo puro, sin engine) para
// que los tests de contrato puedan importarla desde Node.
export { defaultLandUseConfig } from "@/lib/defaults";
