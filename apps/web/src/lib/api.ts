import type { SimulationConfig, SimulationResult } from "@/lib/types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function runSimulation(
  config: SimulationConfig,
): Promise<SimulationResult> {
  const r = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`simulate failed (${r.status}): ${err}`);
  }
  return (await r.json()) as SimulationResult;
}
