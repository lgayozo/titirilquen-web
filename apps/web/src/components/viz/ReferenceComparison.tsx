import { Fragment } from "react";
import { useTranslation } from "react-i18next";

import { PorQue } from "@/components/ui/PorQue";
import { SaberMas, type FuenteNucleo } from "@/components/ui/SaberMas";
import { CaptionTabla } from "@/components/viz/CaptionTabla";
import {
  agregadosDe,
  bienestarComparable,
  type Agregados,
} from "@/lib/agregados";
import { ciudadActiva, politicaActiva } from "@/lib/presets";
import type {
  SimulationConfig,
  SimulationResult,
  StratumId,
} from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";
import { fmtDecimal, fmtEntero, fmtPesos } from "@/lib/modos";

/**
 * Comparación contra la corrida FIJADA como referencia, dentro del propio
 * módulo de transporte: «corro un escenario, lo fijo, corro otro y veo el
 * delta» sin salir de la página.
 *
 * Muestra los AGREGADOS de ciudad completa —persona-minutos, tiempo medio,
 * costo generalizado y excedente— que son los únicos con los que se puede
 * afirmar que una política mejora al sistema. Los promedios por modo que ya
 * estaban en la tabla no sirven para eso: un modo puede mejorar mientras el
 * conjunto empeora.
 */

const STRATA: StratumId[] = [1, 2, 3];
/** Orden canónico de `constantes.MODOS`. El reparto se muestra en ese orden
 *  para que coincida con el de las figuras y el de la tabla de métricas. */
const MODOS = ["Auto", "Metro", "Bici", "Caminata"] as const;

interface Props {
  config: SimulationConfig;
  /** El uso de suelo de ESTA corrida. Hace falta para nombrar la ciudad: σ y ΣH
   *  no están en `SimulationConfig`. */
  landUse: LandUseConfig | null;
  result: SimulationResult;
  reference: {
    config: SimulationConfig;
    landUse: LandUseConfig | null;
    result: SimulationResult;
  } | null;
}

const fmtMin = (v: number) => `${fmtDecimal(v)} min`;
// El signo va ANTES del símbolo: «−$3.331», no «$-3.331».
const fmtMoney = (v: number) => fmtPesos(v);
const fmtMiles = (v: number) => fmtEntero(v);
// Un share se escribe en «%» y su delta en puntos porcentuales: escribir el
// delta como «%» invitaría a leerlo como variación relativa.
const fmtPct = (v: number) => `${fmtDecimal(v)} %`;
const fmtPuntos = (v: number) => `${fmtDecimal(v)} pp`;

/** Los cinco bloques de la tabla, en orden de lectura.
 *
 *  La lista era plana: conteos, tiempos, costos percibidos, transferencias y
 *  excedentes uno tras otro, sin nada que dijera qué se puede sumar con qué.
 *  Lo importante es el último bloque: el costo de recursos y el excedente del
 *  consumidor son DOS CAMINOS a la misma pregunta —cuánto beneficia esta
 *  política—, y sumarlos cuenta dos veces. */
type Grupo = "fisico" | "recursos" | "usuario" | "transferencias" | "beneficio";

const GRUPOS: Grupo[] = [
  "fisico",
  "recursos",
  "usuario",
  "transferencias",
  "beneficio",
];

/** Los dos enfoques del bloque de beneficios, cada uno con su subtítulo. */
type Subgrupo = "ahorro_recursos" | "excedente_consumidor";

const SUBGRUPOS: Subgrupo[] = ["ahorro_recursos", "excedente_consumidor"];

interface FilaAgg {
  label: string;
  grupo: Grupo;
  /** Sólo en «beneficio»: por cuál de los dos enfoques se mide. */
  subgrupo?: Subgrupo;
  /** La ecuación de la métrica y dónde se calcula en el núcleo. */
  saber?: {
    ecuacion: string;
    simbolos: [string, string][];
    fuente: FuenteNucleo;
  };
  actual: number;
  ref: number | null;
  fmt: (v: number) => string;
  /** Formato del Δ, cuando no es el del nivel (el share: % y pp). */
  fmtDelta?: (v: number) => string;
  /** true ⇒ bajar es mejor (tiempos y costos). Solo colorea, no juzga. */
  menorEsMejor: boolean;
  /** Δ sin color: la fila no tiene dirección buena. Un share modal que sube no
   *  es una mejora —más metro no es automáticamente mejor, depende de a costa
   *  de qué—, y pintarlo de verde o rojo sería el simulador opinando. */
  neutra?: boolean;
  /** Si `false`, se muestra el valor pero NO el delta. */
  comparable?: boolean;
  /** Unidad, cuando la fila NO es un total de ciudad —o cuando está pegada a
   *  una que no lo es. El excedente por estrato es un promedio por persona y
   *  quedaba al lado de un total, con el mismo formato y sin nada que lo
   *  dijera: tres órdenes de magnitud de diferencia leídos como si fueran
   *  comparables. */
  unidad?: string;
  nota?: string;
  /** Explicación de la nota, plegada en un «¿por qué?» (B3). */
  porque?: string;
  /** Excedente o bienestar: su cero es arbitrario. Sin referencia se rotula
   *  «nivel», para que nadie lea el número solo. */
  nivel?: boolean;
  /** La cifra principal de la tabla. Hay dos medidas de bienestar que pueden
   *  tener signo opuesto; sin una marcada, no se sabe cuál es «el resultado». */
  destacada?: boolean;
}

export function ReferenceComparison({
  config,
  landUse,
  result,
  reference,
}: Props) {
  const { t } = useTranslation("simulator");
  // Los agregados los calcula el núcleo y vienen en el resultado; acá sólo se
  // leen y se restan contra la referencia que el usuario haya fijado.
  const agg = agregadosDe(result);
  const aggRef = reference ? agregadosDe(reference.result) : null;
  if (!agg) return null;

  // El excedente es el logsum: la única medida desde que el modelo tiene un
  // solo método de carga (nov-2026).
  const excedentePorEstrato = agg.excedente_por_estrato_clp;
  const excedenteRefPorEstrato = aggRef?.excedente_por_estrato_clp;
  // El Δ del excedente sólo es un cambio de bienestar si las dos corridas
  // comparten el cero del nivel (modos, β, teletrabajo y población:
  // `bienestarComparable`). Si no, se muestra el nivel, no el Δ.
  const razon =
    reference && aggRef
      ? bienestarComparable(
          { config, landUse },
          { config: reference.config, landUse: reference.landUse },
        )
      : null;
  const excedenteComparable = razon == null;

  // Los precios sociales son configuración (cambian cada año). Las filas en
  // pesos sociales muestran los de ESTA corrida, y si la referencia se corrió
  // con otros, su Δ mezclaría política y precios: no se muestra.
  const ps = config.precios_sociales;
  // Los costos unitarios de inversión son calibración igual que los precios:
  // con otros, el Δ también mezclaría política y supuestos.
  const preciosIguales =
    !reference ||
    (JSON.stringify(ps) === JSON.stringify(reference.config.precios_sociales) &&
      JSON.stringify(config.inversion) ===
        JSON.stringify(reference.config.inversion));
  const precio = {
    anio: ps.vigencia,
    vot: fmtMoney(ps.vst_viaje_clp_h),
    combustible: fmtMoney(ps.combustible_auto_clp_l),
    lubricante: fmtMoney(ps.lubricante_auto_clp_l),
    neumatico: fmtMoney(ps.neumatico_auto_clp),
    vehiculo: fmtMoney(ps.vehiculo_auto_clp),
    mantencion: fmtMoney(ps.mantencion_clp_h),
    carbono: fmtMoney(ps.carbono_clp_t),
    iri: ps.iri,
    mercado: fmtMoney(config.demand.globales.precio_combustible_clp_l),
    // Qué parte de lo pagado es impuesto: resulta de los dos precios.
    impuesto:
      config.demand.globales.precio_combustible_clp_l > 0
        ? Math.round(
            (1 -
              ps.combustible_auto_clp_l /
                config.demand.globales.precio_combustible_clp_l) *
              100,
          )
        : 0,
  };

  const filas: FilaAgg[] = [
    {
      // El denominador va PRIMERO y explícito: los shares de abajo se calculan
      // sobre esta cifra, y entre dos escenarios puede cambiar (el teletrabajo
      // no viaja). Sin la fila, un share que sube sin que nadie cambie de modo
      // —porque el denominador bajó— se lee como sustitución modal.
      label: t("agg.viajes_fisicos"),
      grupo: "fisico",
      saber: {
        ecuacion: String.raw`V \;=\; \sum_{h}\sum_{m}\sum_{i} d_{hmi}`,
        simbolos: [
          [String.raw`d_{hmi}`, t("agg.sim.d")],
          [String.raw`h,\; m,\; i`, t("agg.sim.hmi")],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "calcular_agregados" },
      },
      actual: agg.viajeros,
      ref: aggRef?.viajeros ?? null,
      fmt: fmtMiles,
      menorEsMejor: false,
      neutra: true,
      nota: t("agg.viajes_fisicos_nota"),
    },
    {
      // D14: quien no tiene ningún modo factible no está en los viajeros ni
      // en el excedente. Sin esta fila, una política que deja gente sin
      // alternativas se leería como un bienestar apenas más bajo.
      label: t("agg.varados"),
      grupo: "fisico",
      saber: {
        ecuacion: String.raw`\#\{\, n \;:\; m_n = \varnothing \,\}`,
        simbolos: [[String.raw`m_n`, t("agg.sim.modo_n")]],
        fuente: { archivo: "bienestar.py", simbolo: "varados" },
      },
      actual: agg.varados,
      ref: aggRef?.varados ?? null,
      fmt: fmtMiles,
      menorEsMejor: true,
      nota: t("agg.varados_nota"),
    },
    ...MODOS.map((m) => ({
      label: t("agg.reparto_modo", { modo: t(`modes.${m.toLowerCase()}`) }),
      grupo: "fisico" as Grupo,
      saber: {
        ecuacion: String.raw`s_m \;=\; V_m \,/\, V`,
        simbolos: [
          [String.raw`V_m`, t("agg.sim.vm")],
          [String.raw`V`, t("agg.sim.v")],
        ] as [string, string][],
        fuente: { archivo: "bienestar.py", simbolo: "viajes_por_modo" },
      },
      actual: share(agg.viajes_por_modo[m], agg.viajeros),
      ref: aggRef ? share(aggRef.viajes_por_modo[m], aggRef.viajeros) : null,
      fmt: fmtPct,
      fmtDelta: fmtPuntos,
      menorEsMejor: false,
      neutra: true,
    })),
    {
      // Va con los eventos físicos: son kilos, no pesos. Su valor al precio
      // social del carbono es otra fila, en «Consumo de recursos».
      label: t("agg.co2"),
      grupo: "fisico",
      actual: result.emisiones_total_kg,
      ref: reference?.result.emisiones_total_kg ?? null,
      fmt: fmtMiles,
      menorEsMejor: true,
      unidad: t("agg.u_co2"),
      nota: t("agg.co2_nota", {
        auto: fmtMiles(result.emisiones_auto_kg),
        metro: fmtMiles(result.emisiones_metro_kg),
      }),
    },
    {
      label: t("agg.tiempo_total"),
      grupo: "recursos",
      saber: {
        ecuacion: String.raw`T \;=\; \sum_{h,m,i} d_{hmi}\; t_{mi}`,
        simbolos: [
          [String.raw`t_{mi}`, t("agg.sim.t_mi")],
          [String.raw`T`, t("agg.sim.T")],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "tiempo_total_min" },
      },
      actual: agg.tiempo_total_min,
      ref: aggRef?.tiempo_total_min ?? null,
      fmt: fmtMiles,
      menorEsMejor: true,
    },
    {
      label: t("agg.tiempo_medio"),
      grupo: "recursos",
      saber: {
        ecuacion: String.raw`\bar t \;=\; T \,/\, V`,
        simbolos: [[String.raw`\bar t`, t("agg.sim.t_medio")]],
        fuente: { archivo: "bienestar.py", simbolo: "tiempo_medio_min" },
      },
      actual: agg.tiempo_medio_min,
      ref: aggRef?.tiempo_medio_min ?? null,
      fmt: fmtMin,
      menorEsMejor: true,
    },
    {
      label: t("agg.cg_percibido"),
      grupo: "usuario",
      saber: {
        ecuacion: String.raw`CG \;=\; \sum_{h,m,i} d_{hmi}\left[\frac{\tilde t_{h}}{60}\,VoT_h \;+\; \$_m\right]`,
        simbolos: [
          [String.raw`\tilde t_{h}`, t("agg.sim.t_pond_h")],
          [String.raw`VoT_h`, t("agg.sim.vot_h")],
          [String.raw`\$_m`, t("agg.sim.dinero")],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "cg_percibido" },
      },
      actual: agg.costo_generalizado_percibido_clp,
      ref: aggRef?.costo_generalizado_percibido_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.cg_percibido_nota"),
    },
    {
      label: t("agg.cg_social"),
      grupo: "usuario",
      saber: {
        ecuacion: String.raw`CG_s \;=\; \sum_{h,m,i} d_{hmi}\left[\frac{\tilde t_{\text{SNI}}}{60}\,VST \;+\; \$_m\right]`,
        simbolos: [
          [String.raw`\tilde t_{\text{SNI}}`, t("agg.sim.t_pond_sni")],
          [String.raw`VST`, t("agg.sim.vst")],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "cg_social" },
      },
      actual: agg.costo_generalizado_social_clp,
      ref: aggRef?.costo_generalizado_social_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      comparable: preciosIguales,
      nota: t("agg.cg_social_nota", precio),
    },
    {
      label: t("agg.recaudacion"),
      grupo: "transferencias",
      saber: {
        ecuacion: String.raw`R \;=\; R_{\text{park}} + R_{\text{peaje}} + R_{\text{tarifa}} + R_{\text{bencina}}`,
        simbolos: [[String.raw`R`, t("agg.sim.R")]],
        fuente: { archivo: "bienestar.py", simbolo: "rec_parking" },
      },
      actual:
        agg.recaudacion_parking_clp +
        agg.recaudacion_peaje_clp +
        agg.recaudacion_tarifa_clp +
        agg.recaudacion_combustible_clp,
      ref:
        aggRef == null
          ? null
          : aggRef.recaudacion_parking_clp +
            aggRef.recaudacion_peaje_clp +
            aggRef.recaudacion_tarifa_clp +
            aggRef.recaudacion_combustible_clp,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: preciosIguales,
      nota: t("agg.recaudacion_nota"),
    },
    {
      // La parte de la bencina que NO es recurso: lo que paga el conductor
      // menos esto es lo que de verdad se consume. Va aparte, además de
      // dentro del total de arriba, porque es la única recaudación que sale
      // de un supuesto (la fracción de impuesto) y no de una tarifa del modelo.
      label: t("agg.impuesto_bencina"),
      grupo: "transferencias",
      saber: {
        ecuacion: String.raw`R_{\text{bencina}} \;=\; \left(P_{\text{mercado}} - PS_{\text{comb}}\right) \, L`,
        simbolos: [
          [String.raw`L`, t("agg.sim.litros")],
          [String.raw`P_{\text{mercado}}`, t("agg.sim.p_mercado", precio)],
          [String.raw`PS_{\text{comb}}`, t("agg.sim.ps_comb", precio)],
        ],
        fuente: {
          archivo: "bienestar.py",
          simbolo: "recaudacion_combustible_clp",
        },
      },
      actual: agg.recaudacion_combustible_clp,
      ref: aggRef?.recaudacion_combustible_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: preciosIguales,
      nota: t("agg.impuesto_bencina_nota", precio),
    },
    {
      // Los MISMOS litros con que cada conductor eligió modo, a precio social
      // (Precios Sociales, tabla 4.3). El consumo es uno solo en todo el
      // modelo: a precio de mercado da lo pagado, y la diferencia es el
      // impuesto, que está en «Transferencias».
      label: t("agg.costo_operacion_auto"),
      grupo: "recursos",
      saber: {
        ecuacion: String.raw`C_{\text{comb}} \;=\; PS_{\text{comb}} \, L \qquad L \;=\; \sum_{\text{auto}} d \; \text{km} \; cm(\bar v) \; \phi`,
        simbolos: [
          [String.raw`PS_{\text{comb}}`, t("agg.sim.ps_comb", precio)],
          [String.raw`L`, t("agg.sim.litros")],
          [String.raw`cm(\bar v)`, t("agg.sim.cm_v")],
          [String.raw`\phi`, t("agg.sim.phi_flota")],
        ],
        fuente: {
          archivo: "bienestar.py",
          simbolo: "recursos_combustible_clp",
        },
      },
      actual: agg.recursos_combustible_clp,
      ref: aggRef?.recursos_combustible_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      comparable: preciosIguales,
      nota: t("agg.costo_operacion_auto_nota", precio),
    },
    {
      // Los «otros costos de operación» del MESPIVU (ec. 13.1.1-7). El modelo
      // no tiene rugosidad del pavimento, así que es un piso.
      label: t("agg.otros_operacion_auto"),
      grupo: "recursos",
      saber: {
        ecuacion: String.raw`C_{\text{otros}} \;=\; \sum_{k} q_k \, L_k \; \frac{CL \cdot VL + CN \cdot VN + CR \cdot VV + CM \cdot VH}{1000}`,
        simbolos: [
          [
            String.raw`CL,\, CN,\, CR,\, CM`,
            t("agg.sim.consumos_otros", precio),
          ],
          [
            String.raw`VL,\, VN,\, VV,\, VH`,
            t("agg.sim.precios_otros", precio),
          ],
        ],
        fuente: {
          archivo: "operacion_vehicular.py",
          simbolo: "otros_costos_operacion_auto_clp_km",
        },
      },
      actual: agg.recursos_otros_operacion_clp,
      ref: aggRef?.recursos_otros_operacion_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      comparable: preciosIguales,
      nota: t("agg.otros_operacion_auto_nota", precio),
    },
    {
      // El costo que faltaba: sin él, ampliar oferta era gratis. Vale cero
      // mientras los costos unitarios estén en cero, y la nota lo dice.
      label: t("agg.costo_inversion"),
      grupo: "recursos",
      saber: {
        ecuacion: String.raw`C_{\text{inv}} \;=\; \frac{K \cdot \dfrac{r}{1 - (1+r)^{-n}}}{H} \qquad K \;=\; \sum_{j} q_j \, c_j`,
        simbolos: [
          [String.raw`K`, t("agg.sim.k_capital")],
          [String.raw`q_j,\, c_j`, t("agg.sim.q_c_inv")],
          [
            String.raw`r,\, n`,
            t("agg.sim.r_n", {
              r: fmtDecimal(ps.tasa_social_descuento * 100, 1),
              n: config.inversion.vida_util_anios,
            }),
          ],
          [
            String.raw`H`,
            t("agg.sim.h_punta", { h: config.inversion.horas_punta_anio }),
          ],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "costo_inversion" },
      },
      actual: agg.costo_inversion_clp,
      ref: aggRef?.costo_inversion_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      comparable: preciosIguales,
      nota:
        agg.inversion_capital_clp === 0
          ? t("agg.costo_inversion_nota_cero")
          : t("agg.costo_inversion_nota", {
              capital: fmtMoney(agg.inversion_capital_clp),
            }),
    },
    {
      label: t("agg.costo_co2"),
      grupo: "recursos",
      saber: {
        ecuacion: String.raw`C_{CO_2} \;=\; E_{CO_2} \times PS_{C}`,
        simbolos: [
          [String.raw`E_{CO_2}`, t("agg.sim.e_co2")],
          [String.raw`PS_{C}`, t("agg.sim.ps_c", precio)],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "costo_co2" },
      },
      actual: agg.costo_co2_clp,
      ref: aggRef?.costo_co2_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      comparable: preciosIguales,
      nota: t("agg.costo_co2_nota", precio),
    },
    {
      label: t("agg.costo_operador"),
      grupo: "recursos",
      saber: {
        ecuacion: String.raw`C_{\text{op}} \;=\; (\text{tren·km}) \times c_{\text{km}}`,
        simbolos: [[String.raw`c_{\text{km}}`, t("agg.sim.c_km")]],
        fuente: { archivo: "bienestar.py", simbolo: "costo_operador" },
      },
      actual: agg.costo_operador_clp,
      ref: aggRef?.costo_operador_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.costo_operador_nota", {
        km: Math.round(agg.tren_km_hora),
      }),
    },
    {
      label: t("agg.subsidio"),
      grupo: "transferencias",
      saber: {
        ecuacion: String.raw`S \;=\; C_{\text{op}}\, f_{\text{punta}} \;-\; R_{\text{tarifa}}`,
        simbolos: [[String.raw`f_{\text{punta}}`, t("agg.sim.f_punta")]],
        fuente: { archivo: "bienestar.py", simbolo: "subsidio_metro_clp" },
      },
      actual: agg.subsidio_metro_clp,
      ref: aggRef?.subsidio_metro_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.subsidio_nota", {
        f: config.supply.train.factor_dia_punta,
      }),
    },
    {
      // EL OTRO ENFOQUE. El costo generalizado y el excedente miran el viaje
      // desde el usuario e incluyen lo que paga aunque ese pago no consuma
      // nada: peaje, parking y tarifa son transferencias. Acá sólo entra lo
      // que la sociedad gasta de verdad, y el tiempo va al VST porque en
      // recursos no tiene sentido que un minuto valga más según quién lo
      // gaste. Es el enfoque del MESPIVU (13.1.1). No es una identidad con
      // el bienestar y pueden discrepar en signo: medido en la base
      // (nov-2026), con Tarificación Vial a 200 $/km el costo de recursos
      // baja 303 mil y el bienestar social baja 727 mil. Por eso los dos
      // están a la vista.
      label: t("agg.costo_recursos"),
      grupo: "beneficio",
      subgrupo: "ahorro_recursos",
      actual: agg.costo_recursos_clp,
      ref: aggRef?.costo_recursos_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      comparable: preciosIguales,
      nota: t("agg.costo_recursos_nota"),
      porque: t("agg.costo_recursos_porque"),
      saber: {
        ecuacion: String.raw`CR \;=\; \underbrace{\sum d\,\frac{\tilde t_{\text{SNI}}}{60}VST}_{\text{tiempo}} \;+\; \underbrace{C_{\text{comb}} + C_{\text{otros}}}_{\text{autos}} \;+\; \underbrace{C_{\text{op}}}_{\text{metro}} \;+\; C_{CO_2} \;+\; C_{\text{inv}}`,
        simbolos: [
          [String.raw`CR`, t("agg.sim.CR")],
          [
            String.raw`C_{\text{comb}},\, C_{\text{otros}},\, C_{\text{op}},\, C_{CO_2}`,
            t("agg.sim.partes_cr"),
          ],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "costo_recursos_clp" },
      },
    },
    {
      // El total que suma el bienestar social, a la vista: sin él, el Δ del
      // bienestar no se podía descomponer en lo que pierde el viajero y lo
      // que vuelve como recaudación.
      label: t("agg.excedente_total"),
      grupo: "beneficio",
      subgrupo: "excedente_consumidor",
      saber: {
        ecuacion: String.raw`EC \;=\; \sum_{h} n_h \,\frac{\overline{\ln \sum_m e^{V_{m}}}}{\lambda_h}`,
        simbolos: [
          [String.raw`\ln \sum_m e^{V_m}`, t("agg.sim.logsum")],
          [String.raw`\lambda_h`, t("agg.sim.lambda_h")],
          [String.raw`n_h`, t("agg.sim.n_h")],
        ],
        fuente: { archivo: "bienestar.py", simbolo: "logsum_de_utilidad" },
      },
      actual: agg.excedente_total_clp,
      ref: aggRef?.excedente_total_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: excedenteComparable,
      unidad: t("agg.u_ciudad"),
      nivel: true,
    },
    {
      label: t("agg.bienestar"),
      grupo: "beneficio",
      subgrupo: "excedente_consumidor",
      saber: {
        ecuacion: String.raw`W \;=\; EC \;+\; R \;-\; C_{\text{op}} \;-\; C_{\text{inv}}`,
        simbolos: [[String.raw`W`, t("agg.sim.W")]],
        fuente: { archivo: "bienestar.py", simbolo: "bienestar_social_clp" },
      },
      actual: agg.bienestar_social_clp,
      ref: aggRef?.bienestar_social_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      // Lleva dentro el excedente, así que hereda su
      // condición de comparabilidad; y la recaudación lleva el impuesto a la
      // bencina, que depende de un parámetro de `precios_sociales`.
      comparable: excedenteComparable && preciosIguales,
      nivel: true,
      destacada: true,
      nota: t("agg.bienestar_nota"),
    },
    {
      // Otra lectura: el MISMO excedente, dividido por un λ común
      // a los estratos (|β_tiempo|·60/VST) en vez del λ_h de cada uno. NO
      // revalúa el tiempo: repondera personas, dinero incluido, por VST/VoT_h
      // (D13, libro cap. 7). La lectura SNI —el tiempo al VST— es `cg_social`.
      // No es redundante: el λ conductual pondera a favor de quien más gana,
      // así que el signo del Δ agregado podría darse vuelta entre las dos.
      label: t("agg.excedente_social"),
      grupo: "beneficio",
      subgrupo: "excedente_consumidor",
      saber: {
        ecuacion: String.raw`EC_s \;=\; \sum_{h} n_h \,\frac{\overline{\ln \sum_m e^{V_m}}}{\lambda_{\text{social}}}, \qquad \lambda_{\text{social}} = \frac{|\beta_t|\cdot 60}{VST}`,
        simbolos: [
          [String.raw`\lambda_{\text{social}}`, t("agg.sim.lambda_social")],
          [String.raw`\beta_t`, t("agg.sim.beta_t")],
        ],
        fuente: {
          archivo: "bienestar.py",
          simbolo: "excedente_social_total_clp",
        },
      },
      actual: agg.excedente_social_total_clp,
      ref: aggRef?.excedente_social_total_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: excedenteComparable && preciosIguales,
      unidad: t("agg.u_ciudad"),
      nivel: true,
      nota: t("agg.excedente_social_corto", precio),
      porque: t("agg.excedente_social_porque"),
    },
    ...STRATA.map((h) => ({
      label: t("agg.excedente_estrato", {
        h: t(`strata.${estratoKey(h)}`),
      }),
      grupo: "beneficio" as Grupo,
      subgrupo: "excedente_consumidor" as Subgrupo,
      saber: {
        ecuacion: String.raw`EC_h \;=\; \frac{\overline{\ln \sum_m e^{V_m}}}{\lambda_h}`,
        simbolos: [[String.raw`EC_h`, t("agg.sim.ec_h")]] as [string, string][],
        fuente: {
          archivo: "bienestar.py",
          simbolo: "excedente_por_estrato_clp",
        },
      },
      actual: excedentePorEstrato[String(h) as "1" | "2" | "3"],
      ref: excedenteRefPorEstrato?.[String(h) as "1" | "2" | "3"] ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: excedenteComparable,
      unidad: t("agg.u_persona"),
      nivel: true,
    })),
  ];

  return (
    <div className="overflow-x-auto">
      <p className="mb-2 text-etiqueta leading-snug text-[var(--muted)]">
        {reference ? t("agg.intro_con_ref") : t("agg.intro_sin_ref")}
      </p>
      {/* `tabla-datos` es el ÚNICO estilo de tabla del módulo (index.css). Antes
          esta usaba serif 14 px y las de métricas mono 11-12 px, una al lado de
          la otra. */}
      <table className="tabla-datos">
        {/* Número y nombre, igual que las figuras llevan `FIG. NN`: sin esto la
            tabla no se puede citar en una guía de clase. */}
        <CaptionTabla n="01" nombre={t("agg.caption")} />
        <thead>
          <tr>
            <th scope="col">{t("agg.metrica")}</th>
            {reference && (
              <th scope="col">
                {t("agg.referencia")}
                <Escenario
                  config={reference.config}
                  landUse={reference.landUse}
                />
              </th>
            )}
            <th scope="col">
              {t("agg.actual")}
              <Escenario config={config} landUse={landUse} />
            </th>
            {reference && <th scope="col">Δ</th>}
          </tr>
        </thead>
        <tbody>
          {GRUPOS.map((g) => {
            const delGrupo = filas
              .filter((f) => f.grupo === g)
              .sort(
                (a, b) =>
                  SUBGRUPOS.indexOf(a.subgrupo as Subgrupo) -
                  SUBGRUPOS.indexOf(b.subgrupo as Subgrupo),
              );
            if (delGrupo.length === 0) return null;
            return (
              <Fragment key={g}>
                <tr className="fila-grupo">
                  <th scope="colgroup" colSpan={reference ? 4 : 2}>
                    {t(`agg.grupo.${g}`)}
                    <span className="grupo-glosa">
                      {t(`agg.grupo.${g}_glosa`, precio)}
                    </span>
                  </th>
                </tr>
                {delGrupo.map((f, i) => {
                  const abreSubgrupo =
                    f.subgrupo != null &&
                    f.subgrupo !== delGrupo[i - 1]?.subgrupo;
                  const d = f.ref == null ? null : f.actual - f.ref;
                  const mostrarDelta = d != null && f.comparable !== false;
                  const neutro = f.neutra === true;
                  const bueno =
                    d == null ? false : f.menorEsMejor ? d < 0 : d > 0;
                  return (
                    <Fragment key={f.label}>
                      {abreSubgrupo && (
                        <tr className="fila-subgrupo">
                          <th scope="colgroup" colSpan={reference ? 4 : 2}>
                            {t(`agg.subgrupo.${f.subgrupo}`)}
                          </th>
                        </tr>
                      )}
                      <tr
                        className={f.destacada ? "fila-destacada" : undefined}
                      >
                        <td>
                          {(() => {
                            // La etiqueta es la misma con o sin desplegable: así
                            // la fila cerrada ocupa exactamente lo que ocupaba
                            // antes de que existiera el «saber más».
                            const etiqueta = (
                              <>
                                {f.label}
                                {f.unidad && (
                                  <span className="celda-unidad ml-1">
                                    {f.unidad}
                                  </span>
                                )}
                                {f.nivel && !reference && (
                                  <span className="celda-unidad ml-1">
                                    {t("agg.u_nivel")}
                                  </span>
                                )}
                                {f.nota && (
                                  <span className="celda-nota ml-1">
                                    {f.nota}
                                  </span>
                                )}
                              </>
                            );
                            if (!f.saber) return etiqueta;
                            return (
                              <SaberMas
                                ecuacion={f.saber.ecuacion}
                                simbolos={f.saber.simbolos}
                                fuente={f.saber.fuente}
                                porque={f.porque}
                              >
                                {etiqueta}
                              </SaberMas>
                            );
                          })()}
                        </td>
                        {reference && (
                          <td className="celda-vacia">
                            {f.ref == null ? "—" : f.fmt(f.ref)}
                          </td>
                        )}
                        <td>{f.fmt(f.actual)}</td>
                        {reference && (
                          <td
                            style={{
                              color:
                                !mostrarDelta || neutro || Math.abs(d!) < 1e-9
                                  ? "var(--muted)"
                                  : bueno
                                    ? "var(--mejora)"
                                    : "var(--empeora)",
                            }}
                          >
                            {!mostrarDelta
                              ? t("agg.no_comparable")
                              : `${d! > 0 ? "+" : ""}${(f.fmtDelta ?? f.fmt)(d!)}`.replace(
                                  "+−",
                                  "−",
                                )}
                          </td>
                        )}
                      </tr>
                    </Fragment>
                  );
                })}
              </Fragment>
            );
          })}
        </tbody>
      </table>

      <p className="mt-2 text-etiqueta leading-snug text-[var(--muted)]">
        {t("agg.reparto_corto")}
      </p>
      <PorQue>{t("agg.reparto_porque")}</PorQue>
      <p className="mt-1 text-etiqueta leading-snug text-[var(--muted)]">
        {t("agg.unidades_corto")}
      </p>
      <PorQue>{t("agg.unidades_porque")}</PorQue>
      <p className="mt-1 text-etiqueta leading-snug text-[var(--muted)]">
        {t("agg.vot_hint", {
          alto: fmtMoney(agg.vot_por_estrato_clp_hora["1"]),
          medio: fmtMoney(agg.vot_por_estrato_clp_hora["2"]),
          bajo: fmtMoney(agg.vot_por_estrato_clp_hora["3"]),
        })}
      </p>
      {razon && (
        <p className="mt-1 text-etiqueta leading-snug text-[var(--alerta)]">
          {t("agg.incomparable", { razon: t(`agg.razon.${razon}`) })}
        </p>
      )}
      {!preciosIguales && (
        <p className="mt-1 text-etiqueta leading-snug text-[var(--alerta)]">
          {t("agg.precios_distintos")}
        </p>
      )}
    </div>
  );
}

/**
 * Los dos nombres que identifican una corrida: la ciudad y la política.
 *
 * La config no guarda de qué preset viene —aplicar uno copia valores y se
 * olvida del nombre—, así que el escenario se RECONOCE por sus parámetros. Sin
 * esto las columnas dicen «Referencia» y «Escenario actual» y la tabla no se
 * puede leer fuera del momento en que se generó: en una guía de clase, o dos
 * días después, nadie sabe qué se comparó contra qué.
 */
function Escenario({
  config,
  landUse,
}: {
  config: SimulationConfig;
  landUse: LandUseConfig | null;
}) {
  const { t } = useTranslation("simulator");
  const custom = t("agg.escenario_custom");
  return (
    <span className="th-escenario" title={t("agg.escenario_hint")}>
      <span>
        {/* Sin uso de suelo no se puede nombrar la ciudad: es el caso de una
            referencia fijada antes de que la corrida lo guardara. Dice «—» en
            vez de adivinar. */}
        {landUse ? (ciudadActiva(config, landUse) ?? custom) : "—"}{" "}
        <span className="th-tipo">({t("agg.tipo_ciudad")})</span>
      </span>
      <span>
        {politicaActiva(config, landUse ?? undefined) ?? custom}{" "}
        <span className="th-tipo">({t("agg.tipo_politica")})</span>
      </span>
    </span>
  );
}

/** Share en PORCENTAJE (no fracción): las filas de reparto y sus Δ viven en
 *  puntos porcentuales. */
function share(viajes: number | undefined, total: number): number {
  return total > 0 ? ((viajes ?? 0) / total) * 100 : 0;
}

function estratoKey(h: StratumId): string {
  return h === 1 ? "alto" : h === 2 ? "medio" : "bajo";
}

export type { Agregados };
