import type { SimulationConfig, SimulationResult } from "@/lib/types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function runSimulation(config: SimulationConfig): Promise<SimulationResult> {
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

export type IterationEvent = SimulationResult["iteraciones"][number];

export async function runSimulationStream(
  config: SimulationConfig,
  onIteration: (it: IterationEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const r = await fetch(`${API_BASE}/simulate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
    signal,
  });
  if (!r.ok || !r.body) {
    throw new Error(`simulate/stream failed (${r.status})`);
  }

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
      onIteration(JSON.parse(json) as IterationEvent);
    }
  }
}
