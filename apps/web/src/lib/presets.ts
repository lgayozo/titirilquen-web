/**
 * Presets de ciudad y de política.
 *
 * Eran un espejo a mano de `titirilquen_core.presets`: unos 77 valores que
 * había que mover en dos lugares cada vez que se recalibraba. Hoy se generan.
 *
 * La regla de siempre sigue vigente y ahora tiene test en el core
 * (`test_presets.py`): los presets declaran valores ABSOLUTOS, no diferencias
 * contra el default. Si una política omite un parámetro, aplicarla NO lo
 * restaura — hereda el del escenario vigente, y eso ya causó cuatro incidentes.
 * Excepción: pistas y ciclovía se aplican a la escala de la ciudad
 * (`capacidadPolitica`).
 */

import {
  CITY_PRESETS,
  POLICY_PRESETS,
  type CityPresetName,
  type PolicyPresetName,
  type PolicyPresetValues,
} from "@/lib/gen/presets.gen";
import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";

export { CITY_PRESETS, POLICY_PRESETS } from "@/lib/gen/presets.gen";
export type {
  CityPresetName,
  CityPresetValues,
  PolicyPresetName,
  PolicyPresetValues,
} from "@/lib/gen/presets.gen";

/**
 * Dónde vive cada parámetro de política dentro de `SimulationConfig`.
 *
 * El preset declara `parking`, la config lo guarda en
 * `demand.globales.costo_parking`: este mapa es la única traducción entre los
 * dos vocabularios. Vive acá y no en la galería porque hay dos consumidores —
 * la galería, que muestra los valores, y la tabla de agregados, que necesita
 * NOMBRAR el escenario de una corrida ya hecha.
 */
export const LEE_POLITICA: Record<
  keyof PolicyPresetValues,
  (c: SimulationConfig) => number
> = {
  num_pistas: (c) => c.supply.car.num_pistas,
  parking: (c) => c.demand.globales.costo_parking,
  bencina: (c) => c.demand.globales.costo_combustible_km,
  peaje: (c) => c.demand.globales.peaje_km,
  factor_flota: (c) => c.demand.globales.factor_flota_auto,
  num_estaciones: (c) => c.supply.train.num_estaciones,
  frec_max: (c) => c.supply.train.frec_max,
  cap_tren: (c) => c.supply.train.capacidad_tren,
  tarifa: (c) => c.demand.globales.costo_tarifa_metro,
  cap_bici: (c) => c.supply.bike.capacidad_pista,
};

/**
 * Qué preset de política describe a esta config, o `null` si ninguno.
 *
 * Es la IDENTIDAD DERIVADA del escenario: la config no guarda de qué preset
 * viene —aplicar uno copia valores y se olvida del nombre—, así que la única
 * forma de rotular una corrida es reconocerla por sus parámetros.
 *
 * `Personalizado` se excluye a propósito: declara cero campos y `every` sobre
 * una lista vacía es `true`, o sea que matchearía con TODO y sería siempre el
 * primer resultado.
 *
 * La ciudad la reconoce `ciudadActiva`, que necesita además el uso de suelo.
 * Con `lu` la política se compara A LA ESCALA de esa ciudad (pistas y
 * ciclovía, ver `capacidadPolitica`); sin él, a la de Base.
 */
export function politicaActiva(
  cfg: SimulationConfig,
  lu?: LandUseConfig,
): PolicyPresetName | null {
  const escala = escalaCiudad(lu ? ciudadActiva(cfg, lu) : null);
  return (
    Object.entries(POLICY_PRESETS).find(([nombre, v]) => {
      if (nombre === "Personalizado") return false;
      const esperado = { ...v, ...capacidadPolitica(v, escala) };
      return (Object.keys(v) as (keyof PolicyPresetValues)[]).every(
        (k) => LEE_POLITICA[k](cfg) === esperado[k],
      );
    })?.[0] ?? null
  );
}

/** La política de referencia: sus pistas y ciclovía definen la escala 1. */
const REFERENCIA = POLICY_PRESETS.Base as Required<
  Pick<PolicyPresetValues, "num_pistas" | "cap_bici">
>;

/**
 * Pistas y ciclovía de la ESCALA de una ciudad: las que declara su preset
 * (Base, Ciudad con metro, Metrópolis) o, si no declara escala (Compacta,
 * Dispersa, ninguna), las de Base.
 */
export function escalaCiudad(ciudad: CityPresetName | null): {
  num_pistas: number;
  cap_bici: number;
} {
  const c = ciudad ? CITY_PRESETS[ciudad] : undefined;
  return {
    num_pistas: c?.num_pistas ?? REFERENCIA.num_pistas,
    cap_bici: c?.cap_bici ?? REFERENCIA.cap_bici,
  };
}

/**
 * Pistas y ciclovía que una política fija a una escala dada (auditoría A3,
 * oct-2026). Las políticas declaran sus valores para Base (4 pistas, 6.000
 * bici/h); a otra escala se lee su INTENSIDAD: la razón contra Base. Pro-Auto
 * es ×1,25 pistas y ×0,5 ciclovía; Ciclorrecreovía convierte un cuarto de las
 * pistas y multiplica la ciclovía ×2,4.
 *
 * Antes la política fijaba los absolutos y pisaba la escala de la ciudad:
 * Metrópolis + cualquier política volvía a 4 pistas (v/c del auto 2,5-2,9) y el
 * mismo par ciudad-política cambiaba hasta 15,6 pp de metro según el orden de
 * los clics. Con la razón, el resultado es f(ciudad, política) en cualquier
 * orden, y en Base no cambia nada.
 */
export function capacidadPolitica(
  pol: PolicyPresetValues,
  escala: { num_pistas: number; cap_bici: number },
): Partial<Pick<PolicyPresetValues, "num_pistas" | "cap_bici">> {
  return {
    ...(pol.num_pistas !== undefined && {
      num_pistas: Math.max(
        1,
        Math.round(
          (escala.num_pistas * pol.num_pistas) / REFERENCIA.num_pistas,
        ),
      ),
    }),
    ...(pol.cap_bici !== undefined && {
      cap_bici: Math.round(
        (escala.cap_bici * pol.cap_bici) / REFERENCIA.cap_bici,
      ),
    }),
  };
}

/**
 * Qué preset de ciudad describe a esta config, o `null` si ninguno.
 *
 * Necesita el uso de suelo porque dos de las cuatro dimensiones de la forma
 * urbana viven ahí: la concentración de la oferta (σ) y la población (ΣH). La
 * densidad NO se compara — es derivada (ρ = ΣH/largo), así que compararla sería
 * pedir dos veces lo mismo y fallar por redondeo.
 *
 * Tampoco compara `num_pistas`, aunque los presets de escala lo FIJEN: las
 * pistas son un parámetro de política, y meterlas en el match acoplaba las dos
 * identidades — aplicar «Pro-Auto» (3 pistas) hacía que la ciudad dejara de
 * reconocerse y pasara a «Personalizada» sin que la ciudad hubiera cambiado.
 * Fijar un valor y usarlo para identificar son cosas distintas. Base y
 * Metrópolis, que comparten geometría, se distinguen por `poblacion`.
 *
 * Compacta y Dispersa no declaran `poblacion` a propósito: son iso-población y
 * matchean con la que el usuario tenga.
 */
export function ciudadActiva(
  cfg: SimulationConfig,
  lu: LandUseConfig,
): CityPresetName | null {
  const sumaH = lu.H_por_estrato.reduce((a, b) => a + b, 0);
  return (
    Object.entries(CITY_PRESETS).find(
      ([nombre, v]) =>
        nombre !== "Personalizado" &&
        cfg.city.largo_ciudad_km === v.largo_ciudad &&
        (v.sigma === undefined || lu.oferta_sigma_frac === v.sigma) &&
        (v.poblacion === undefined || Math.round(sumaH) === v.poblacion),
    )?.[0] ?? null
  );
}
