/**
 * El único punto de entrada al motor de simulación.
 *
 * El simulador corre el mismo núcleo Python de dos maneras: dentro del
 * navegador vía Pyodide (`engine: "local"`, el default) o contra el servidor
 * FastAPI (`engine: "api"`). Cuál se usa es una decisión de configuración, no
 * algo que cada página deba resolver.
 *
 * Hasta agosto de 2026 no era así: había dos módulos, `api.ts` hablaba REST
 * puro sin saber del motor local, y `api-v2.ts` —que sí encapsulaba la
 * decisión— cubría sólo las operaciones de suelo y acoplado. El resultado era
 * que cada página entraba por una puerta distinta: el Sandbox llamaba al worker
 * directo, Compare hacía el `engine === "api" ? … : …` a mano, y las otras dos
 * pasaban por la capa. Los nombres tampoco ayudaban: no había un "v1" y un
 * "v2" de la API — los endpoints de suelo y acoplado conviven con `/simulate`
 * en el mismo servidor.
 *
 * Acá las cinco operaciones deciden igual, en un solo lugar.
 */

import { pyodideEngine } from "@/lib/pyodide-engine";
import type {
  IterationSnapshot,
  LandUseConfig,
  SimulationConfig,
  SimulationResult,
} from "@/lib/types";
import type {
  CoupledRequest,
  CoupledResult,
  LandUseSolveResponse,
  OuterIteration,
} from "@/lib/types-v2";
import { useSimulationStore } from "@/store/simulationStore";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

/** El motor local (Pyodide en el navegador) es el default; ver `simulationStore`. */
function motorLocal(): boolean {
  return useSimulationStore.getState().engine === "local";
}

async function postJson<T>(
  ruta: string,
  cuerpo: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const r = await fetch(`${API_BASE}${ruta}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
    signal,
  });
  if (!r.ok) throw new Error(`${ruta} falló (${r.status}): ${await r.text()}`);
  return (await r.json()) as T;
}

/** Lee un stream de Server-Sent Events y llama `onEvento` por cada `data:`. */
async function leerSse<T>(
  ruta: string,
  cuerpo: unknown,
  onEvento: (dato: T) => void,
  signal?: AbortSignal,
): Promise<void> {
  const r = await fetch(`${API_BASE}${ruta}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
    signal,
  });
  if (!r.ok || !r.body) throw new Error(`${ruta} falló (${r.status})`);

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    const partes = buffer.split("\n\n");
    buffer = partes.pop() ?? "";
    for (const parte of partes) {
      if (parte.startsWith("event: done")) return;
      const linea = parte.split("\n").find((l) => l.startsWith("data:"));
      const json = linea?.slice(5).trim();
      if (json) onEvento(JSON.parse(json) as T);
    }
  }
}

// ---------------------------------------------------------------------------
// Transporte
// ---------------------------------------------------------------------------

/**
 * Corre el equilibrio de transporte emitiendo cada iteración del MSA.
 *
 * Con el motor local el streaming es real —el worker emite un `postMessage` por
 * iteración y la ciudad se redibuja mientras converge, que es medio punto del
 * simulador—. Contra la API no hay endpoint de streaming para transporte, así
 * que la corrida es de una sola vez y `onIteracion` recibe las iteraciones al
 * final, desde el resultado. Quien llame ve la misma firma en los dos casos.
 */
export async function simularTransporte(
  config: SimulationConfig,
  onIteracion: (snap: IterationSnapshot) => void,
  signal?: AbortSignal,
  landUse?: LandUseConfig,
  localizacion?: "equilibrio" | "original",
): Promise<SimulationResult> {
  if (motorLocal()) {
    return pyodideEngine.simulateStream(
      config,
      onIteracion,
      signal,
      landUse,
      localizacion,
    );
  }
  // `/simulate` no recibe uso de suelo: por esta ruta la población es la de
  // densidad plana (C-02). Es una diferencia real entre motores, no un bug.
  const resultado = await postJson<SimulationResult>(
    "/simulate",
    config,
    signal,
  );
  resultado.iteraciones.forEach(onIteracion);
  return resultado;
}

// ---------------------------------------------------------------------------
// Uso de suelo
// ---------------------------------------------------------------------------

export async function resolverUsoDeSuelo(
  req: {
    L: number;
    CBD: number;
    /** Largo físico de la ciudad (km): T y densidad van en unidades físicas (D-26). */
    largo_km: number;
    land_use: LandUseConfig;
  },
  signal?: AbortSignal,
): Promise<LandUseSolveResponse> {
  if (motorLocal()) return pyodideEngine.solveLandUse(req, signal);
  return postJson<LandUseSolveResponse>("/land-use/solve", req, signal);
}

// ---------------------------------------------------------------------------
// Loop acoplado suelo ↔ transporte
// ---------------------------------------------------------------------------

export async function resolverAcoplado(
  req: CoupledRequest,
): Promise<CoupledResult> {
  if (motorLocal()) {
    // El worker sólo expone la variante en streaming; el resultado completo se
    // arma juntando las iteraciones exteriores.
    const iteraciones: OuterIteration[] = [];
    await pyodideEngine.solveCoupledStream(req, (it) => iteraciones.push(it));
    const última = iteraciones.at(-1);
    return {
      converged:
        última?.T_residual != null && última.T_residual < req.outer_tol,
      iterations: iteraciones,
      // El worker no reconstruye la ciudad final; sólo la usa la vista de
      // parcelas del motor api.
      final_parcelas: [],
      S: null,
    };
  }
  return postJson<CoupledResult>("/coupled/solve", req);
}

export async function resolverAcopladoStream(
  req: CoupledRequest,
  onIteracionExterior: (it: OuterIteration) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (motorLocal()) {
    return pyodideEngine.solveCoupledStream(req, onIteracionExterior, signal);
  }
  return leerSse("/coupled/stream", req, onIteracionExterior, signal);
}
