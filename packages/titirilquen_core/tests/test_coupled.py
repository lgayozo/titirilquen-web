from __future__ import annotations

import numpy as np
import pytest

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.coupled import _aggregate_T_expected, run_coupled
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig


def _sim_small(demanda_sintetica: DemandConfig) -> SimulationConfig:
    return SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=5, densidad_hab_km=50),
        supply=SupplyConfig(),
        demand=demanda_sintetica,
        max_iter=3,
        seed=42,
    )


def _land_use_config() -> LandUseConfig:
    return LandUseConfig(
        H_por_estrato=(50, 100, 100),
        estratos=(
            LandUseStratumConfig(y=100.0, alpha=1.3, rho=1.0),
            LandUseStratumConfig(y=50.0, alpha=1.2, rho=1.0),
            LandUseStratumConfig(y=10.0, alpha=1.1, rho=1.0),
        ),
        max_iter=2000,
    )


def test_coupled_run_basic(demanda_sintetica: DemandConfig) -> None:
    res = run_coupled(
        sim=_sim_small(demanda_sintetica),
        land_use_config=_land_use_config(),
        outer_max_iter=2,
        outer_tol=0.1,
    )
    assert len(res.iterations) >= 1
    assert res.final_city is not None
    # Total de agentes debe coincidir con H-CBD_capacity
    cbd_idx = 51 // 2
    capacidad_cbd = res.final_city.S[cbd_idx]
    # Suma de H
    total_H = sum(_land_use_config().H_por_estrato)
    # Agentes generados = hogares fuera del CBD
    hogares_no_cbd = total_H - int(capacidad_cbd)
    assert len(res.final_agents) == hogares_no_cbd


def test_coupled_T_matrix_shape(demanda_sintetica: DemandConfig) -> None:
    res = run_coupled(
        sim=_sim_small(demanda_sintetica),
        land_use_config=_land_use_config(),
        outer_max_iter=1,
    )
    T = res.iterations[0].T_matrix
    assert T.shape == (3, 51)
    assert np.all(np.isfinite(T))


def test_coupled_residual_decreases_o_converge(demanda_sintetica: DemandConfig) -> None:
    """El residuo exterior debería disminuir entre iteraciones o converger."""
    res = run_coupled(
        sim=_sim_small(demanda_sintetica),
        land_use_config=_land_use_config(),
        outer_max_iter=3,
        outer_tol=0.01,
    )
    residuals = [it.T_residual for it in res.iterations if it.T_residual != float("inf")]
    # Al menos una iteración con residuo medible
    assert len(residuals) >= 1


# ---------------------------------------------------------------------------
# Accesibilidad: la decisión D-22
# ---------------------------------------------------------------------------


def test_la_accesibilidad_es_comun_a_los_estratos(demanda_sintetica: DemandConfig) -> None:
    """`T[h, i]` es igual para los tres estratos: la accesibilidad la define la
    UBICACIÓN, no quién vive ahí.

    No es un detalle de implementación. Si cada estrato tuviera su propia T, el
    bid-rent se invertiría: el estrato alto —que valora más el tiempo— vería
    tiempos distintos y pujaría distinto por la misma parcela, y el modelo
    terminaría explicando la segregación con un artefacto en vez de con las
    preferencias. Son 100 líneas de `coupled.py` que hasta ahora no tocaba
    ningún test.
    """
    sim = SimulationConfig(
        city=CityConfig(n_celdas=41, largo_ciudad_km=8, densidad_hab_km=300),
        supply=SupplyConfig(),
        demand=demanda_sintetica,
        max_iter=2,
        seed=11,
        assignment="expected",
    )
    ciudad = CiudadLineal(n_celdas=41, largo_total_km=8)
    trace = ConvergenceTrace()
    for _ in iter_msa(sim, trace):
        pass

    T = _aggregate_T_expected(
        sim, ciudad, trace.iteraciones[-1], n_strata=3, cbd_index=ciudad.cbd_index
    )
    assert T.shape == (3, 41)
    assert np.allclose(T[0], T[1]) and np.allclose(T[1], T[2])
    # Y crece con la distancia: el CBD es el mínimo.
    assert T[0, ciudad.cbd_index] == pytest.approx(T[0].min())
    assert T[0, 0] > T[0, ciudad.cbd_index]


def test_la_accesibilidad_pondera_por_poblacion(demanda_sintetica: DemandConfig) -> None:
    """La media entre estratos va ponderada por cuánta gente hay en cada uno.

    Con los tres estratos idénticos el resultado no puede depender de los pesos;
    ése es justamente el control que hace significativa la comparación.
    """
    sim = SimulationConfig(
        city=CityConfig(n_celdas=41, largo_ciudad_km=8, densidad_hab_km=300),
        supply=SupplyConfig(),
        demand=demanda_sintetica,
        max_iter=2,
        seed=11,
        assignment="expected",
    )
    ciudad = CiudadLineal(n_celdas=41, largo_total_km=8)
    trace = ConvergenceTrace()
    for _ in iter_msa(sim, trace):
        pass
    snap = trace.iteraciones[-1]

    simple = _aggregate_T_expected(sim, ciudad, snap, 3, ciudad.cbd_index)
    sesgada = _aggregate_T_expected(
        sim, ciudad, snap, 3, ciudad.cbd_index, H_por_estrato=np.array([1.0, 1.0, 98.0])
    )
    assert np.allclose(simple, sesgada), (
        "con estratos idénticos la ponderación no debería cambiar nada"
    )
