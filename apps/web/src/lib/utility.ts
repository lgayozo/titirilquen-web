/**
 * Implementación TS de `titirilquen_core.demand.utility.calcular_utilidades`.
 * Mirror exacto del código Python para que el frontend pueda mostrar la
 * descomposición en tiempo real sin re-correr la simulación.
 */

import type {
  DemandConfig,
  Modo,
  ModoTransporte,
  StratumId,
} from "@/lib/types";
import {
  A_DOMINANCIA_METRO,
  OMEGA_CORTE_SUAVE,
  OMEGA_DOMINANCIA_METRO,
  VIAJES_POR_TOUR,
} from "@/lib/gen/constantes.gen";

export interface TiemposObservados {
  auto_total: number;
  bici_total: number;
  /** Red vacía: sobre este tiempo van los escalones y el corte de la bici (D9). */
  bici_libre: number;
  tren_acceso: number;
  tren_espera: number;
  tren_viaje: number;
}

export interface UtilityBreakdown {
  modo: Modo;
  valor: number;
  asc: number;
  v_tiempo: number;
  v_costo: number;
  v_penalizaciones: number;
  feasible: boolean;
}

const UTIL_IMPOSIBLE = -9999;

type Tres = readonly [number, number, number];

/** Espejo de `_escalones` (D-02): suma `p_k` por cada umbral cruzado. */
function escalones(t: number, umbrales: Tres, penal: Tres): number {
  let p = 0;
  for (let k = 0; k < 3; k++) if (t > umbrales[k]!) p += penal[k]!;
  return p;
}

/** Espejo de `_rampa` (`umbrales="suaves"`): la penalización acumulada de los
 *  escalones interpolada por sus puntos medios, y más allá del último nodo la
 *  última pendiente. */
function rampa(t: number, umbrales: Tres, penal: Tres): number {
  const h0 = (umbrales[1] - umbrales[0]) / 2;
  const h2 = (umbrales[2] - umbrales[1]) / 2;
  const xs = [
    umbrales[0] - h0,
    umbrales[1] - h0,
    umbrales[2] - h2,
    umbrales[2] + h2,
  ];
  const ys = [0, penal[0], penal[0] + penal[1], penal[0] + penal[1] + penal[2]];
  // `np.interp` deja el valor del extremo a la izquierda del primer nodo.
  if (t <= xs[0]!) return ys[0]!;
  for (let k = 1; k < 4; k++) {
    if (t <= xs[k]!) {
      const w = (t - xs[k - 1]!) / (xs[k]! - xs[k - 1]!);
      return ys[k - 1]! + w * (ys[k]! - ys[k - 1]!);
    }
  }
  return ys[3]! + ((t - xs[3]!) * (ys[3]! - ys[2]!)) / (xs[3]! - xs[2]!);
}

/** Espejo de `_ln_phi`: corte CMNL, `−ln(1 + e^{ωx})`, sin desbordar para
 *  x grande (lo mismo que `np.logaddexp(0, ωx)`). */
function lnPhi(x: number, omega: number): number {
  const z = omega * x;
  return -(Math.max(z, 0) + Math.log1p(Math.exp(-Math.abs(z))));
}

function flujoLibreTiempos(
  distKm: number,
  g: DemandConfig["globales"],
): TiemposObservados {
  return {
    auto_total: (distKm / g.v_auto) * 60,
    bici_total: (distKm / g.v_bici) * 60,
    bici_libre: (distKm / g.v_bici) * 60,
    tren_acceso: 10,
    tren_espera: 5,
    tren_viaje: (distKm / g.v_metro) * 60,
  };
}

export function calcularUtilidades({
  estrato,
  distKm,
  tieneAuto,
  config,
  tiempos,
  modosHabilitados,
}: {
  estrato: StratumId;
  distKm: number;
  tieneAuto: boolean;
  config: DemandConfig;
  tiempos?: TiemposObservados | null;
  /** Set de elección. `undefined` ⇒ todos habilitados (igual que `None` en el core). */
  modosHabilitados?: readonly ModoTransporte[];
}): Record<Modo, UtilityBreakdown> {
  const stratum = config.estratos[estrato];
  if (!stratum) throw new Error(`Stratum ${estrato} not configured`);
  const betas = stratum.betas;
  const penal = betas.penalizaciones_fisicas;
  const gl = config.globales;

  const suaves = gl.umbrales === "suaves";
  const tt = tiempos ?? flujoLibreTiempos(distKm, gl);
  const tCam = (distKm / gl.v_caminata) * 60;

  // Auto
  // Espejo de `costo_monetario_auto`: bencina y peaje por km (D7), más medio
  // parking, que es por tour (día).
  const cAuto =
    distKm * (gl.costo_combustible_km + gl.peaje_km) +
    gl.costo_parking / VIAJES_POR_TOUR;
  const vTAuto = betas.b_tiempo_viaje * tt.auto_total;
  const vCAuto = betas.b_costo * cAuto;
  const auto: UtilityBreakdown = tieneAuto
    ? {
        modo: "Auto",
        asc: betas.asc_auto,
        v_tiempo: vTAuto,
        v_costo: vCAuto,
        v_penalizaciones: 0,
        valor: betas.asc_auto + vTAuto + vCAuto,
        feasible: true,
      }
    : {
        modo: "Auto",
        asc: 0,
        v_tiempo: 0,
        v_costo: 0,
        v_penalizaciones: 0,
        valor: UTIL_IMPOSIBLE,
        feasible: false,
      };

  // Metro
  const cMetro = gl.costo_tarifa_metro;
  const vTMetro =
    betas.b_tiempo_viaje * tt.tren_viaje +
    betas.b_tiempo_espera * tt.tren_espera +
    betas.b_tiempo_acceso * tt.tren_acceso;
  const vCMetro = betas.b_costo * cMetro;
  // Espejo de `calcular_utilidades`: sin tramo en tren no hay viaje en metro.
  // `tren_viaje == 0` ⇒ la estación más cercana es la del CBD (el destino), así
  // que "tomar el metro" sería caminar hasta el destino sin subirse a nada —
  // caso que además esquivaba el corte de 30 min de la caminata. Con «suaves»
  // la oferta ya no asigna esa estación fuera del CBD y el filtro es la
  // dominancia suave frente a caminar directo, en minutos de vehículo.
  let pMetro = 0;
  if (suaves) {
    const bv = betas.b_tiempo_viaje;
    const gtMetro =
      (betas.b_tiempo_acceso / bv) * tt.tren_acceso +
      (betas.b_tiempo_espera / bv) * tt.tren_espera +
      tt.tren_viaje;
    const gtCam = (betas.b_tiempo_caminata / bv) * tCam;
    pMetro = lnPhi(
      gtMetro - A_DOMINANCIA_METRO * gtCam,
      OMEGA_DOMINANCIA_METRO,
    );
  }
  const metro: UtilityBreakdown =
    tt.tren_viaje <= 0
      ? {
          modo: "Metro",
          asc: 0,
          v_tiempo: 0,
          v_costo: 0,
          v_penalizaciones: 0,
          valor: UTIL_IMPOSIBLE,
          feasible: false,
        }
      : {
          modo: "Metro",
          asc: betas.asc_metro,
          v_tiempo: vTMetro,
          v_costo: vCMetro,
          v_penalizaciones: pMetro,
          valor: betas.asc_metro + vTMetro + vCMetro + pMetro,
          feasible: true,
        };

  // Penalización física y corte (D-02). «escalones»: saltos y, sobre el corte,
  // el modo sale del conjunto. «suaves»: rampas y el corte como penalización
  // CMNL, siempre factible. `null` ⇒ infactible.
  const fisica = (
    t: number,
    umbrales: Tres,
    pen: Tres,
    corte: number,
  ): number | null => {
    if (suaves)
      return rampa(t, umbrales, pen) + lnPhi(t - corte, OMEGA_CORTE_SUAVE);
    if (t > corte) return null;
    return escalones(t, umbrales, pen);
  };

  // Bici — penalización y corte sobre el tiempo de red vacía; la congestión
  // entra sólo por b_tiempo (D9). El corte es el configurable, como en el core.
  const pBici = fisica(
    tt.bici_libre,
    [10, 20, 30],
    [penal.bici_10, penal.bici_20, penal.bici_30],
    gl.corte_bici_min,
  );
  let bici: UtilityBreakdown;
  if (pBici === null) {
    bici = {
      modo: "Bici",
      asc: 0,
      v_tiempo: 0,
      v_costo: 0,
      v_penalizaciones: 0,
      valor: UTIL_IMPOSIBLE,
      feasible: false,
    };
  } else {
    const p = pBici;
    const vT = betas.b_tiempo_viaje * tt.bici_total;
    bici = {
      modo: "Bici",
      asc: betas.asc_bici,
      v_tiempo: vT,
      v_costo: 0,
      v_penalizaciones: p,
      valor: betas.asc_bici + vT + p,
      feasible: true,
    };
  }

  // Caminata
  const pCam = fisica(
    tCam,
    [5, 15, 25],
    [penal.walk_5, penal.walk_15, penal.walk_25],
    gl.corte_caminata_min,
  );
  let cam: UtilityBreakdown;
  if (pCam === null) {
    cam = {
      modo: "Caminata",
      asc: 0,
      v_tiempo: 0,
      v_costo: 0,
      v_penalizaciones: 0,
      valor: UTIL_IMPOSIBLE,
      feasible: false,
    };
  } else {
    const p = pCam;
    const vT = betas.b_tiempo_caminata * tCam;
    cam = {
      modo: "Caminata",
      asc: betas.asc_caminata,
      v_tiempo: vT,
      v_costo: 0,
      v_penalizaciones: p,
      valor: betas.asc_caminata + vT + p,
      feasible: true,
    };
  }

  const resultado: Record<Modo, UtilityBreakdown> = {
    Auto: auto,
    Metro: metro,
    Bici: bici,
    Caminata: cam,
    Teletrabajo: {
      modo: "Teletrabajo",
      asc: 0,
      v_tiempo: 0,
      v_costo: 0,
      v_penalizaciones: 0,
      valor: 0,
      feasible: false,
    },
  };

  // Espejo de `modos_habilitados` en el core: un modo fuera del set de elección
  // se trata como infeasible (utilidad −∞), no como un modo con V baja. Sin
  // esto, deshabilitar un modo no cambiaba nada aguas abajo.
  if (modosHabilitados) {
    const habilitados = new Set<string>(modosHabilitados);
    for (const modo of Object.keys(resultado) as Modo[]) {
      if (!habilitados.has(modo) && resultado[modo].feasible) {
        resultado[modo] = {
          modo,
          asc: 0,
          v_tiempo: 0,
          v_costo: 0,
          v_penalizaciones: 0,
          valor: UTIL_IMPOSIBLE,
          feasible: false,
        };
      }
    }
  }

  return resultado;
}

export function probabilidadesLogit(
  utils: Record<Modo, UtilityBreakdown>,
): Record<Modo, number> {
  const feasibles = Object.values(utils).filter((u) => u.feasible);
  if (feasibles.length === 0) {
    return {
      Auto: 0,
      Metro: 0,
      Bici: 0,
      Caminata: 0,
      Teletrabajo: 0,
    } as Record<Modo, number>;
  }
  const maxV = Math.max(...feasibles.map((u) => u.valor));
  const exps = feasibles.map((u) => Math.exp(u.valor - maxV));
  const sum = exps.reduce((a, b) => a + b, 0);
  const out: Record<Modo, number> = {
    Auto: 0,
    Metro: 0,
    Bici: 0,
    Caminata: 0,
    Teletrabajo: 0,
  };
  feasibles.forEach((u, i) => {
    out[u.modo] = (exps[i] ?? 0) / sum;
  });
  return out;
}
