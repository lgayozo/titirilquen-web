import type {
  CoupledRequest,
  CoupledResult,
  LandUseConfig,
  LandUseSolveResponse,
  OuterIteration,
} from "@/lib/types-v2";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function solveLandUse(req: {
  L: number;
  CBD: number;
  land_use: LandUseConfig;
}): Promise<LandUseSolveResponse> {
  const r = await fetch(`${API_BASE}/land-use/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) throw new Error(`land-use/solve failed (${r.status}): ${await r.text()}`);
  return (await r.json()) as LandUseSolveResponse;
}

export async function solveCoupled(req: CoupledRequest): Promise<CoupledResult> {
  const r = await fetch(`${API_BASE}/coupled/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) throw new Error(`coupled/solve failed (${r.status}): ${await r.text()}`);
  return (await r.json()) as CoupledResult;
}

export async function solveCoupledStream(
  req: CoupledRequest,
  onOuter: (it: OuterIteration) => void,
  signal?: AbortSignal
): Promise<void> {
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

export const defaultLandUseConfig: LandUseConfig = {
  H_por_estrato: [1000, 4000, 5000],
  estratos: [
    { y: 120, lambda: 1, alpha: 1.3, rho: 1 },
    { y: 50, lambda: 1, alpha: 1.2, rho: 1 },
    { y: 10, lambda: 1, alpha: 1.1, rho: 1 },
  ],
  beta: 1,
  solver: "logit",
  tol: 1e-8,
  max_iter: 2000,
};
