/**
 * Escenarios de las actividades guiadas del tutorial (cap. 7) — F-02.
 *
 * Cada escenario parte de los DEFAULTS (no de la config viva): la actividad
 * asume un estado inicial reproducible. El botón <LoadScenario id=…> de los
 * MDX aplica el estado a los stores y navega al módulo correspondiente.
 */

import { defaultLandUseConfig } from "@/lib/api-v2";
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
  // Escalera alrededor del nuevo default ($2.500). Los ids no llevan la cifra
  // a propósito: antes eran `parking_3k`/`_6k`/`_15k` y quedaron mintiendo al
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
    build: () => ({ sim: sim() }), // default = $2.500
  },
  parking_alto: {
    to: "/sandbox",
    build: () => {
      const s = sim();
      s.demand.globales.costo_parking = 10000;
      return { sim: s };
    },
  },

  // B. El artefacto del logit (λ del estrato alto)
  lambda_alto_05: {
    to: "/land-use",
    build: () => {
      const l = lu();
      l.estratos[0]!.lambda = 0.5;
      return { landUse: l };
    },
  },
  lambda_alto_3: {
    to: "/land-use",
    build: () => {
      const l = lu();
      l.estratos[0]!.lambda = 3;
      return { landUse: l };
    },
  },

  // C. Capacidad de ciclovía
  bici_base: {
    to: "/sandbox",
    build: () => ({ sim: sim() }), // default = 800 bici/h
  },
  bici_probici: {
    to: "/sandbox",
    build: () => {
      const s = sim();
      s.supply.bike.capacidad_pista = 5000;
      return { sim: s };
    },
  },

  // D. Efecto Alonso (α por estrato, utiles/min)
  alonso_directo: {
    to: "/land-use",
    build: () => {
      const l = lu();
      l.estratos[0]!.alpha = 12;
      l.estratos[2]!.alpha = 3;
      return { landUse: l };
    },
  },
  alonso_invertido: {
    to: "/land-use",
    build: () => {
      const l = lu();
      l.estratos[0]!.alpha = 3;
      l.estratos[2]!.alpha = 12;
      return { landUse: l };
    },
  },

  // E. Sensibilidad al MSA
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
      s.max_iter = 20;
      return { sim: s };
    },
  },
};
