import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { test, expect } from "@playwright/test";

import { supplyVector } from "../src/lib/citySupply";
import { defaultDemandConfig } from "../src/lib/defaults";
import { calcularUtilidades, type TiemposObservados } from "../src/lib/utility";

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

/**
 * El espejo de LÓGICA que no se pudo eliminar.
 *
 * `lib/utility.ts` reimplementa a mano `demand/utility.py`. A diferencia de los
 * tipos y los defaults —que hoy se generan— y del bienestar —que se movió al
 * núcleo en F5—, esta función se evalúa mientras el usuario arrastra un slider
 * del inspector de utilidad. Cruzar al worker de Pyodide en cada movimiento
 * significaría rondas asíncronas y un estado de "motor cargando" en un widget
 * puramente didáctico, así que se conserva la copia y se pinea.
 *
 * Ya no alimenta ningún indicador: desde F5 el bienestar lo calcula el núcleo.
 * Si esto driftara, el daño se limita a que el inspector muestre una utilidad
 * que no es la que el modelo usó — sigue siendo un error, pero acotado.
 */
test.describe("contrato utility.ts ↔ utility.py", () => {
  const { cases } = read("utility-golden.json") as {
    cases: Array<{
      estrato: 1 | 2 | 3;
      celda: number;
      dist_km: number;
      tiene_auto: boolean;
      tiempos: TiemposObservados;
      utilidades: Record<string, { valor: number; feasible: boolean }>;
    }>;
  };

  for (const c of cases) {
    test(`estrato=${c.estrato} celda=${c.celda} auto=${c.tiene_auto}`, () => {
      const utils = calcularUtilidades({
        estrato: c.estrato,
        distKm: c.dist_km,
        tieneAuto: c.tiene_auto,
        config: defaultDemandConfig,
        tiempos: c.tiempos,
      });
      for (const [modo, esperado] of Object.entries(c.utilidades)) {
        const obtenido = utils[modo as keyof typeof utils];
        expect(obtenido, `modo ${modo}`).toBeTruthy();
        expect(obtenido!.feasible, `${modo}.feasible`).toBe(esperado.feasible);
        // Sólo tiene sentido comparar el valor de un modo factible: el
        // infactible lleva el centinela −9999 en los dos lados.
        if (esperado.feasible) {
          expect(obtenido!.valor, `${modo}.valor`).toBeCloseTo(
            esperado.valor,
            9,
          );
        }
      }
    });
  }
});
