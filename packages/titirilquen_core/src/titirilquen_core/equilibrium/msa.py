"""Método de Promedios Sucesivos (MSA) para el equilibrio oferta-demanda.

Portado y extendido desde `titirilquen-repo/app.py:470-524`. Cambios:

- Criterio de convergencia real: residuo `‖T_n − T_{n−1}‖_∞ < tol`. Si
  `tol=0` (default), se respeta `max_iter` como antes (ver D-10).
- Retorna `ConvergenceTrace` con snapshot por iteración para visualización
  en vivo (antes este dato se perdía tras el loop).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.demand.choice import elegir_modo
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.population import Agente, generar_poblacion
from titirilquen_core.supply.bike import demora_bici_tramo
from titirilquen_core.supply.car import demora_auto_tramo
from titirilquen_core.supply.train import oferta_tren

ModalSplit = dict[str, int]


@dataclass
class IterationSnapshot:
    """Estado de la red al final de una iteración del MSA."""

    iter: int
    f_msa: float
    modal_split: ModalSplit
    demanda_auto: NDArray[np.float64]
    demanda_metro: NDArray[np.float64]
    demanda_bici: NDArray[np.float64]
    t_auto: NDArray[np.float64]
    t_bici: NDArray[np.float64]
    t_tren_acceso: NDArray[np.float64]
    t_tren_espera: NDArray[np.float64]
    t_tren_viaje: NDArray[np.float64]
    frecuencia_metro: float
    residuo: float


@dataclass
class ConvergenceTrace:
    """Resultado completo del loop MSA."""

    iteraciones: list[IterationSnapshot] = field(default_factory=list)
    converged: bool = False
    capacidad_auto: float = 0.0
    v_libre_auto: float = 0.0
    alpha_auto_bpr: float = 0.0
    beta_auto_bpr: float = 0.0
    carga_metro: NDArray[np.float64] | None = None
    estaciones_km: NDArray[np.float64] | None = None
    agentes: list[Agente] = field(default_factory=list)


def _tiempos_de_snapshot(snap: IterationSnapshot, n_celdas: int) -> list[TiemposObservados]:
    return [
        TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        for i in range(n_celdas)
    ]


def _correr_iteracion(
    agentes: list[Agente],
    ciudad: CiudadLineal,
    demand: DemandConfig,
    tiempos_por_celda: list[TiemposObservados] | None,
    rng: np.random.Generator,
) -> tuple[ModalSplit, NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    conteo: ModalSplit = {"Auto": 0, "Metro": 0, "Bici": 0, "Caminata": 0, "Teletrabajo": 0}
    dem_auto = np.zeros(ciudad.n_celdas)
    dem_metro = np.zeros(ciudad.n_celdas)
    dem_bici = np.zeros(ciudad.n_celdas)

    for a in agentes:
        if a.teletrabaja:
            a.modo_elegido = "Teletrabajo"
            a.utilidad_elegida = 0.0
            conteo["Teletrabajo"] += 1
            continue

        tiempos = tiempos_por_celda[a.celda_origen] if tiempos_por_celda is not None else None
        utils = calcular_utilidades(
            estrato=a.estrato,
            celda_origen=a.celda_origen,
            tiene_auto=a.tiene_auto,
            ciudad=ciudad,
            config=demand,
            tiempos_observados=tiempos,
        )
        modo = elegir_modo(utils, rng=rng)
        a.modo_elegido = modo
        a.utilidad_elegida = utils[modo].valor
        conteo[modo] += 1
        if modo == "Auto":
            dem_auto[a.celda_origen] += 1
        elif modo == "Metro":
            dem_metro[a.celda_origen] += 1
        elif modo == "Bici":
            dem_bici[a.celda_origen] += 1

    return conteo, dem_auto, dem_metro, dem_bici


def iter_msa(sim: SimulationConfig) -> Iterator[IterationSnapshot]:
    """Generador que emite una IterationSnapshot por iteración.

    Ideal para streaming (SSE/WebSocket) — el consumidor decide cuándo parar.
    """
    rng = np.random.default_rng(sim.seed)
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)

    agentes = generar_poblacion(
        ciudad=ciudad,
        densidad_por_celda=sim.city.densidad_por_celda,
        share_estratos=sim.city.share_estratos,
        demand_config=sim.demand,
        teletrabajo_factor=sim.city.teletrabajo_factor,
        rng=rng,
    )

    tiempos_actuales: list[TiemposObservados] | None = None
    t_auto_ac = np.zeros(ciudad.n_celdas)
    t_bici_ac = np.zeros(ciudad.n_celdas)
    t_tren_acc_ac = np.zeros(ciudad.n_celdas)
    t_tren_esp_ac = np.zeros(ciudad.n_celdas)
    t_tren_v_ac = np.zeros(ciudad.n_celdas)

    for it in range(sim.max_iter):
        conteo, d_auto, d_metro, d_bici = _correr_iteracion(
            agentes, ciudad, sim.demand, tiempos_actuales, rng
        )

        car_p = sim.supply.car
        bike_p = sim.supply.bike
        train_p = sim.supply.train

        car_result = demora_auto_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            demanda=d_auto,
            v_max_kmh=car_p.v_max_kmh,
            ancho_pista_m=car_p.ancho_pista_m,
            largo_vehiculo_m=car_p.largo_vehiculo_m,
            gap_m=car_p.gap_m,
            L_ciudad_km=ciudad.largo_total_km,
            num_pistas=car_p.num_pistas,
            alpha_bpr=car_p.alpha_bpr,
            beta_bpr=car_p.beta_bpr,
        )
        bike_result = demora_bici_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            capacidad=bike_p.capacidad_pista,
            demanda=d_bici,
            v_media=bike_p.v_media_kmh,
            L_ciudad_km=ciudad.largo_total_km,
            alpha=bike_p.alpha_bpr,
            beta=bike_p.beta_bpr,
            pendiente_porcentaje=sim.city.pendiente_porcentaje,
        )
        train_result = oferta_tren(
            demanda=d_metro,
            L_ciudad_km=ciudad.largo_total_km,
            x_centro_km=ciudad.cbd_km,
            v_tren_kmh=train_p.v_tren_kmh,
            capacidad_tren=train_p.capacidad_tren,
            num_estaciones=train_p.num_estaciones,
            v_caminata_kmh=train_p.v_caminata_kmh,
            tasa_carga=train_p.tasa_carga,
            frec_min=train_p.frec_min,
            frec_max=train_p.frec_max,
        )

        if tiempos_actuales is None:
            t_auto_ac = car_result.t_usuarios_min.copy()
            t_bici_ac = bike_result.t_usuarios_min.copy()
            t_tren_acc_ac = train_result.t_acceso_min.copy()
            t_tren_esp_ac = train_result.t_espera_min.copy()
            t_tren_v_ac = train_result.t_viaje_min.copy()
            residuo = float("inf")
        else:
            f = 1.0 / (it + 1)
            old_auto = t_auto_ac.copy()
            t_auto_ac = f * car_result.t_usuarios_min + (1 - f) * t_auto_ac
            t_bici_ac = f * bike_result.t_usuarios_min + (1 - f) * t_bici_ac
            t_tren_acc_ac = f * train_result.t_acceso_min + (1 - f) * t_tren_acc_ac
            t_tren_esp_ac = f * train_result.t_espera_min + (1 - f) * t_tren_esp_ac
            t_tren_v_ac = f * train_result.t_viaje_min + (1 - f) * t_tren_v_ac
            residuo = float(np.max(np.abs(t_auto_ac - old_auto)))

        tiempos_actuales = [
            TiemposObservados(
                auto_total=float(t_auto_ac[i]),
                bici_total=float(t_bici_ac[i]),
                tren_acceso=float(t_tren_acc_ac[i]),
                tren_espera=float(t_tren_esp_ac[i]),
                tren_viaje=float(t_tren_v_ac[i]),
            )
            for i in range(ciudad.n_celdas)
        ]

        yield IterationSnapshot(
            iter=it,
            f_msa=1.0 / (it + 1),
            modal_split=conteo,
            demanda_auto=d_auto,
            demanda_metro=d_metro,
            demanda_bici=d_bici,
            t_auto=t_auto_ac.copy(),
            t_bici=t_bici_ac.copy(),
            t_tren_acceso=t_tren_acc_ac.copy(),
            t_tren_espera=t_tren_esp_ac.copy(),
            t_tren_viaje=t_tren_v_ac.copy(),
            frecuencia_metro=train_result.frecuencia_operativa,
            residuo=residuo,
        )


def run_msa(sim: SimulationConfig) -> ConvergenceTrace:
    """Ejecuta el loop MSA completo hasta convergencia o `max_iter`."""
    rng = np.random.default_rng(sim.seed)
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)

    agentes = generar_poblacion(
        ciudad=ciudad,
        densidad_por_celda=sim.city.densidad_por_celda,
        share_estratos=sim.city.share_estratos,
        demand_config=sim.demand,
        teletrabajo_factor=sim.city.teletrabajo_factor,
        rng=rng,
    )

    trace = ConvergenceTrace(agentes=agentes)
    last_car = _run_final_assignments(sim, ciudad, agentes, trace)
    if last_car is None:
        return trace

    trace.capacidad_auto = last_car["capacidad"]
    trace.v_libre_auto = last_car["v_libre"]
    trace.alpha_auto_bpr = last_car["alpha"]
    trace.beta_auto_bpr = last_car["beta"]
    trace.carga_metro = last_car["carga_metro"]
    trace.estaciones_km = last_car["estaciones"]
    return trace


def _run_final_assignments(
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    agentes: list[Agente],
    trace: ConvergenceTrace,
) -> dict | None:
    rng = np.random.default_rng(sim.seed)
    # Re-semilla para compatibilidad con iter_msa: una sola corrida
    tiempos_actuales: list[TiemposObservados] | None = None
    t_auto_ac = np.zeros(ciudad.n_celdas)
    t_bici_ac = np.zeros(ciudad.n_celdas)
    t_tren_acc_ac = np.zeros(ciudad.n_celdas)
    t_tren_esp_ac = np.zeros(ciudad.n_celdas)
    t_tren_v_ac = np.zeros(ciudad.n_celdas)

    last_state = None
    car_p = sim.supply.car
    bike_p = sim.supply.bike
    train_p = sim.supply.train

    for it in range(sim.max_iter):
        conteo, d_auto, d_metro, d_bici = _correr_iteracion(
            agentes, ciudad, sim.demand, tiempos_actuales, rng
        )

        car_result = demora_auto_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            demanda=d_auto,
            v_max_kmh=car_p.v_max_kmh,
            ancho_pista_m=car_p.ancho_pista_m,
            largo_vehiculo_m=car_p.largo_vehiculo_m,
            gap_m=car_p.gap_m,
            L_ciudad_km=ciudad.largo_total_km,
            num_pistas=car_p.num_pistas,
            alpha_bpr=car_p.alpha_bpr,
            beta_bpr=car_p.beta_bpr,
        )
        bike_result = demora_bici_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            capacidad=bike_p.capacidad_pista,
            demanda=d_bici,
            v_media=bike_p.v_media_kmh,
            L_ciudad_km=ciudad.largo_total_km,
            alpha=bike_p.alpha_bpr,
            beta=bike_p.beta_bpr,
            pendiente_porcentaje=sim.city.pendiente_porcentaje,
        )
        train_result = oferta_tren(
            demanda=d_metro,
            L_ciudad_km=ciudad.largo_total_km,
            x_centro_km=ciudad.cbd_km,
            v_tren_kmh=train_p.v_tren_kmh,
            capacidad_tren=train_p.capacidad_tren,
            num_estaciones=train_p.num_estaciones,
            v_caminata_kmh=train_p.v_caminata_kmh,
            tasa_carga=train_p.tasa_carga,
            frec_min=train_p.frec_min,
            frec_max=train_p.frec_max,
        )

        if tiempos_actuales is None:
            t_auto_ac = car_result.t_usuarios_min.copy()
            t_bici_ac = bike_result.t_usuarios_min.copy()
            t_tren_acc_ac = train_result.t_acceso_min.copy()
            t_tren_esp_ac = train_result.t_espera_min.copy()
            t_tren_v_ac = train_result.t_viaje_min.copy()
            residuo = float("inf")
        else:
            f = 1.0 / (it + 1)
            old_auto = t_auto_ac.copy()
            t_auto_ac = f * car_result.t_usuarios_min + (1 - f) * t_auto_ac
            t_bici_ac = f * bike_result.t_usuarios_min + (1 - f) * t_bici_ac
            t_tren_acc_ac = f * train_result.t_acceso_min + (1 - f) * t_tren_acc_ac
            t_tren_esp_ac = f * train_result.t_espera_min + (1 - f) * t_tren_esp_ac
            t_tren_v_ac = f * train_result.t_viaje_min + (1 - f) * t_tren_v_ac
            residuo = float(np.max(np.abs(t_auto_ac - old_auto)))

        tiempos_actuales = [
            TiemposObservados(
                auto_total=float(t_auto_ac[i]),
                bici_total=float(t_bici_ac[i]),
                tren_acceso=float(t_tren_acc_ac[i]),
                tren_espera=float(t_tren_esp_ac[i]),
                tren_viaje=float(t_tren_v_ac[i]),
            )
            for i in range(ciudad.n_celdas)
        ]

        trace.iteraciones.append(
            IterationSnapshot(
                iter=it,
                f_msa=1.0 / (it + 1),
                modal_split=conteo,
                demanda_auto=d_auto.copy(),
                demanda_metro=d_metro.copy(),
                demanda_bici=d_bici.copy(),
                t_auto=t_auto_ac.copy(),
                t_bici=t_bici_ac.copy(),
                t_tren_acceso=t_tren_acc_ac.copy(),
                t_tren_espera=t_tren_esp_ac.copy(),
                t_tren_viaje=t_tren_v_ac.copy(),
                frecuencia_metro=train_result.frecuencia_operativa,
                residuo=residuo,
            )
        )

        last_state = {
            "capacidad": car_result.capacidad_direccion,
            "v_libre": car_result.v_libre_kmh,
            "alpha": car_result.alpha_bpr,
            "beta": car_result.beta_bpr,
            "carga_metro": train_result.carga_por_tramo,
            "estaciones": train_result.estaciones_km,
        }

        if sim.tolerance > 0 and residuo < sim.tolerance:
            trace.converged = True
            break

    return last_state
