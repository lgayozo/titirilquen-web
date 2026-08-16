/**
 * Import/export de escenarios del simulador.
 *
 * Formato de archivo `.ttrq.json`:
 * ```json
 * {
 *   "$schema": "titirilquen-scenario/v3",
 *   "name": "Mi escenario",
 *   "config": { ...SimulationConfig },
 *   "land_use": { ...LandUseConfig },          // opcional
 *   "coupled": { "poblacion": 25000, "outer_max_iter": 12 }  // opcional
 * }
 * ```
 * URL-state: `?s=<base64url(JSON)>` con el mismo objeto.
 *
 * SIN MIGRACIONES, a propósito
 * ----------------------------
 * Hubo aquí cinco migraciones que rellenaban o descartaban campos para que un
 * escenario viejo siguiera validando contra el core (`extra="forbid"` rechaza
 * cualquier clave que sobre). Se retiraron en agosto de 2026 junto con la
 * limpieza del esquema: mantenerlas obliga a arrastrar para siempre la
 * historia de cada parámetro que alguna vez existió, y este es un simulador
 * educativo cuyos escenarios se rehacen en minutos, no un sistema con datos
 * que no se pueden perder.
 *
 * La consecuencia es explícita: un archivo o link anterior a v3 falla al
 * importarse, con un mensaje que dice por qué. Si algún día hay escenarios que
 * de verdad importe conservar, la decisión se revisa — y entonces el lugar
 * correcto es un migrador versionado, no cinco parches sueltos.
 */

import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";

export const TTRQ_SCHEMA = "titirilquen-scenario/v3";
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
  $schema: typeof TTRQ_SCHEMA;
  name?: string;
  description?: string;
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
    throw new Error(
      `Archivo no es JSON válido: ${e instanceof Error ? e.message : String(e)}`,
    );
  }
  if (typeof data !== "object" || data === null) {
    throw new Error("El archivo no contiene un objeto JSON.");
  }
  const obj = data as Record<string, unknown>;
  if (obj.$schema !== TTRQ_SCHEMA) {
    throw new Error(
      `Este escenario es de una versión anterior del simulador ` +
        `(${String(obj.$schema)}; se espera "${TTRQ_SCHEMA}") y ya no se puede ` +
        `importar. El esquema cambió en agosto de 2026: se retiraron parámetros ` +
        `que ningún cálculo leía. Vuelve a exportarlo desde la versión actual.`,
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
  const padded =
    s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4);
  return decodeURIComponent(escape(atob(padded)));
}

/** Codifica el escenario completo para `?s=` (config + suelo + coupled). */
export function scenarioToUrlParam(payload: ScenarioPayload): string {
  return base64UrlEncode(JSON.stringify(payload));
}

/** Decodifica `?s=` — formato `{config, land_use?, coupled?}`.
 *
 * Los links generados antes de agosto de 2026 llevan campos que el core ya no
 * acepta (`extra="forbid"`), así que fallarán al validar. Es deliberado: ver
 * la nota sobre migraciones más arriba. */
export function scenarioFromUrlParam(param: string): ScenarioPayload {
  const raw = base64UrlDecode(param);
  const data = JSON.parse(raw) as Record<string, unknown>;
  if (typeof data.config !== "object" || data.config === null) {
    throw new Error("El link no contiene un escenario válido.");
  }
  return data as unknown as ScenarioPayload;
}

export function downloadFile(
  filename: string,
  content: string,
  mime = "application/json",
): void {
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
