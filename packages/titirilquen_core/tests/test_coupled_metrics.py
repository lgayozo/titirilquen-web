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


def _run():
    sim = _sim_small()
    lu = _land_use_config()
    res = run_coupled(sim=sim, land_use_config=lu, outer_max_iter=2, outer_tol=0.1)
    return res.iterations[-1].metrics, sim, lu


def test_estructura_basica() -> None:
    m, _sim, lu = _run()
    assert len(m.por_estrato) == 3
    for h, sm in enumerate(m.por_estrato):
        assert sm.estrato == h + 1
    # n_hogares total ≈ Σ H (la oferta redistribuye el CBD, Σ S = Σ H)
    total = sum(s.n_hogares for s in m.por_estrato)
    assert abs(total - sum(lu.H_por_estrato)) < 1.0


def test_reparto_modal_suma_uno() -> None:
    m, _sim, _lu = _run()
    for sm in m.por_estrato:
        assert abs(sum(sm.reparto_modal.values()) - 1.0) < 1e-9
        assert set(sm.reparto_modal) == {
            "Auto", "Metro", "Bici", "Caminata", "Teletrabajo", "Varado",
        }
    assert abs(sum(m.sistema.reparto_modal.values()) - 1.0) < 1e-9


def test_valores_finitos_y_signos() -> None:
    m, _sim, _lu = _run()
    for sm in m.por_estrato:
        assert np.isfinite(sm.dist_media_cbd_km) and sm.dist_media_cbd_km >= 0
        assert np.isfinite(sm.tiempo_medio_min) and sm.tiempo_medio_min >= 0
        assert np.isfinite(sm.costo_medio_clp) and sm.costo_medio_clp >= 0
        # ΔCS vs red vacía: signo libre (congestión <0, Mohring >0), pero finito.
        assert np.isfinite(sm.delta_excedente_clp)
        assert np.isfinite(sm.carga_costo_ingreso) and sm.carga_costo_ingreso >= 0
    s = m.sistema
    assert 0.0 <= s.segregacion_theil <= 1.0
    assert s.tiempo_total_pax_min >= 0
    assert s.emisiones_total_kg >= 0
    assert s.iteraciones_exteriores >= 1


def test_consistencia_tiempo_sistema() -> None:
    """El tiempo medio del sistema = total / nº de viajeros; coherente con estratos."""
    m, _sim, _lu = _run()
    s = m.sistema
    if s.tiempo_total_pax_min > 0:
        assert s.tiempo_medio_min > 0
        # El medio del sistema debe caer dentro del rango de los medios por estrato
        medios = [sm.tiempo_medio_min for sm in m.por_estrato if sm.tiempo_medio_min > 0]
        assert min(medios) - 1e-6 <= s.tiempo_medio_min <= max(medios) + 1e-6


def test_regresividad_por_ingreso() -> None:
    """Con ingresos 100/50/10 y betas iguales, la carga costo/ingreso del estrato
    bajo supera a la del alto (regresivo)."""
    m, _sim, _lu = _run()
    if m.sistema.ratio_carga_bajo_alto is not None:
        assert m.sistema.ratio_carga_bajo_alto > 1.0


def test_bienestar_total_es_suma_ponderada() -> None:
    m, _sim, _lu = _run()
    esperado = sum(sm.delta_excedente_clp * sm.n_hogares for sm in m.por_estrato)
    assert abs(m.sistema.delta_bienestar_total_clp - esperado) < 1e-3
