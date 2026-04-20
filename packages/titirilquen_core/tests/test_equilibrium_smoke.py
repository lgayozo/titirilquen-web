from __future__ import annotations

from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    PhysicalPenalties,
    SimulationConfig,
    StratumBetas,
    StratumConfig,
    SupplyConfig,
)
from titirilquen_core.equilibrium.msa import run_msa


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


def test_run_msa_smoke_pequena() -> None:
    """Smoke test: corre una simulación chica y verifica invariantes básicas."""
    sim = SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=5, densidad_por_celda=5),
        supply=SupplyConfig(),
        demand=_demand_config(),
        max_iter=3,
        seed=42,
    )
    trace = run_msa(sim)

    assert len(trace.iteraciones) == 3
    # Todos los agentes recibieron un modo
    for a in trace.agentes:
        assert a.modo_elegido is not None
    # Modal split suma a la población total
    last = trace.iteraciones[-1]
    total_agentes = len(trace.agentes)
    total_modal = sum(last.modal_split.values())
    assert total_modal == total_agentes


def test_run_msa_converge_con_tolerancia_alta() -> None:
    sim = SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=5, densidad_por_celda=5),
        supply=SupplyConfig(),
        demand=_demand_config(),
        max_iter=20,
        tolerance=1e6,  # absurdamente alta -> converge al 2do paso
        seed=42,
    )
    trace = run_msa(sim)
    assert trace.converged
    assert len(trace.iteraciones) < 20
