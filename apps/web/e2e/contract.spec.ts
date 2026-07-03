import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { test, expect } from "@playwright/test";

import { supplyVector } from "../src/lib/citySupply";
import {
  defaultLandUseConfig,
  defaultSimulationConfig,
} from "../src/lib/defaults";

/**
 * Contrato anti-drift core ↔ frontend (Fase 5). Corre en Node (sin browser):
 *
 * 1. `citySupply.ts` duplica deliberadamente las formas de oferta del core
 *    (preview a 60fps); este test lo compara contra el fixture golden generado
 *    por Python. Si el core cambia, pytest falla primero y el fixture se
 *    regenera (`uv run --extra dev python tests/test_contract_frontend.py`);
 *    si ESTE test falla con fixtures vigentes, el espejo TS driftó.
 *
 * 2. Paridad de defaults TS ↔ Pydantic: misma estructura de claves (detecta
 *    renames como ingresos_estratos/densidad_hab_km/factor_emision_*) y mismos
 *    valores salvo las divergencias INTENCIONALES listadas abajo.
 */

const FIXTURES = join(dirname(fileURLToPath(import.meta.url)), "fixtures");
const read = (name: string) =>
  JSON.parse(readFileSync(join(FIXTURES, name), "utf-8"));

test.describe("contrato citySupply ↔ supply.py", () => {
  const { cases } = read("supply-golden.json") as {
    cases: Array<{
      forma: Parameters<typeof supplyVector>[0];
      L: number;
      CBD: number;
      N: number;
      sigma_frac: number;
      forma_param: number;
      S: number[];
    }>;
  };

  for (const c of cases) {
    test(`forma=${c.forma} L=${c.L} σ=${c.sigma_frac}`, () => {
      const S = supplyVector(c.forma, c.L, c.CBD, c.sigma_frac, c.forma_param, c.N);
      expect(S).toEqual(c.S);
    });
  }
});

/** Divergencias intencionales y documentadas entre los defaults Pydantic (py)
 * y los del frontend (ts). Cualquier OTRA diferencia es drift y falla. */
const ALLOWED: Record<string, { py: unknown; ts: unknown }> = {
  // El frontend usa una grilla liviana por interactividad; el core conserva la
  // resolución del modelo original.
  "city.n_celdas": { py: 1001, ts: 201 },
  // El frontend corta por residual (pedagógico); el core respeta el original
  // (solo max_iter) salvo que se pida tolerancia.
  "sim.tolerance": { py: 0, ts: 0.1 },
  // El frontend fija la semilla para reproducibilidad de la demo.
  "sim.seed": { py: null, ts: 42 },
  // Población de suelo: el core conserva la escala del paper (99.900); el
  // frontend usa 10.000 para que el acoplado sea interactivo.
  "land_use.H_por_estrato.0": { py: 33300, ts: 1000 },
  "land_use.H_por_estrato.1": { py: 33300, ts: 4000 },
  "land_use.H_por_estrato.2": { py: 33300, ts: 5000 },
  // Punto fijo del suelo: presupuesto menor en el navegador.
  "land_use.max_iter": { py: 10000, ts: 2000 },
};

function flatten(obj: unknown, prefix = "", out: Record<string, unknown> = {}) {
  if (obj !== null && typeof obj === "object") {
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      flatten(v, prefix ? `${prefix}.${k}` : k, out);
    }
  } else {
    out[prefix] = obj;
  }
  return out;
}

test.describe("paridad de defaults TS ↔ Pydantic", () => {
  const golden = read("defaults-golden.json").defaults as Record<string, unknown>;
  const ts = {
    city: defaultSimulationConfig.city,
    supply: defaultSimulationConfig.supply,
    globales: defaultSimulationConfig.demand.globales,
    sim: {
      max_iter: defaultSimulationConfig.max_iter,
      tolerance: defaultSimulationConfig.tolerance,
      seed: defaultSimulationConfig.seed,
      assignment: defaultSimulationConfig.assignment,
      modos_habilitados: defaultSimulationConfig.modos_habilitados,
    },
    land_use: defaultLandUseConfig,
  };

  const flatPy = flatten(golden);
  const flatTs = flatten(ts);

  test("misma estructura de claves (detecta renames)", () => {
    const pyKeys = Object.keys(flatPy).sort();
    const tsKeys = Object.keys(flatTs).sort();
    expect(tsKeys).toEqual(pyKeys);
  });

  test("mismos valores salvo divergencias intencionales", () => {
    const diffs: string[] = [];
    for (const key of Object.keys(flatPy)) {
      const py = flatPy[key];
      const tsV = flatTs[key];
      const allowed = ALLOWED[key];
      if (allowed) {
        if (py !== allowed.py || tsV !== allowed.ts) {
          diffs.push(
            `${key}: divergencia permitida desactualizada (py=${py}, ts=${tsV}, esperado py=${allowed.py}, ts=${allowed.ts})`,
          );
        }
      } else if (py !== tsV) {
        diffs.push(`${key}: py=${py} ≠ ts=${tsV}`);
      }
    }
    expect(diffs, diffs.join("\n")).toEqual([]);
  });
});
