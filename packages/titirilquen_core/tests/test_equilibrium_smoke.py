from __future__ import annotations

from tests._poblacion import suelo_uniforme
from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.equilibrium.msa import run_msa


def test_run_msa_smoke_pequena(demanda_sintetica: DemandConfig) -> None:
    """Smoke test: corre una simulación chica y verifica invariantes básicas."""
    sim = SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=5),
        supply=SupplyConfig(),
        demand=demanda_sintetica,
        max_iter=3,
        seed=42,
    )
    trace = run_msa(sim, suelo_uniforme(250))

    assert len(trace.iteraciones) == 3
    # Todos los agentes recibieron un modo
    for a in trace.agentes:
        assert a.modo_elegido is not None
    # Modal split suma a la población total
    last = trace.iteraciones[-1]
    total_agentes = len(trace.agentes)
    total_modal = sum(last.modal_split.values())
    assert total_modal == total_agentes
    # Flujos de corredor expuestos en el trace (numerador del v/c). El flujo
    # acumulado domina a la demanda originada por celda y es 0 en el CBD.
    assert trace.flujos_auto_veh_h is not None
    assert trace.flujos_bici_veh_h is not None
    assert len(trace.flujos_auto_veh_h) == sim.city.n_celdas
    cbd = sim.city.n_celdas // 2
    assert trace.flujos_auto_veh_h[cbd] == 0
    assert trace.flujos_auto_veh_h.max() >= last.demanda_auto.max()


def test_run_msa_converge_con_tolerancia_alta(demanda_sintetica: DemandConfig) -> None:
    sim = SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=5),
        supply=SupplyConfig(),
        demand=demanda_sintetica,
        max_iter=20,
        tolerance=1e6,  # absurdamente alta -> converge al 2do paso
        seed=42,
    )
    trace = run_msa(sim, suelo_uniforme(250))
    assert trace.converged
    assert len(trace.iteraciones) < 20
