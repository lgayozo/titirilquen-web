/**
 * Implementación TS de `titirilquen_core.demand.utility.calcular_utilidades`.
 * Mirror exacto del código Python para que el frontend pueda mostrar la
 * descomposición en tiempo real sin re-correr la simulación.
 */

import type { DemandConfig, Modo, StratumId } from "@/lib/types";

export interface TiemposObservados {
  auto_total: number;
  bici_total: number;
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

function flujoLibreTiempos(distKm: number, g: DemandConfig["globales"]): TiemposObservados {
  return {
    auto_total: (distKm / g.v_auto) * 60,
    bici_total: (distKm / g.v_bici) * 60,
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
}: {
  estrato: StratumId;
  distKm: number;
  tieneAuto: boolean;
  config: DemandConfig;
  tiempos?: TiemposObservados | null;
}): Record<Modo, UtilityBreakdown> {
  const stratum = config.estratos[estrato];
  if (!stratum) throw new Error(`Stratum ${estrato} not configured`);
  const betas = stratum.betas;
  const penal = betas.penalizaciones_fisicas;
  const gl = config.globales;

  const tt = tiempos ?? flujoLibreTiempos(distKm, gl);
  const tCam = (distKm / gl.v_caminata) * 60;

  // Auto
  const cAuto = distKm * gl.costo_combustible_km + gl.costo_parking;
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
    betas.b_tiempo_caminata * tt.tren_acceso;
  const vCMetro = betas.b_costo * cMetro;
  const metro: UtilityBreakdown = {
    modo: "Metro",
    asc: betas.asc_metro,
    v_tiempo: vTMetro,
    v_costo: vCMetro,
    v_penalizaciones: 0,
    valor: betas.asc_metro + vTMetro + vCMetro,
    feasible: true,
  };

  // Bici
  let bici: UtilityBreakdown;
  if (tt.bici_total > 45) {
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
    let p = 0;
    if (tt.bici_total > 10) p += penal.bici_10;
    if (tt.bici_total > 20) p += penal.bici_20;
    if (tt.bici_total > 30) p += penal.bici_30;
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
  let cam: UtilityBreakdown;
  if (tCam > 30) {
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
    let p = 0;
    if (tCam > 5) p += penal.walk_5;
    if (tCam > 15) p += penal.walk_15;
    if (tCam > 25) p += penal.walk_25;
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

  return { Auto: auto, Metro: metro, Bici: bici, Caminata: cam, Teletrabajo: {
    modo: "Teletrabajo",
    asc: 0, v_tiempo: 0, v_costo: 0, v_penalizaciones: 0, valor: 0, feasible: false,
  } };
}

export function probabilidadesLogit(utils: Record<Modo, UtilityBreakdown>): Record<Modo, number> {
  const feasibles = Object.values(utils).filter((u) => u.feasible);
  if (feasibles.length === 0) {
    return {
      Auto: 0, Metro: 0, Bici: 0, Caminata: 0, Teletrabajo: 0,
    } as Record<Modo, number>;
  }
  const maxV = Math.max(...feasibles.map((u) => u.valor));
  const exps = feasibles.map((u) => Math.exp(u.valor - maxV));
  const sum = exps.reduce((a, b) => a + b, 0);
  const out: Record<Modo, number> = {
    Auto: 0, Metro: 0, Bici: 0, Caminata: 0, Teletrabajo: 0,
  };
  feasibles.forEach((u, i) => {
    out[u.modo] = (exps[i] ?? 0) / sum;
  });
  return out;
}
