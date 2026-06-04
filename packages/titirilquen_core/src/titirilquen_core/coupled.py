"""Loop acoplado suelo ↔ transporte.

Estructura (V2):

    Iter 0: LandUseCity.build(T = dist(i, CBD))        # bootstrap
    Para n = 1..N_outer:
        1. poblacion = generar_poblacion_desde_land_use(city)
        2. transport_trace = run_msa(config, poblacion)
        3. T_new[h, i] = mean travel time por (estrato, celda)
        4. city.update(T_new)
        5. si ||T_new - T_old|| < tol_outer → break

Devuelve la trayectoria completa para visualizar cómo la ciudad y la red
co-evolucionan.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    IterationSnapshot,
    run_msa_con_poblacion,
)
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.equilibrium import LandUseResult
from titirilquen_core.population import Agente, generar_poblacion_desde_land_use


@dataclass
class OuterIteration:
    """Estado al final de una iteración del loop exterior suelo↔transporte."""

    outer_iter: int
    land_use: LandUseResult
    transport: ConvergenceTrace
    T_matrix: NDArray[np.float64]
    T_residual: float
    """Residuo ||T_new - T_old||_∞ (min)."""


@dataclass
class CoupledResult:
    """Resultado del loop acoplado."""

    iterations: list[OuterIteration] = field(default_factory=list)
    final_city: LandUseCity | None = None
    final_agents: list[Agente] = field(default_factory=list)
    converged: bool = False


# Velocidad de referencia (km/h) para el fallback en minutos de la 1ª iteración.
_V_REF_FALLBACK_KMH = 30.0


def _aggregate_T(
    agentes: list[Agente],
    snap: IterationSnapshot,
    n_strata: int,
    n_celdas: int,
    cbd_index: int,
    ancho_celda_km: float,
    T_prev: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    """Construye T[h, i] = tiempo de viaje esperado del estrato h desde la celda i.

    Se usa el tiempo (en minutos) del modo efectivamente elegido por cada agente
    (de la última iteración del MSA). Para celdas/estratos **sin agentes** de
    muestra:
      - si hay estado previo `T_prev`, se mantiene ese valor (carry-forward) —
        así el residual refleja sólo cambios reales y no el ruido de qué celdas
        quedaron vacías en cada sorteo;
      - en la 1ª iteración (sin `T_prev`), se usa un fallback **en minutos**
        (distancia km / velocidad de referencia · 60), no la distancia en
        índices de celda.
    """
    T = np.zeros((n_strata, n_celdas), dtype=float)
    counts = np.zeros((n_strata, n_celdas), dtype=int)

    for a in agentes:
        if a.modo_elegido is None or a.teletrabaja:
            continue
        h = a.estrato - 1
        i = a.celda_origen
        if a.modo_elegido == "Auto":
            t = snap.t_auto[i]
        elif a.modo_elegido == "Metro":
            t = snap.t_tren_acceso[i] + snap.t_tren_espera[i] + snap.t_tren_viaje[i]
        elif a.modo_elegido == "Bici":
            t = snap.t_bici[i]
        else:  # Caminata
            t = abs(i - cbd_index) * ancho_celda_km / 4.8 * 60  # dist_km / v_cam · 60
        T[h, i] += float(t)
        counts[h, i] += 1

    mask = counts > 0
    with np.errstate(invalid="ignore", divide="ignore"):
        T = np.where(mask, T / np.maximum(counts, 1), T)

    if T_prev is not None:
        T = np.where(mask, T, T_prev)
    else:
        dist_km = np.abs(np.arange(n_celdas) - cbd_index).astype(float) * ancho_celda_km
        fallback_min = dist_km / _V_REF_FALLBACK_KMH * 60.0
        T = np.where(mask, T, fallback_min[None, :])
    return T


def _run_transport_with_population(
    sim: SimulationConfig,
    agentes: list[Agente],
    ciudad: CiudadLineal,
    rng: np.random.Generator | None = None,
) -> tuple[ConvergenceTrace, IterationSnapshot]:
    """Corre el loop MSA de transporte usando una población ya construida.

    Reutiliza `run_msa_con_poblacion` de msa.py para evitar duplicar la lógica.
    """
    if rng is None:
        rng = np.random.default_rng(sim.seed)
    trace = run_msa_con_poblacion(sim, ciudad, agentes, rng)
    final_snap = trace.iteraciones[-1]
    return trace, final_snap


def iter_coupled(
    *,
    sim: SimulationConfig,
    land_use_config: LandUseConfig,
    outer_max_iter: int = 5,
    outer_tol: float = 1.0,
) -> Iterator[OuterIteration]:
    """Generador que emite una OuterIteration por cada paso del loop exterior.

    Ideal para SSE: el consumidor puede renderizar progreso en vivo.
    """
    rng = np.random.default_rng(sim.seed)
    L = sim.city.n_celdas
    CBD = L // 2
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)

    city = LandUseCity.build(L=L, CBD=CBD, cfg=land_use_config, rng=rng)

    n_strata = len(land_use_config.H_por_estrato)
    T_state: NDArray[np.float64] | None = None

    for outer in range(outer_max_iter):
        agentes = generar_poblacion_desde_land_use(
            land_use_city=city,
            demand_config=sim.demand,
            teletrabajo_factor=sim.city.teletrabajo_factor,
            rng=rng,
        )
        transport_trace, final_snap = _run_transport_with_population(sim, agentes, ciudad)
        T_new = _aggregate_T(
            agentes, final_snap, n_strata, L, CBD, ciudad.ancho_celda_km, T_state
        )

        residual = float("inf") if T_state is None else float(np.max(np.abs(T_new - T_state)))
        # Amortiguación MSA del loop externo: T_state ← θ·T_new + (1-θ)·T_state.
        if T_state is None:
            T_state = T_new
        else:
            theta = 1.0 / (outer + 1)
            T_state = theta * T_new + (1.0 - theta) * T_state

        assert city.result is not None
        yield OuterIteration(
            outer_iter=outer,
            land_use=city.result,
            transport=transport_trace,
            T_matrix=T_state.copy(),
            T_residual=residual,
        )

        if outer > 0 and residual < outer_tol:
            break
        city.update(T=T_state, rng=rng)


def run_coupled(
    *,
    sim: SimulationConfig,
    land_use_config: LandUseConfig,
    outer_max_iter: int = 5,
    outer_tol: float = 1.0,  # minutos
) -> CoupledResult:
    """Ejecuta el loop suelo↔transporte hasta el final y devuelve el resultado agregado.

    :param sim: configuración de transporte (`SimulationConfig` de V1).
    :param land_use_config: configuración del módulo de uso de suelo.
    :param outer_max_iter: iteraciones máximas del loop exterior.
    :param outer_tol: tolerancia en minutos sobre ||T_new - T_old||_∞.
    """
    rng = np.random.default_rng(sim.seed)
    L = sim.city.n_celdas
    CBD = L // 2
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)
    city = LandUseCity.build(L=L, CBD=CBD, cfg=land_use_config, rng=rng)

    result = CoupledResult()
    n_strata = len(land_use_config.H_por_estrato)
    T_state: NDArray[np.float64] | None = None

    for outer in range(outer_max_iter):
        agentes = generar_poblacion_desde_land_use(
            land_use_city=city,
            demand_config=sim.demand,
            teletrabajo_factor=sim.city.teletrabajo_factor,
            rng=rng,
        )
        transport_trace, final_snap = _run_transport_with_population(sim, agentes, ciudad)
        T_new = _aggregate_T(
            agentes, final_snap, n_strata, L, CBD, ciudad.ancho_celda_km, T_state
        )
        residual = float("inf") if T_state is None else float(np.max(np.abs(T_new - T_state)))
        # Amortiguación MSA del loop externo.
        if T_state is None:
            T_state = T_new
        else:
            theta = 1.0 / (outer + 1)
            T_state = theta * T_new + (1.0 - theta) * T_state

        assert city.result is not None
        result.iterations.append(
            OuterIteration(
                outer_iter=outer,
                land_use=city.result,
                transport=transport_trace,
                T_matrix=T_state.copy(),
                T_residual=residual,
            )
        )

        if outer > 0 and residual < outer_tol:
            result.converged = True
            break
        city.update(T=T_state, rng=rng)

    result.final_city = city
    if result.iterations:
        result.final_agents = result.iterations[-1].transport.agentes
    return result
