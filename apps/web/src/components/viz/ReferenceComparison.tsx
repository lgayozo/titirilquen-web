import { useTranslation } from "react-i18next";

import { PorQue } from "@/components/ui/PorQue";
import { CaptionTabla } from "@/components/viz/CaptionTabla";
import {
  agregadosDe,
  bienestarComparable,
  type Agregados,
} from "@/lib/agregados";
import { VOT_SOCIAL_CLP_HORA } from "@/lib/gen/constantes.gen";
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
// Un share y su delta van en la MISMA unidad: puntos porcentuales. Escribir el
// delta como «%» invitaría a leerlo como variación relativa.
const fmtPuntos = (v: number) => `${fmtDecimal(v)} pp`;

interface FilaAgg {
  label: string;
  actual: number;
  ref: number | null;
  fmt: (v: number) => string;
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

  // Cuál de las dos medidas de excedente corresponde al método de asignación lo
  // decide el NÚCLEO (`medida_bienestar`): logsum bajo logit, utilidad máxima
  // media bajo determinístico, donde no hay término aleatorio que promediar.
  // Acá sólo se elige el campo y el rótulo; la regla no se reimplementa.
  const usaMax = agg.medida_bienestar === "utilidad_maxima";
  const excedentePorEstrato = usaMax
    ? agg.excedente_max_por_estrato_clp
    : agg.excedente_por_estrato_clp;
  const excedenteRefPorEstrato = usaMax
    ? aggRef?.excedente_max_por_estrato_clp
    : aggRef?.excedente_por_estrato_clp;
  // El Δ del excedente sólo es un cambio de bienestar si las dos corridas
  // comparten el cero del nivel (modos, β, teletrabajo, población y medida:
  // `bienestarComparable`). Si no, se muestra el nivel, no el Δ.
  const razon =
    reference && aggRef
      ? bienestarComparable(
          { config, landUse, medida: agg.medida_bienestar },
          {
            config: reference.config,
            landUse: reference.landUse,
            medida: aggRef.medida_bienestar,
          },
        )
      : null;
  const excedenteComparable = razon == null;

  const filas: FilaAgg[] = [
    {
      // El denominador va PRIMERO y explícito: los shares de abajo se calculan
      // sobre esta cifra, y entre dos escenarios puede cambiar (el teletrabajo
      // no viaja). Sin la fila, un share que sube sin que nadie cambie de modo
      // —porque el denominador bajó— se lee como sustitución modal.
      label: t("agg.viajes_fisicos"),
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
      actual: agg.varados,
      ref: aggRef?.varados ?? null,
      fmt: fmtMiles,
      menorEsMejor: true,
      nota: t("agg.varados_nota"),
    },
    ...MODOS.map((m) => ({
      label: t("agg.reparto_modo", { modo: t(`modes.${m.toLowerCase()}`) }),
      actual: share(agg.viajes_por_modo[m], agg.viajeros),
      ref: aggRef ? share(aggRef.viajes_por_modo[m], aggRef.viajeros) : null,
      fmt: fmtPuntos,
      menorEsMejor: false,
      neutra: true,
    })),
    {
      label: t("agg.tiempo_total"),
      actual: agg.tiempo_total_min,
      ref: aggRef?.tiempo_total_min ?? null,
      fmt: fmtMiles,
      menorEsMejor: true,
    },
    {
      label: t("agg.tiempo_medio"),
      actual: agg.tiempo_medio_min,
      ref: aggRef?.tiempo_medio_min ?? null,
      fmt: fmtMin,
      menorEsMejor: true,
    },
    {
      label: t("agg.cg_percibido"),
      actual: agg.costo_generalizado_percibido_clp,
      ref: aggRef?.costo_generalizado_percibido_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.cg_percibido_nota"),
    },
    {
      label: t("agg.cg_social"),
      actual: agg.costo_generalizado_social_clp,
      ref: aggRef?.costo_generalizado_social_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.cg_social_nota", { vot: fmtMoney(VOT_SOCIAL_CLP_HORA) }),
    },
    {
      label: t("agg.recaudacion"),
      actual:
        agg.recaudacion_parking_clp +
        agg.recaudacion_peaje_clp +
        agg.recaudacion_tarifa_clp,
      ref:
        aggRef == null
          ? null
          : aggRef.recaudacion_parking_clp +
            aggRef.recaudacion_peaje_clp +
            aggRef.recaudacion_tarifa_clp,
      fmt: fmtMoney,
      menorEsMejor: false,
      nota: t("agg.recaudacion_nota"),
    },
    {
      label: t("agg.costo_operador"),
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
      actual: agg.subsidio_metro_clp,
      ref: aggRef?.subsidio_metro_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: true,
      nota: t("agg.subsidio_nota", {
        f: config.supply.train.factor_dia_punta,
      }),
    },
    {
      // El total que suma el bienestar social, a la vista: sin él, el Δ del
      // bienestar no se podía descomponer en lo que pierde el viajero y lo
      // que vuelve como recaudación.
      label: t(usaMax ? "agg.excedente_total_max" : "agg.excedente_total"),
      actual: usaMax ? agg.excedente_max_total_clp : agg.excedente_total_clp,
      ref:
        aggRef == null
          ? null
          : usaMax
            ? aggRef.excedente_max_total_clp
            : aggRef.excedente_total_clp,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: excedenteComparable,
      unidad: t("agg.u_ciudad"),
      nivel: true,
    },
    {
      label: t("agg.bienestar"),
      actual: agg.bienestar_social_clp,
      ref: aggRef?.bienestar_social_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      // Lleva dentro el excedente de la medida emparejada, así que hereda su
      // condición de comparabilidad.
      comparable: excedenteComparable,
      nivel: true,
      nota: t("agg.bienestar_nota"),
    },
    {
      // Tercera medida: el MISMO excedente emparejado, dividido por un λ común
      // a los estratos (|β_tiempo|·60/VST) en vez del λ_h de cada uno. NO
      // revalúa el tiempo: repondera personas, dinero incluido, por VST/VoT_h
      // (D13, libro cap. 7). La lectura SNI —el tiempo al VST— es `cg_social`.
      // No es redundante: el λ conductual pondera a favor de quien más gana,
      // así que el signo del Δ agregado podría darse vuelta entre las dos.
      label: t("agg.excedente_social"),
      actual: agg.excedente_social_total_clp,
      ref: aggRef?.excedente_social_total_clp ?? null,
      fmt: fmtMoney,
      menorEsMejor: false,
      comparable: excedenteComparable,
      unidad: t("agg.u_ciudad"),
      nivel: true,
      nota: t("agg.excedente_social_corto", {
        vot: fmtMoney(VOT_SOCIAL_CLP_HORA),
      }),
      porque: t("agg.excedente_social_porque"),
    },
    ...STRATA.map((h) => ({
      label: t(usaMax ? "agg.excedente_estrato_max" : "agg.excedente_estrato", {
        h: t(`strata.${estratoKey(h)}`),
      }),
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
          {filas.map((f) => {
            const d = f.ref == null ? null : f.actual - f.ref;
            const mostrarDelta = d != null && f.comparable !== false;
            const neutro = f.neutra === true;
            const bueno = d == null ? false : f.menorEsMejor ? d < 0 : d > 0;
            return (
              <tr key={f.label}>
                <td>
                  {f.label}
                  {f.unidad && (
                    <span className="celda-unidad ml-1">{f.unidad}</span>
                  )}
                  {f.nivel && !reference && (
                    <span className="celda-unidad ml-1">
                      {t("agg.u_nivel")}
                    </span>
                  )}
                  {f.nota && <span className="celda-nota ml-1">{f.nota}</span>}
                  {f.porque && <PorQue>{f.porque}</PorQue>}
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
                      : `${d! > 0 ? "+" : ""}${f.fmt(d!)}`.replace("+−", "−")}
                  </td>
                )}
              </tr>
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
      {usaMax && (
        <p className="mt-1 text-etiqueta leading-snug text-[var(--muted)]">
          {t("agg.medida_utilidad_maxima")}
        </p>
      )}
      {razon && (
        <p className="mt-1 text-etiqueta leading-snug text-[var(--alerta)]">
          {t("agg.incomparable", { razon: t(`agg.razon.${razon}`) })}
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
        {politicaActiva(config) ?? custom}{" "}
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
