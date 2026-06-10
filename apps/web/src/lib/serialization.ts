/**
 * Import/export de escenarios del simulador.
 *
 * Formato de archivo `.ttrq.json` (v2 — el v1 sigue siendo importable):
 * ```json
 * {
 *   "$schema": "titirilquen-scenario/v2",
 *   "name": "Mi escenario",
 *   "config": { ...SimulationConfig },
 *   "land_use": { ...LandUseConfig },          // opcional
 *   "coupled": { "poblacion": 25000, "outer_max_iter": 12 }  // opcional
 * }
 * ```
 * v1 (`titirilquen-scenario/v1`) solo trae `config` (transporte).
 *
 * URL-state: `?s=<base64url(JSON)>`. v2 codifica el escenario completo
 * `{config, land_use?, coupled?}`; los links viejos (config plano) se siguen
 * aceptando.
 */

import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";

export const TTRQ_SCHEMA_V1 = "titirilquen-scenario/v1";
export const TTRQ_SCHEMA = "titirilquen-scenario/v2";
export const TTRQ_EXT = ".ttrq.json";

export interface CoupledPrefs {
  poblacion: number;
  outer_max_iter: number;
}

export interface ScenarioPayload {
  config: SimulationConfig;
  land_use?: LandUseConfig;
  coupled?: CoupledPrefs;
}

export interface TtrqFile extends ScenarioPayload {
  $schema: typeof TTRQ_SCHEMA | typeof TTRQ_SCHEMA_V1;
  name?: string;
  description?: string;
}

/** Migraciones de compatibilidad sobre el `config` importado: descarta campos
 * que existieron en versiones anteriores (el core los rechaza con
 * `extra="forbid"`). Muta y devuelve el mismo objeto. */
function migrateConfig(config: SimulationConfig): SimulationConfig {
  const city = (config as unknown as { city?: Record<string, unknown> }).city;
  if (city && "ingresos_estratos" in city) {
    delete city.ingresos_estratos; // parámetro muerto, eliminado del core (A3)
  }
  if (city && "densidad_por_celda" in city && !("densidad_hab_km" in city)) {
    // D-28: la densidad pasó de hab/celda a hab/km. Conversión fiel: preserva
    // la población total que tenía el escenario (densidad·(N−1)/largo).
    const n = Number(city.n_celdas) || 201;
    const largo = Number(city.largo_ciudad_km) || 20;
    const dpc = Number(city.densidad_por_celda) || 50;
    city.densidad_hab_km = Math.max(1, Math.round((dpc * (n - 1)) / largo));
    delete city.densidad_por_celda;
  }
  return config;
}

export function serializeToJson(
  config: SimulationConfig,
  name?: string,
  extras?: { land_use?: LandUseConfig; coupled?: CoupledPrefs },
): string {
  const file: TtrqFile = {
    $schema: TTRQ_SCHEMA,
    ...(name ? { name } : {}),
    config,
    ...(extras?.land_use ? { land_use: extras.land_use } : {}),
    ...(extras?.coupled ? { coupled: extras.coupled } : {}),
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
  if (obj.$schema !== TTRQ_SCHEMA && obj.$schema !== TTRQ_SCHEMA_V1) {
    throw new Error(
      `Esquema desconocido: ${String(obj.$schema)}. Esperado: "${TTRQ_SCHEMA}" (o v1).`
    );
  }
  if (typeof obj.config !== "object" || obj.config === null) {
    throw new Error("El archivo no contiene un `config` válido.");
  }
  const file = obj as unknown as TtrqFile;
  migrateConfig(file.config);
  return file;
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

/** Codifica el escenario completo para `?s=` (config + suelo + coupled). */
export function scenarioToUrlParam(payload: ScenarioPayload): string {
  return base64UrlEncode(JSON.stringify(payload));
}

/** Decodifica `?s=`. Acepta el formato v2 `{config, land_use?, coupled?}` y el
 * legado (un `SimulationConfig` plano, reconocible por su clave `city`). */
export function scenarioFromUrlParam(param: string): ScenarioPayload {
  const raw = base64UrlDecode(param);
  const data = JSON.parse(raw) as Record<string, unknown>;
  if (typeof data.config === "object" && data.config !== null) {
    const payload = data as unknown as ScenarioPayload;
    migrateConfig(payload.config);
    return payload;
  }
  // Legado: el JSON ES el SimulationConfig.
  const config = migrateConfig(data as unknown as SimulationConfig);
  return { config };
}

/** @deprecated usar `scenarioToUrlParam` (links legados siguen decodificando). */
export function configToUrlParam(config: SimulationConfig): string {
  return scenarioToUrlParam({ config });
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
