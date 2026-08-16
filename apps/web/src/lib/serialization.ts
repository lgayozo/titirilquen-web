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
  // `b_tiempo_acceso` se separó de `b_tiempo_caminata` (ago-2026): antes un solo
  // coeficiente pesaba el acceso al metro Y el modo caminata completo. Es campo
  // REQUERIDO en el core, así que un escenario viejo sin él no valida. Se rellena
  // con el valor que tenía el coeficiente único, que es exactamente lo que ese
  // escenario usaba para el acceso: la migración conserva su comportamiento.
  const estratos = (
    config as unknown as {
      demand?: {
        estratos?: Record<string, { betas?: Record<string, unknown> }>;
      };
    }
  ).demand?.estratos;
  if (estratos) {
    for (const s of Object.values(estratos)) {
      const b = s?.betas;
      if (b && !("b_tiempo_acceso" in b) && "b_tiempo_caminata" in b) {
        b.b_tiempo_acceso = b.b_tiempo_caminata;
      }
    }
  }
  const globales = (
    config as unknown as { demand?: { globales?: Record<string, unknown> } }
  ).demand?.globales;
  if (globales && "factor_emision_auto" in globales) {
    // Era un parámetro HUÉRFANO (0.18, nadie lo leía): las emisiones salían de
    // la curva COPERT. Se reemplaza por `factor_flota_auto`, un multiplicador
    // adimensional sobre esa curva. No hay conversión posible —el valor viejo
    // no tenía efecto ni unidades comparables—, así que se adopta el default.
    delete globales.factor_emision_auto;
    if (!("factor_flota_auto" in globales)) {
      globales.factor_flota_auto = 1;
    }
  }
  if (globales && "factor_emision_metro" in globales) {
    // D-29: el metro emite por tren-km, no por pax·km. No hay conversión
    // automática (requiere el factor de carga); se adopta el default nuevo.
    delete globales.factor_emision_metro;
    if (!("factor_emision_metro_tren_km" in globales)) {
      globales.factor_emision_metro_tren_km = 2.5;
    }
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

/** Migraciones sobre el `land_use` importado. Mismo motivo que `migrateConfig`:
 * el core valida con `extra="forbid"`, así que un campo eliminado hace fallar
 * la importación de escenarios guardados. Muta y devuelve el mismo objeto. */
function migrateLandUse(landUse: LandUseConfig): LandUseConfig {
  const lu = landUse as unknown as Record<string, unknown>;
  if ("solver" in lu) {
    // El campo ofrecía un segundo solver como «corrección» del λ heterogéneo y
    // no lo era: dejaba λ inerte. Se eliminó del core; queda un único solver
    // (logit), con su limitación de λ documentada y sin corregir (D-08).
    delete lu.solver;
  }
  return landUse;
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
  if (obj.$schema !== TTRQ_SCHEMA && obj.$schema !== TTRQ_SCHEMA_V1) {
    throw new Error(
      `Esquema desconocido: ${String(obj.$schema)}. Esperado: "${TTRQ_SCHEMA}" (o v1).`,
    );
  }
  if (typeof obj.config !== "object" || obj.config === null) {
    throw new Error("El archivo no contiene un `config` válido.");
  }
  const file = obj as unknown as TtrqFile;
  migrateConfig(file.config);
  if (file.land_use) migrateLandUse(file.land_use);
  return file;
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

/** Decodifica `?s=`. Acepta el formato v2 `{config, land_use?, coupled?}` y el
 * legado (un `SimulationConfig` plano, reconocible por su clave `city`). */
export function scenarioFromUrlParam(param: string): ScenarioPayload {
  const raw = base64UrlDecode(param);
  const data = JSON.parse(raw) as Record<string, unknown>;
  if (typeof data.config === "object" && data.config !== null) {
    const payload = data as unknown as ScenarioPayload;
    migrateConfig(payload.config);
    if (payload.land_use) migrateLandUse(payload.land_use);
    return payload;
  }
  // Legado: el JSON ES el SimulationConfig.
  const config = migrateConfig(data as unknown as SimulationConfig);
  return { config };
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
