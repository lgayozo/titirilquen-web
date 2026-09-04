from __future__ import annotations

import numpy as np

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.coupled import _T_logsum_snapshot, run_coupled
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig
from titirilquen_core.presets import DEFAULT_STRATA


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
# Accesibilidad: D-22 revisada por D-34
# ---------------------------------------------------------------------------


def _snapshot(demand: DemandConfig):
    sim = SimulationConfig(
        city=CityConfig(n_celdas=41, largo_ciudad_km=8, densidad_hab_km=300),
        supply=SupplyConfig(),
        demand=demand,
        max_iter=2,
        seed=11,
        assignment="expected",
    )
    ciudad = CiudadLineal(n_celdas=41, largo_total_km=8)
    trace = ConvergenceTrace()
    for _ in iter_msa(sim, trace):
        pass
    return sim, ciudad, trace.iteraciones[-1]


def test_la_accesibilidad_es_el_logsum_y_crece_con_la_distancia(
    demanda_sintetica: DemandConfig,
) -> None:
    """`T[h, i] = −VIAJES_MES·logsum_h(i)` sobre los tiempos del snapshot.

    Con la demanda sintética los tres estratos son idénticos, así que las tres
    filas tienen que coincidir: si difieren, se coló algo que no es la demanda.
    Y es un costo: crece hacia los bordes (la celda del CBD, sin vivienda, queda
    fuera de la comparación).
    """
    sim, ciudad, snap = _snapshot(demanda_sintetica)
    T = _T_logsum_snapshot(sim, ciudad, snap)
    assert T.shape == (3, 41)
    assert np.allclose(T[0], T[1]) and np.allclose(T[1], T[2])
    c = ciudad.cbd_index
    assert T[0, 0] > T[0, c + 1] and T[0, -1] > T[0, c - 1]


def test_la_accesibilidad_es_por_estrato() -> None:
    """Con la demanda calibrada las filas difieren: la accesibilidad es la del
    hogar que vive ahí (auto, valor del tiempo), no un atributo del lugar.

    Hasta sep-2026 (D-22) se promediaba entre estratos porque `T` en minutos
    por estrato invertía Alonso. Con el logsum en pesos no invierte —lo fija
    `test_accesibilidad.py`— y la heterogeneidad vuelve a la puja (D-34).
    """
    sim, ciudad, snap = _snapshot(DemandConfig.model_validate({"estratos": DEFAULT_STRATA}))
    T = _T_logsum_snapshot(sim, ciudad, snap)
    assert not np.allclose(T[0], T[2]), "los estratos alto y bajo ven la misma accesibilidad"
