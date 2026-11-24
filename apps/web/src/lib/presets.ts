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
  type CityPresetValues,
  type PolicyPresetName,
  type PolicyPresetValues,
} from "@/lib/gen/presets.gen";
import { defaultLandUseConfig, defaultSimulationConfig } from "@/lib/defaults";
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
  bencina: (c) => c.demand.globales.precio_combustible_clp_l,
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
 * o, si no hay ciudad reconocible, las de Base.
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
 * Los cuatro presets declaran `poblacion` (nov-2026): un preset es un
 * escenario completo.
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

/** El escenario que corre una página: la config de simulación y la de suelo. */
export interface Escenario {
  config: SimulationConfig;
  landUse: LandUseConfig;
}

/**
 * El escenario de un par ciudad-política, armado DESDE LA BASE.
 *
 * Elegir un preset no parcha la config que haya: la reconstruye desde los
 * valores de fábrica y le aplica la ciudad y la política pedidas. Así dos
 * corridas del mismo preset son la misma corrida, se haya pasado antes por
 * donde se haya pasado, que es lo que hace falta para comparar resultados.
 *
 * Hasta nov-2026 el preset pisaba sólo los parámetros que declaraba, y todo lo
 * demás —una pendiente movida a mano, otro tope de iteraciones, la población de
 * la ciudad anterior— se heredaba en silencio.
 *
 * Lo único que se conserva de `actual` es la CALIBRACIÓN, que no describe un
 * escenario sino el modelo con que se comparan todos: los estratos de la
 * demanda (betas, tenencia de auto, teletrabajo), los cortes de caminata y
 * bici, los precios sociales y el ingreso de cada estrato. Es lo mismo que
 * conserva `applyJointPreset`.
 *
 * `null` en ciudad o en política significa «la de Base».
 */
export function escenarioDesdeBase(
  actual: Escenario,
  ciudad: CityPresetName | null,
  politica: PolicyPresetName | null,
): Escenario {
  const c: CityPresetValues = (ciudad && CITY_PRESETS[ciudad]) || {};
  const p: PolicyPresetValues = (politica && POLICY_PRESETS[politica]) || {};
  const base = defaultSimulationConfig;
  // Pistas y ciclovía: las de la política, leídas a la escala de la ciudad.
  const escala = escalaCiudad(ciudad);
  const cap = { ...escala, ...capacidadPolitica(p, escala) };

  const config: SimulationConfig = {
    ...base,
    precios_sociales: actual.config.precios_sociales,
    city: {
      ...base.city,
      ...(c.largo_ciudad !== undefined && { largo_ciudad_km: c.largo_ciudad }),
    },
    supply: {
      ...base.supply,
      car: { ...base.supply.car, num_pistas: cap.num_pistas },
      bike: { ...base.supply.bike, capacidad_pista: cap.cap_bici },
      train: {
        ...base.supply.train,
        ...(p.num_estaciones !== undefined && {
          num_estaciones: p.num_estaciones,
        }),
        ...(p.frec_max !== undefined && { frec_max: p.frec_max }),
        ...(p.cap_tren !== undefined && { capacidad_tren: p.cap_tren }),
      },
    },
    demand: {
      ...base.demand,
      estratos: actual.config.demand.estratos,
      globales: {
        ...base.demand.globales,
        corte_caminata_min: actual.config.demand.globales.corte_caminata_min,
        corte_bici_min: actual.config.demand.globales.corte_bici_min,
        ...(p.tarifa !== undefined && { costo_tarifa_metro: p.tarifa }),
        ...(p.parking !== undefined && { costo_parking: p.parking }),
        ...(p.bencina !== undefined && { precio_combustible_clp_l: p.bencina }),
        ...(p.peaje !== undefined && { peaje_km: p.peaje }),
        ...(p.factor_flota !== undefined && {
          factor_flota_auto: p.factor_flota,
        }),
      },
    },
  };

  const lu = defaultLandUseConfig;
  // La población del preset reparte ΣH con la composición de fábrica. Enteros
  // (`tuple[int, int, int]` en Pydantic); el tercero absorbe el redondeo para
  // que ΣH dé exacto, o `ciudadActiva` no reconocería su propio preset.
  const [h1, h2, h3] = lu.H_por_estrato;
  const total = c.poblacion ?? h1 + h2 + h3;
  const k = total / (h1 + h2 + h3 || 1);
  const a = Math.round(h1 * k);
  const b = Math.round(h2 * k);
  const landUse: LandUseConfig = {
    ...lu,
    ...(c.sigma !== undefined && { oferta_sigma_frac: c.sigma }),
    H_por_estrato: [a, b, total - a - b],
    // El ingreso es calibración; ρ es del escenario y vuelve al de fábrica.
    estratos: lu.estratos.map((e, i) => ({
      ...e,
      y: actual.landUse.estratos[i]?.y ?? e.y,
    })) as LandUseConfig["estratos"],
  };

  return { config, landUse };
}

/** JSON con las claves ordenadas: dos objetos iguales dan el mismo texto
 *  aunque se hayan armado en otro orden (un escenario importado, p. ej.). */
function canonico(v: unknown): string {
  return JSON.stringify(v, (_k, x: unknown) =>
    x && typeof x === "object" && !Array.isArray(x)
      ? Object.fromEntries(
          Object.entries(x as Record<string, unknown>).sort(([a], [b]) =>
            a < b ? -1 : a > b ? 1 : 0,
          ),
        )
      : x,
  );
}

/**
 * ¿El escenario tiene ajustes hechos a mano por fuera de sus presets?
 *
 * Se arma el escenario que sus presets reconocidos darían desde la base y se
 * compara entero. Si difiere, comparar esta corrida con otra «del mismo
 * preset» no es comparar lo mismo, y la galería lo avisa.
 */
export function tieneAjustesManuales(actual: Escenario): boolean {
  const limpio = escenarioDesdeBase(
    actual,
    ciudadActiva(actual.config, actual.landUse),
    politicaActiva(actual.config, actual.landUse),
  );
  return canonico(limpio) !== canonico(actual);
}
