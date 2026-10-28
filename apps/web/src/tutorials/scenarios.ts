/**
 * Escenarios de las actividades guiadas del tutorial (cap. 7) — F-02.
 *
 * Cada escenario parte de los DEFAULTS (no de la config viva): la actividad
 * asume un estado inicial reproducible. El botón <LoadScenario id=…> de los
 * MDX aplica el estado a los stores y navega al módulo correspondiente.
 */

import { defaultLandUseConfig } from "@/lib/defaults";
import { defaultSimulationConfig } from "@/lib/defaults";
import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";

export interface TutorialScenario {
  /** Ruta del módulo donde ocurre la actividad. */
  to: "/sandbox" | "/land-use";
  build: () => { sim?: SimulationConfig; landUse?: LandUseConfig };
}

const sim = (): SimulationConfig => structuredClone(defaultSimulationConfig);
const lu = (): LandUseConfig => structuredClone(defaultLandUseConfig);

export const TUTORIAL_SCENARIOS: Record<string, TutorialScenario> = {
  // A. Efecto del precio del parking
  // Escalera alrededor del default vigente. Los ids no llevan la cifra a
  // propósito: antes eran `parking_3k`/`_6k`/`_15k` y quedaron mintiendo al
  // recalibrar el default.
  parking_bajo: {
    to: "/sandbox",
    build: () => {
      const s = sim();
      s.demand.globales.costo_parking = 0;
      return { sim: s };
    },
  },
  parking_base: {
    to: "/sandbox",
    build: () => ({ sim: sim() }),
  },
  parking_alto: {
    to: "/sandbox",
    build: () => {
      const s = sim();
      s.demand.globales.costo_parking = 5000;
      return { sim: s };
    },
  },

  // B. λ y el valor del tiempo. λ_h = |b_costo_h| (schema v6): se mueve
  // desde la demanda, y con él la accesibilidad T, que también depende de
  // b_costo. Las cifras que citan los MDX salen de replicar estos escenarios
  // en el núcleo: docs/libro/datos/tutoriales.json (datos_tutoriales.py).
  // Devuelven también el suelo por defecto, para partir de un estado
  // reproducible en los dos módulos.
  lambda_iguales: {
    to: "/land-use",
    build: () => {
      const s = sim();
      const medio = s.demand.estratos[2].betas.b_costo;
      s.demand.estratos[1].betas.b_costo = medio;
      s.demand.estratos[3].betas.b_costo = medio;
      return { sim: s, landUse: lu() };
    },
  },
  lambda_alto_doble: {
    to: "/land-use",
    build: () => {
      const s = sim();
      s.demand.estratos[1].betas.b_costo *= 2;
      return { sim: s, landUse: lu() };
    },
  },

  // C. Capacidad de ciclovía
  bici_base: {
    to: "/sandbox",
    build: () => ({ sim: sim() }), // default del núcleo (6.000 bici/h)
  },
  bici_probici: {
    to: "/sandbox",
    build: () => {
      const s = sim();
      // El valor del preset Pro-Bici (presets.py), el doble del default de
      // 6.000. Con 5.000 sobre el default de 4.000 casi no movía nada.
      s.supply.bike.capacidad_pista = 12000;
      return { sim: s };
    },
  },

  // D. Efecto Alonso y su inversión. La accesibilidad entra con peso 1 (D-34):
  // la inversión se produce con la penalización por densidad, que entra
  // dividida por λ y castiga más en pesos al estrato alto. ρ = 54 en los tres
  // (utiles-mes sobre la densidad relativa, schema v7; es el 0,03 por hog/km de
  // v6 con 1.800 hog/km). La inversión y su umbral, medidos en
  // docs/libro/datos/tutoriales.json.
  alonso_base: {
    to: "/land-use",
    build: () => ({ sim: sim(), landUse: lu() }),
  },
  alonso_invertido: {
    to: "/land-use",
    build: () => {
      const l = lu();
      for (const e of l.estratos) e.rho = 54;
      return { sim: sim(), landUse: l };
    },
  },

  // E. Sensibilidad al MSA: el tope corto contra el default (150 desde
  // oct-2026; antes 40, y el largo era 20, que significaba BAJAR el tope).
  msa_corto: {
    to: "/sandbox",
    build: () => {
      const s = sim();
      s.max_iter = 3;
      return { sim: s };
    },
  },
  msa_largo: {
    to: "/sandbox",
    build: () => {
      const s = sim();
      s.max_iter = 150;
      return { sim: s };
    },
  },
};
