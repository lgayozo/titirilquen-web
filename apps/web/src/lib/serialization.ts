/**
 * Import/export de configuración del simulador.
 *
 * Formato de archivo `.ttrq.json`:
 * ```json
 * {
 *   "$schema": "titirilquen-scenario/v1",
 *   "name": "Mi escenario",
 *   "config": { ...SimulationConfig }
 * }
 * ```
 *
 * URL-state: `?s=<base64url(JSON.stringify(config))>` — sin compresión
 * adicional; el config completo pesa ~3 KB, manejable en URL.
 */

import type { SimulationConfig } from "@/lib/types";

export const TTRQ_SCHEMA = "titirilquen-scenario/v1";
export const TTRQ_EXT = ".ttrq.json";

export interface TtrqFile {
  $schema: typeof TTRQ_SCHEMA;
  name?: string;
  description?: string;
  config: SimulationConfig;
}

export function serializeToJson(config: SimulationConfig, name?: string): string {
  const file: TtrqFile = {
    $schema: TTRQ_SCHEMA,
    ...(name ? { name } : {}),
    config,
  };
  return JSON.stringify(file, null, 2);
}

export function parseTtrqJson(raw: string): TtrqFile {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    throw new Error(`Archivo no es JSON válido: ${e instanceof Error ? e.message : String(e)}`);
  }
  if (typeof data !== "object" || data === null) {
    throw new Error("El archivo no contiene un objeto JSON.");
  }
  const obj = data as Record<string, unknown>;
  if (obj.$schema !== TTRQ_SCHEMA) {
    throw new Error(
      `Esquema desconocido: ${String(obj.$schema)}. Esperado: "${TTRQ_SCHEMA}".`
    );
  }
  if (typeof obj.config !== "object" || obj.config === null) {
    throw new Error("El archivo no contiene un `config` válido.");
  }
  return obj as unknown as TtrqFile;
}

function base64UrlEncode(s: string): string {
  return btoa(unescape(encodeURIComponent(s)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function base64UrlDecode(s: string): string {
  const padded = s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4);
  return decodeURIComponent(escape(atob(padded)));
}

export function configToUrlParam(config: SimulationConfig): string {
  return base64UrlEncode(JSON.stringify(config));
}

export function configFromUrlParam(param: string): SimulationConfig {
  const raw = base64UrlDecode(param);
  return JSON.parse(raw) as SimulationConfig;
}

export function downloadFile(filename: string, content: string, mime = "application/json"): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error("read failed"));
    reader.readAsText(file);
  });
}
