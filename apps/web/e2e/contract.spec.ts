import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { test, expect } from "@playwright/test";

import { supplyVector } from "../src/lib/citySupply";

/**
 * Contrato anti-drift core ↔ frontend. Corre en Node (sin browser).
 *
 * Queda UN espejo que vigilar: `citySupply.ts` reimplementa a mano las formas
 * de oferta del núcleo para poder redibujar la vista previa a 60 fps sin
 * cruzar al worker. Este test lo compara contra el fixture golden que genera
 * Python. Si el core cambia, pytest falla primero y el fixture se regenera
 * (`uv run --extra dev python tests/test_contract_frontend.py`); si ESTE test
 * falla con fixtures vigentes, el espejo TS driftó.
 *
 * La paridad de DEFAULTS vivía también acá, con una lista de divergencias
 * permitidas que funcionaba como salvoconducto para el drift. Ya no hace
 * falta: los defaults del frontend se generan desde Pydantic
 * (`lib/gen/defaults.gen.ts`) y las diferencias deliberadas son código a la
 * vista en `lib/overrides.ts`. Que los generados estén al día lo verifica el
 * CI con `npm run sync:core && git diff --exit-code`.
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
      const S = supplyVector(
        c.forma,
        c.L,
        c.CBD,
        c.sigma_frac,
        c.forma_param,
        c.N,
      );
      expect(S).toEqual(c.S);
    });
  }
});
