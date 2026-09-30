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

  // B. λ y el valor del tiempo. Con α = 1 común, el valor del tiempo es α/λ:
  // igualar los λ lo iguala para todos y la ciudad se invierte (medido con la
  // config de la app: alto 5,5 km, bajo 2,2 km). Los λ se escalan desde el
  // default, que está en útiles por peso (~10⁻³): un valor absoluto como 0,5
  // sería mil veces el de calibración.
  lambda_iguales: {
    to: "/land-use",
    build: () => {
      const l = lu();
      const medio = l.estratos[1]!.lambda;
      l.estratos[0]!.lambda = medio;
      l.estratos[2]!.lambda = medio;
      return { landUse: l };
    },
  },
  lambda_alto_doble: {
    to: "/land-use",
    build: () => {
      const l = lu();
      l.estratos[0]!.lambda *= 2;
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

  // D. Efecto Alonso y su inversión. α es común y vale 1 (D-34): la inversión
  // se produce con la penalización por densidad, que entra dividida por λ y
  // castiga más en pesos al estrato alto. Con ρ = 0,03 en los tres (el tope de
  // la interfaz) el alto pasa a 5,8 km y el bajo a 2,8 km.
  alonso_base: {
    to: "/land-use",
    build: () => ({ landUse: lu() }),
  },
  alonso_invertido: {
    to: "/land-use",
    build: () => {
      const l = lu();
      for (const e of l.estratos) e.rho = 0.03;
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
