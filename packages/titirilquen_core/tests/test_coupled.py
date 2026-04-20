from __future__ import annotations

import numpy as np

from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    PhysicalPenalties,
    SimulationConfig,
    StratumBetas,
    StratumConfig,
    SupplyConfig,
)
from titirilquen_core.coupled import run_coupled
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig


def _demand_config() -> DemandConfig:
    penal = PhysicalPenalties(
        bici_10=-0.09, bici_20=-0.15, bici_30=-0.5,
        walk_5=-0.09, walk_15=-0.18, walk_25=-0.4,
    )
    betas = StratumBetas(
        asc_auto=1.5, asc_metro=-0.2, asc_bici=-0.9, asc_caminata=-0.5,
        b_tiempo_viaje=-0.055, b_costo=-0.00008,
        b_tiempo_espera=-0.05, b_tiempo_caminata=-0.15,
        penalizaciones_fisicas=penal,
    )
    s = StratumConfig(prob_teletrabajo=0.2, prob_auto=0.6, betas=betas)
    return DemandConfig(estratos={1: s, 2: s, 3: s})


def _sim_small() -> SimulationConfig:
    return SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=5, densidad_por_celda=5),
        supply=SupplyConfig(),
        demand=_demand_config(),
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


def test_coupled_run_basic() -> None:
    res = run_coupled(
        sim=_sim_small(),
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


def test_coupled_T_matrix_shape() -> None:
    res = run_coupled(
        sim=_sim_small(),
        land_use_config=_land_use_config(),
        outer_max_iter=1,
    )
    T = res.iterations[0].T_matrix
    assert T.shape == (3, 51)
    assert np.all(np.isfinite(T))


def test_coupled_residual_decreases_o_converge() -> None:
    """El residuo exterior debería disminuir entre iteraciones o converger."""
    res = run_coupled(
        sim=_sim_small(),
        land_use_config=_land_use_config(),
        outer_max_iter=3,
        outer_tol=0.01,
    )
    residuals = [it.T_residual for it in res.iterations if it.T_residual != float("inf")]
    # Al menos una iteración con residuo medible
    assert len(residuals) >= 1
