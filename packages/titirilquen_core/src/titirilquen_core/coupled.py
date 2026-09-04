"""Loop acoplado suelo ↔ transporte.

Estructura (V2):

    Iter 0: LandUseCity.build(T = logsum mensual a flujo libre)  # baseline sin feedback
    Para n = 1..N_outer:
        1. poblacion = generar_poblacion_desde_land_use_det(city)
        2. transport_trace = run_msa(config, poblacion)
        3. T_new[h, i] = −VIAJES_MES·logsum_h(i) sobre los tiempos finales
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
from titirilquen_core.coupled_metrics import (
    EquilibriumMetrics,
    compute_equilibrium_metrics,
)
from titirilquen_core.demand.utility import TiemposObservados
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    IterationSnapshot,
    run_msa_con_poblacion,
)
from titirilquen_core.land_use.accesibilidad import (
    T_desde_logsum,
    T_flujo_libre,
    logsum_por_celda,
)
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.equilibrium import LandUseResult
from titirilquen_core.population import (
    Agente,
    generar_poblacion_desde_land_use_det,
)


@dataclass
class OuterIteration:
    """Estado al final de una iteración del loop exterior suelo↔transporte."""

    outer_iter: int
    land_use: LandUseResult
    transport: ConvergenceTrace
    T_matrix: NDArray[np.float64]
    T_residual: float
    """Residuo ||T_new - T_old||_∞ (utiles de transporte por mes)."""
    metrics: EquilibriumMetrics
    """Reporte de métricas (por estrato + sistema) de esta iteración."""


@dataclass
class CoupledResult:
    """Resultado del loop acoplado."""

    iterations: list[OuterIteration] = field(default_factory=list)
    final_city: LandUseCity | None = None
    final_agents: list[Agente] = field(default_factory=list)
    converged: bool = False


def _tiempos_del_snapshot(snap: IterationSnapshot, n: int) -> list[TiemposObservados]:
    return [
        TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        for i in range(n)
    ]


def _T_logsum_snapshot(
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    snap: IterationSnapshot,
) -> NDArray[np.float64]:
    """`T[h, i]` = accesibilidad mensual **por estrato** sobre los tiempos del
    snapshot final: `−VIAJES_MES · logsum_h(i)` (ver `land_use.accesibilidad`).

    Hasta sep-2026 acá se devolvía el tiempo esperado en minutos, promediado
    entre estratos (D-22), porque por estrato invertía Alonso. Con el logsum en
    pesos eso no pasa (`tests/test_accesibilidad.py`), y la heterogeneidad de
    acceso —auto, valor del tiempo— vuelve a ser parte de la puja, que es donde
    corresponde (D-34). Es determinista y está definido en todas las celdas,
    así que el residual del loop exterior refleja sólo cambios reales."""
    tiempos = _tiempos_del_snapshot(snap, ciudad.n_celdas)
    return T_desde_logsum(logsum_por_celda(sim.demand, ciudad, tiempos, sim.modos_habilitados))


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
    result: CoupledResult | None = None,
) -> Iterator[OuterIteration]:
    """Generador que emite una OuterIteration por cada paso del loop exterior.

    Ideal para SSE: el consumidor puede renderizar progreso en vivo. Si se pasa
    `result`, lo popula por completo en el mismo recorrido (iteraciones, ciudad
    final, agentes, convergencia) — mismo patrón que `iter_msa(trace=...)`;
    `run_coupled` no es más que consumir este generador con un `result`.
    """
    rng = np.random.default_rng(sim.seed)
    # El loop acoplado usa asignación **esperada** (determinista) para que el
    # equilibrio suelo↔transporte converja sin el piso estocástico del Monte Carlo.
    sim_eq = sim.model_copy(update={"assignment": "expected"})
    L = sim.city.n_celdas
    CBD = L // 2
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)

    # Baseline "sin feedback": la misma accesibilidad (logsum mensual) a flujo
    # libre, en la misma escala que las iteraciones (D-23, D-34).
    T_init = T_flujo_libre(sim.demand, L, CBD, ciudad.ancho_celda_km, sim.modos_habilitados)
    city = LandUseCity.build(
        L=L,
        CBD=CBD,
        cfg=land_use_config,
        T=T_init,
        rng=rng,
        # Ancho físico real: la penalización ρ usa densidad hogares/km (D-26).
        ancho_celda_km=ciudad.ancho_celda_km,
    )
    T_state: NDArray[np.float64] | None = None

    for outer in range(outer_max_iter):
        assert city.result is not None
        agentes = generar_poblacion_desde_land_use_det(
            Q=city.result.Q,
            S=city.S,
            cbd_index=CBD,
            demand_config=sim.demand,
            teletrabajo_factor=sim.city.teletrabajo_factor,
        )
        transport_trace, final_snap = _run_transport_with_population(sim_eq, agentes, ciudad)
        T_new = _T_logsum_snapshot(sim_eq, ciudad, final_snap)

        residual = float("inf") if T_state is None else float(np.max(np.abs(T_new - T_state)))
        # Amortiguación MSA del loop externo: T_state ← θ·T_new + (1-θ)·T_state.
        if T_state is None:
            T_state = T_new
        else:
            theta = 1.0 / (outer + 1)
            T_state = theta * T_new + (1.0 - theta) * T_state

        assert city.result is not None
        is_converged = outer > 0 and residual < outer_tol
        metrics = compute_equilibrium_metrics(
            land_use=city.result,
            trace=transport_trace,
            S=city.S,
            sim=sim,
            land_use_config=land_use_config,
            T_residual=residual,
            converged=is_converged,
            iterations_count=outer + 1,
        )
        iteration = OuterIteration(
            outer_iter=outer,
            land_use=city.result,
            transport=transport_trace,
            T_matrix=T_state.copy(),
            T_residual=residual,
            metrics=metrics,
        )
        if result is not None:
            result.iterations.append(iteration)
        yield iteration

        if is_converged:
            if result is not None:
                result.converged = True
            break
        city.update(T=T_state, rng=rng)

    if result is not None:
        result.final_city = city
        if result.iterations:
            result.final_agents = result.iterations[-1].transport.agentes


def run_coupled(
    *,
    sim: SimulationConfig,
    land_use_config: LandUseConfig,
    outer_max_iter: int = 5,
    outer_tol: float = 1.0,  # minutos
) -> CoupledResult:
    """Ejecuta el loop suelo↔transporte hasta el final y devuelve el resultado agregado.

    Es simplemente consumir `iter_coupled` con un `result` (un único recorrido).

    :param sim: configuración de transporte (`SimulationConfig` de V1).
    :param land_use_config: configuración del módulo de uso de suelo.
    :param outer_max_iter: iteraciones máximas del loop exterior.
    :param outer_tol: tolerancia en minutos sobre ||T_new - T_old||_∞.
    """
    result = CoupledResult()
    for _ in iter_coupled(
        sim=sim,
        land_use_config=land_use_config,
        outer_max_iter=outer_max_iter,
        outer_tol=outer_tol,
        result=result,
    ):
        pass
    return result
