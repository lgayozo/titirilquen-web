/**
 * Agregados de CIUDAD COMPLETA para la tabla de resultados.
 *
 * Hasta ahora la tabla mostraba promedios y máximos POR MODO, con los que no se
 * puede decir si una política mejora al sistema: un modo puede mejorar mientras
 * el conjunto empeora. Estas funciones cierran esa brecha.
 *
 * Tres medidas, deliberadamente separadas porque responden preguntas distintas:
 *
 * 1. `tiempoTotalMin` — persona-minutos de todos los viajeros. El agregado
 *    físico, sin supuestos de valoración.
 *
 * 2. `costoGeneralizado` — tiempo valorado + dinero. Se ofrece en DOS versiones
 *    y la distinción no es cosmética:
 *      · *percibido*: usa el valor del tiempo CONDUCTUAL de cada estrato
 *        (β_tiempo/β_costo). Es el único consistente con el modelo, porque es
 *        literalmente el trade-off que el logit usa para elegir modo.
 *      · *social*: usa un valor del tiempo ÚNICO. El conductual implica que un
 *        minuto del estrato alto vale ~27× el del bajo; eso es un juicio
 *        distributivo, no un dato técnico, y en evaluación social se reemplaza
 *        por un valor de norma para no sesgar hacia proyectos que sirven a los
 *        de mayor ingreso.
 *
 * 3. `logsumPorEstrato` — el valor esperado del máximo de utilidad,
 *    `ln Σ_m e^{V_m}`. Reemplaza a la «utilidad media», que no significa nada:
 *    promediar utilidades entre personas no es una medida de bienestar. Dividido
 *    por λ (= −β_costo) queda en $ y es el excedente del consumidor.
 *
 *    OJO: el nivel del logsum tiene CERO ARBITRARIO (incluye las ASC), así que
 *    solo la DIFERENCIA contra otro escenario es interpretable — por eso la
 *    tabla lo muestra únicamente como delta contra la referencia. Y la
 *    comparación es inválida si los escenarios no comparten el conjunto de
 *    modos: ver `logsumComparable`.
 */

import { calcularUtilidades, type TiemposObservados } from "@/lib/utility";
import type {
  DemandConfig,
  IterationSnapshot,
  Modo,
  SimulationConfig,
  SimulationResult,
  StratumId,
} from "@/lib/types";

const STRATA: StratumId[] = [1, 2, 3];
const MODOS: Modo[] = ["Auto", "Metro", "Bici", "Caminata"];

export interface Agregados {
  /** Persona-minutos de todos los viajeros de la ciudad. */
  tiempoTotalMin: number;
  /** Viajeros físicos (excluye teletrabajo). */
  viajeros: number;
  /** Minutos por viajero. */
  tiempoMedioMin: number;
  /** $ totales, tiempo valorado al VoT conductual de cada estrato + dinero. */
  costoGeneralizadoPercibidoClp: number;
  /** $ totales con un VoT único (evaluación social). */
  costoGeneralizadoSocialClp: number;
  /** Valor del tiempo conductual por estrato ($/hora), = β_t/β_c. */
  votPorEstratoClpHora: Record<StratumId, number>;
  /** Logsum medio por estrato (utiles) y su equivalente en $ (÷ λ_h). */
  logsumPorEstrato: Record<StratumId, number>;
  excedentePorEstratoClp: Record<StratumId, number>;
}

/** Tiempo de cada modo en la celda `i`, en minutos. La caminata no va acá: es
 *  puramente geométrica y `calcularUtilidades` la deriva de `distKm`. */
function tiemposDeCelda(snap: IterationSnapshot, i: number): TiemposObservados {
  return {
    auto_total: snap.t_auto[i] ?? 0,
    bici_total: snap.t_bici[i] ?? 0,
    tren_acceso: snap.t_tren_acceso[i] ?? 0,
    tren_espera: snap.t_tren_espera[i] ?? 0,
    tren_viaje: snap.t_tren_viaje[i] ?? 0,
  };
}

/** `ln Σ_m e^{V_m}` sobre los modos FACTIBLES y HABILITADOS.
 *
 * El filtro por `modos_habilitados` se hace acá porque el espejo TS de
 * `calcular_utilidades` no lo aplica (el core sí): sin él, deshabilitar un modo
 * no cambiaría el logsum y el excedente quedaría inflado. */
function logsumDeCelda(
  h: StratumId,
  distKm: number,
  tieneAuto: boolean,
  cfg: SimulationConfig,
  tiempos: TiemposObservados,
): number | null {
  const utils = calcularUtilidades({
    estrato: h,
    distKm,
    tieneAuto,
    config: cfg.demand,
    tiempos,
  });
  const habilitados = new Set<Modo>(cfg.modos_habilitados);
  const vs = MODOS.filter((m) => habilitados.has(m))
    .map((m) => utils[m])
    .filter((u) => u?.feasible)
    .map((u) => u!.valor)
    .filter((v) => Number.isFinite(v));
  if (vs.length === 0) return null;
  const mx = Math.max(...vs);
  return mx + Math.log(vs.reduce((s, v) => s + Math.exp(v - mx), 0));
}

/** Valor del tiempo conductual: β_tiempo_viaje / β_costo, en $/hora. */
export function votClpHora(demand: DemandConfig, h: StratumId): number {
  const b = demand.estratos[h].betas;
  if (b.b_costo === 0) return 0;
  return (b.b_tiempo_viaje / b.b_costo) * 60;
}

/** Costo monetario del modo para un viaje desde la celda `i`. */
function dineroDelModo(
  modo: Modo,
  cfg: SimulationConfig,
  distKm: number,
): number {
  const g = cfg.demand.globales;
  if (modo === "Auto") return distKm * g.costo_combustible_km + g.costo_parking;
  if (modo === "Metro") return g.costo_tarifa_metro;
  return 0; // bici y caminata no tienen costo monetario en el modelo
}

/**
 * ¿Es válido comparar logsums entre dos configuraciones? Solo si comparten el
 * conjunto de modos: con distinto choice set el logsum cambia de escala y la
 * diferencia deja de ser un excedente.
 */
export function logsumComparable(
  a: SimulationConfig,
  b: SimulationConfig,
): boolean {
  const sa = [...a.modos_habilitados].sort().join(",");
  const sb = [...b.modos_habilitados].sort().join(",");
  return sa === sb;
}

export function calcularAgregados(
  result: SimulationResult,
  cfg: SimulationConfig,
  votSocialClpHora: number,
): Agregados | null {
  const snap = result.iteraciones.at(-1);
  if (!snap) return null;

  const n = cfg.city.n_celdas;
  const cbd = Math.floor(n / 2);
  const dx = cfg.city.largo_ciudad_km / n;
  const vCam = cfg.demand.globales.v_caminata || 4.8;

  const vot: Record<StratumId, number> = { 1: 0, 2: 0, 3: 0 };
  for (const h of STRATA) vot[h] = votClpHora(cfg.demand, h);

  let tiempoTotal = 0;
  let viajeros = 0;
  let cgPercibido = 0;
  let cgSocial = 0;
  const lsSum: Record<StratumId, number> = { 1: 0, 2: 0, 3: 0 };
  const lsN: Record<StratumId, number> = { 1: 0, 2: 0, 3: 0 };

  // `demanda_estrato[h][modo][celda]` es la demanda esperada desagregada. Sin
  // ella no se puede aplicar un VoT por estrato: el snapshot agregado solo trae
  // demanda por modo.
  const porEstrato = result.demanda_estrato;

  for (let i = 0; i < n; i++) {
    const distKm = Math.abs(cbd - i) * dx;
    const tCam = (distKm / vCam) * 60;
    const tiempos = tiemposDeCelda(snap, i);
    const tPorModo: Record<Modo, number> = {
      Auto: tiempos.auto_total,
      Metro: tiempos.tren_acceso + tiempos.tren_espera + tiempos.tren_viaje,
      Bici: tiempos.bici_total,
      Caminata: tCam,
      Teletrabajo: 0,
    };

    for (const h of STRATA) {
      const hIdx = h - 1;
      for (let m = 0; m < MODOS.length; m++) {
        const modo = MODOS[m]!;
        const d = porEstrato?.[hIdx]?.[m]?.[i] ?? 0;
        if (d <= 0) continue;
        const minutos = tPorModo[modo];
        const dinero = dineroDelModo(modo, cfg, distKm);
        tiempoTotal += d * minutos;
        viajeros += d;
        cgPercibido += d * ((minutos / 60) * vot[h] + dinero);
        cgSocial += d * ((minutos / 60) * votSocialClpHora + dinero);
      }

      // Logsum de la celda para este estrato. Se pondera por la demanda del
      // estrato en la celda: es el valor esperado sobre la población, no sobre
      // las celdas (que daría el mismo peso a la periferia vacía).
      const nEstrato = MODOS.reduce(
        (s, _m, mi) => s + (porEstrato?.[hIdx]?.[mi]?.[i] ?? 0),
        0,
      );
      if (nEstrato > 0) {
        // El choice set depende de tener auto, así que el logsum del estrato es
        // la mezcla de ambos casos ponderada por `prob_auto`. Usar `true` para
        // todos sobreestimaría el excedente de quienes no tienen auto.
        const pAuto = cfg.demand.estratos[h].prob_auto;
        const conAuto = logsumDeCelda(h, distKm, true, cfg, tiempos);
        const sinAuto = logsumDeCelda(h, distKm, false, cfg, tiempos);
        const partes: [number, number][] = [];
        if (conAuto != null) partes.push([conAuto, pAuto]);
        if (sinAuto != null) partes.push([sinAuto, 1 - pAuto]);
        const peso = partes.reduce((s, [, w]) => s + w, 0);
        if (peso > 0) {
          const ls = partes.reduce((s, [v, w]) => s + v * w, 0) / peso;
          lsSum[h] += ls * nEstrato;
          lsN[h] += nEstrato;
        }
      }
    }
  }

  const logsum: Record<StratumId, number> = { 1: 0, 2: 0, 3: 0 };
  const excedente: Record<StratumId, number> = { 1: 0, 2: 0, 3: 0 };
  for (const h of STRATA) {
    logsum[h] = lsN[h] > 0 ? lsSum[h] / lsN[h] : 0;
    // λ_h = −β_costo (utilidad marginal del ingreso): pasa utiles a $.
    const lambda = -cfg.demand.estratos[h].betas.b_costo;
    excedente[h] = lambda > 0 ? logsum[h] / lambda : 0;
  }

  return {
    tiempoTotalMin: tiempoTotal,
    viajeros,
    tiempoMedioMin: viajeros > 0 ? tiempoTotal / viajeros : 0,
    costoGeneralizadoPercibidoClp: cgPercibido,
    costoGeneralizadoSocialClp: cgSocial,
    votPorEstratoClpHora: vot,
    logsumPorEstrato: logsum,
    excedentePorEstratoClp: excedente,
  };
}

/** VoT social por defecto: promedio de los conductuales ponderado por los
 *  shares de estrato. Arranca neutro (no cambia el ranking respecto del
 *  percibido si los shares son los del escenario) y es lo que el usuario debe
 *  reemplazar por el valor de norma que corresponda. */
export function votSocialPorDefecto(cfg: SimulationConfig): number {
  const shares = cfg.city.share_estratos;
  return STRATA.reduce(
    (s, h) => s + votClpHora(cfg.demand, h) * (shares[h - 1] ?? 0),
    0,
  );
}
