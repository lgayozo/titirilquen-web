/**
 * Dónde y por qué el frontend se aparta de los defaults del núcleo.
 *
 * Los valores por defecto vienen generados desde Pydantic (`lib/gen/`), pero
 * la aplicación no arranca exactamente con ellos: hay seis diferencias
 * deliberadas, casi todas por interactividad en el navegador.
 *
 * Antes vivían como una lista de excepciones dentro del test de contrato
 * (`e2e/contract.spec.ts`), donde funcionaban como permiso para que el drift
 * no fallara. Acá son lo que realmente son: la configuración inicial de la
 * app, escrita a mano, sobre una base generada que no puede desincronizarse.
 *
 * Si aparece una diferencia que NO está en este archivo, es drift.
 */

import {
  DEFAULTS_CORE,
  DEFAULTS_LAND_USE_CORE,
  ESTRATOS_CALIBRADOS,
} from "@/lib/gen/defaults.gen";
import type { LandUseConfig, SimulationConfig } from "@/lib/gen/tipos.gen";

/** Población total del escenario base: 1.800 hab/km × 20 km. */
const POBLACION_BASE = 36_000;

/** Mezcla socioeconómica 20/50/30 (alto/medio/bajo). */
const SHARES = [0.2, 0.5, 0.3] as const;

export const defaultSimulationConfig: SimulationConfig = {
  ...DEFAULTS_CORE,
  city: {
    ...DEFAULTS_CORE.city,
    // El núcleo conserva la grilla del modelo original (1.001 celdas). En el
    // navegador cada iteración se dibuja en vivo, así que 201 celdas
    // (Δx ≈ 100 m) es el punto donde la resolución sigue siendo suficiente y
    // la simulación se siente instantánea.
    n_celdas: 201,
    // El núcleo trae la escala liviana del paper (500 hab/km). La app usa la
    // del preset «Base»: por debajo de ~1.800 el corredor no se congestiona y
    // la BPR del auto queda plana, con lo que mover la oferta no cambia nada y
    // el ejercicio pierde sentido (S-03).
    densidad_hab_km: 1800,
  },
  demand: {
    ...DEFAULTS_CORE.demand,
    estratos: ESTRATOS_CALIBRADOS,
  },
  // Semilla fija: dos corridas con la misma configuración deben dar el mismo
  // número, o comparar escenarios es imposible.
  seed: 42,
  // El núcleo conserva el Monte Carlo del original. La app reparte por flujos
  // esperados: es el mismo modelo sin ruido de muestreo, y sin ruido las
  // curvas de sensibilidad se leen.
  assignment: "expected",
};

export const defaultLandUseConfig: LandUseConfig = {
  ...DEFAULTS_LAND_USE_CORE,
  // El núcleo conserva la escala del paper (99.900 hogares). La app usa 36.000
  // en sync con `city.densidad_hab_km`, repartidos según SHARES.
  H_por_estrato: [
    POBLACION_BASE * SHARES[0],
    POBLACION_BASE * SHARES[1],
    POBLACION_BASE * SHARES[2],
  ],
  // Punto fijo del suelo: menos presupuesto de iteraciones en el navegador.
  // Con tol = 1e-8 converge mucho antes, así que el tope no muerde.
  max_iter: 2000,
};

/** La demanda calibrada, suelta — la usan el panel de calibración y los
 *  presets para reconstruir un estrato. */
export const defaultDemandConfig = defaultSimulationConfig.demand;
