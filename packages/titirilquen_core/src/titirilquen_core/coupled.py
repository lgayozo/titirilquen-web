"""Loop acoplado suelo ↔ transporte.

Estructura (V2):

    Iter 0: LandUseCity.build(T = flujo libre en min)  # baseline sin feedback
    Para n = 1..N_outer:
        1. poblacion = generar_poblacion_desde_land_use_det(city)
        2. transport_trace = run_msa(config, poblacion)
        3. T_new[i] = accesibilidad esperada (min), común por ubicación
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
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    IterationSnapshot,
    run_msa_con_poblacion,
)
from titirilquen_core.demand.utility import (
    UTIL_IMPOSIBLE,
    TiemposObservados,
    calcular_utilidades,
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
    """Residuo ||T_new - T_old||_∞ (min)."""
    metrics: EquilibriumMetrics
    """Reporte de métricas (por estrato + sistema) de esta iteración."""


@dataclass
class CoupledResult:
    """Resultado del loop acoplado."""

    iterations: list[OuterIteration] = field(default_factory=list)
    final_city: LandUseCity | None = None
    final_agents: list[Agente] = field(default_factory=list)
    converged: bool = False


# Velocidad de referencia (km/h) para el fallback en minutos de la 1ª iteración.
_V_REF_FALLBACK_KMH = 30.0


def _aggregate_T_expected(
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    snap: IterationSnapshot,
    n_strata: int,
    cbd_index: int,
) -> NDArray[np.float64]:
    """T[h, i] = accesibilidad (tiempo de viaje esperado) de la celda i hacia el
    CBD — **común a todos los estratos** (todas las filas h son iguales).

    Para cada estrato se computa la esperanza analítica del tiempo

        Te_h(i) = Σ_{auto} w_auto · Σ_m P(m | h,i,auto) · t_m(i)

    con `w_auto = prob_auto` (entre los que viajan; teletrabajo excluido) y
    `P(m|·)` el logit de modo sobre los tiempos del snapshot final; luego se
    devuelve la **media simple entre estratos** `T(i) = mean_h Te_h(i)`,
    replicada en todas las filas.

    Por qué común y no por estrato (ver D-22): la accesibilidad es un **atributo
    de la ubicación** en el bid-rent de suelo; la heterogeneidad entre usuarios
    ya la captura `α_h` (cuánto valora cada estrato la cercanía al CBD). Si en
    cambio T fuera por estrato, el menor tiempo de los estratos con más auto se
    leería como "la distancia no les molesta" e **invertiría** el ordenamiento
    (ricos a la periferia). El experimentado por estrato sí se reporta aparte en
    `coupled_metrics` a partir de los agentes.

    Es **determinista** y está definido en **todas** las celdas (no necesita el
    carry-forward para celdas vacías): el residual refleja sólo cambios reales,
    así que el loop exterior converge a ~0.
    """
    n = ciudad.n_celdas
    gl = sim.demand.globales
    tiempos = [
        TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        for i in range(n)
    ]
    T = np.zeros((n_strata, n), dtype=float)

    for h in range(n_strata):
        estrato = h + 1
        p_a = float(sim.demand.estratos[estrato].prob_auto)  # type: ignore[index]
        for i in range(n):
            if i == cbd_index:
                continue
            d_km = abs(i - cbd_index) * ciudad.ancho_celda_km
            t_modo = {
                "Auto": float(snap.t_auto[i]),
                "Metro": float(snap.t_tren_acceso[i] + snap.t_tren_espera[i] + snap.t_tren_viaje[i]),
                "Bici": float(snap.t_bici[i]),
                "Caminata": d_km / gl.v_caminata * 60.0,
            }
            num = 0.0
            den = 0.0
            for tiene_auto, w in ((True, p_a), (False, 1.0 - p_a)):
                if w <= 0:
                    continue
                utils = calcular_utilidades(
                    estrato=estrato,  # type: ignore[arg-type]
                    celda_origen=i,
                    tiene_auto=tiene_auto,
                    ciudad=ciudad,
                    config=sim.demand,
                    tiempos_observados=tiempos[i],
                    modos_habilitados=sim.modos_habilitados,
                )
                vals = [
                    (m, b.valor)
                    for m, b in utils.items()
                    if b.feasible and b.valor > UTIL_IMPOSIBLE
                ]
                if not vals:
                    continue  # rama sin modo factible (varado): no aporta tiempo
                mx = max(v for _, v in vals)
                exps = [(m, float(np.exp(v - mx))) for m, v in vals]
                Z = sum(e for _, e in exps)
                et = sum((e / Z) * t_modo[m] for m, e in exps)
                num += w * et
                den += w
            T[h, i] = (num / den) if den > 0 else d_km / _V_REF_FALLBACK_KMH * 60.0

    # Accesibilidad común por ubicación: media simple entre estratos, replicada
    # en todas las filas (ver docstring — evita la inversión del bid-rent).
    T_comun = T.mean(axis=0)
    return np.tile(T_comun, (n_strata, 1))


def _freeflow_T(
    ciudad: CiudadLineal, n_strata: int, v_ref_kmh: float
) -> NDArray[np.float64]:
    """Accesibilidad inicial **a flujo libre**, en minutos: T(i) = d_km(i)/v_ref·60.

    Es el baseline "sin feedback" honesto: el suelo se resuelve con una
    accesibilidad ingenua (tiempo a velocidad de referencia, ignorando modo,
    espera y congestión) pero **en la misma escala (minutos)** que las
    iteraciones acopladas. Antes el arranque usaba la distancia en índices de
    celda (`_default_T`), una escala ~3× mayor, lo que hacía que el salto iter0→
    final fuera mayormente un reescalado de unidades y no el efecto real del
    feedback de congestión (ver D-23).
    """
    cbd = ciudad.n_celdas // 2
    d_km = np.abs(np.arange(ciudad.n_celdas) - cbd).astype(float) * ciudad.ancho_celda_km
    t_min = d_km / v_ref_kmh * 60.0
    return np.tile(t_min, (n_strata, 1))


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
    # El loop acoplado usa asignación **esperada** (determinista) para que el
    # equilibrio suelo↔transporte converja sin el piso estocástico del Monte Carlo.
    sim_eq = sim.model_copy(update={"assignment": "expected"})
    L = sim.city.n_celdas
    CBD = L // 2
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)

    n_strata = len(land_use_config.H_por_estrato)
    # Baseline "sin feedback" en minutos a flujo libre (no índices de celda),
    # para que iter0→final mida el efecto real del feedback (ver D-23).
    T_init = _freeflow_T(ciudad, n_strata, sim.demand.globales.v_auto)
    city = LandUseCity.build(L=L, CBD=CBD, cfg=land_use_config, T=T_init, rng=rng)
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
        T_new = _aggregate_T_expected(sim_eq, ciudad, final_snap, n_strata, CBD)

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
        yield OuterIteration(
            outer_iter=outer,
            land_use=city.result,
            transport=transport_trace,
            T_matrix=T_state.copy(),
            T_residual=residual,
            metrics=metrics,
        )

        if is_converged:
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
    sim_eq = sim.model_copy(update={"assignment": "expected"})
    L = sim.city.n_celdas
    CBD = L // 2
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)

    result = CoupledResult()
    n_strata = len(land_use_config.H_por_estrato)
    # Baseline "sin feedback" en minutos a flujo libre (ver D-23).
    T_init = _freeflow_T(ciudad, n_strata, sim.demand.globales.v_auto)
    city = LandUseCity.build(L=L, CBD=CBD, cfg=land_use_config, T=T_init, rng=rng)
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
        T_new = _aggregate_T_expected(sim_eq, ciudad, final_snap, n_strata, CBD)
        residual = float("inf") if T_state is None else float(np.max(np.abs(T_new - T_state)))
        # Amortiguación MSA del loop externo.
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
        result.iterations.append(
            OuterIteration(
                outer_iter=outer,
                land_use=city.result,
                transport=transport_trace,
                T_matrix=T_state.copy(),
                T_residual=residual,
                metrics=metrics,
            )
        )

        if is_converged:
            result.converged = True
            break
        city.update(T=T_state, rng=rng)

    result.final_city = city
    if result.iterations:
        result.final_agents = result.iterations[-1].transport.agentes
    return result
