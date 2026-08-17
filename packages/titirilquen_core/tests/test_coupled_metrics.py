from __future__ import annotations

import numpy as np
import pytest

from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.coupled import run_coupled
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


@pytest.fixture(scope="module")
def corrida(demanda_sintetica_modulo: DemandConfig):
    sim = _sim_small(demanda_sintetica_modulo)
    lu = _land_use_config()
    res = run_coupled(sim=sim, land_use_config=lu, outer_max_iter=2, outer_tol=0.1)
    return res.iterations[-1].metrics, sim, lu


def test_estructura_basica(corrida) -> None:
    m, _sim, lu = corrida
    assert len(m.por_estrato) == 3
    for h, sm in enumerate(m.por_estrato):
        assert sm.estrato == h + 1
    # n_hogares total ≈ Σ H (la oferta redistribuye el CBD, Σ S = Σ H)
    total = sum(s.n_hogares for s in m.por_estrato)
    assert abs(total - sum(lu.H_por_estrato)) < 1.0


def test_reparto_modal_suma_uno(corrida) -> None:
    m, _sim, _lu = corrida
    for sm in m.por_estrato:
        assert abs(sum(sm.reparto_modal.values()) - 1.0) < 1e-9
        assert set(sm.reparto_modal) == {
            "Auto",
            "Metro",
            "Bici",
            "Caminata",
            "Teletrabajo",
            "Varado",
        }
    assert abs(sum(m.sistema.reparto_modal.values()) - 1.0) < 1e-9


def test_valores_finitos_y_signos(corrida) -> None:
    m, _sim, _lu = corrida
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


def test_consistencia_tiempo_sistema(corrida) -> None:
    """El tiempo medio del sistema = total / nº de viajeros; coherente con estratos."""
    m, _sim, _lu = corrida
    s = m.sistema
    if s.tiempo_total_pax_min > 0:
        assert s.tiempo_medio_min > 0
        # El medio del sistema debe caer dentro del rango de los medios por estrato
        medios = [sm.tiempo_medio_min for sm in m.por_estrato if sm.tiempo_medio_min > 0]
        assert min(medios) - 1e-6 <= s.tiempo_medio_min <= max(medios) + 1e-6


def test_regresividad_por_ingreso(corrida) -> None:
    """Con ingresos 100/50/10 y betas iguales, la carga costo/ingreso del estrato
    bajo supera a la del alto (regresivo)."""
    m, _sim, _lu = corrida
    if m.sistema.ratio_carga_bajo_alto is not None:
        assert m.sistema.ratio_carga_bajo_alto > 1.0


def test_bienestar_total_es_suma_ponderada(corrida) -> None:
    m, _sim, _lu = corrida
    esperado = sum(sm.delta_excedente_clp * sm.n_hogares for sm in m.por_estrato)
    assert abs(m.sistema.delta_bienestar_total_clp - esperado) < 1e-3


# ---------------------------------------------------------------------------
# La medida del excedente sigue al método (emparejamiento con el Sandbox)
# ---------------------------------------------------------------------------
#
# Esta página calculaba su propio logsum y no aplicaba el emparejamiento, así
# que bajo `todo_o_nada` medía el bienestar con una regla distinta de la del
# Sandbox para el mismo escenario. Nada lo detectaba: los dos números eran
# plausibles.


@pytest.mark.parametrize(
    ("metodo", "esperada"),
    [
        ("montecarlo", "logsum"),
        ("expected", "logsum"),
        ("todo_o_nada", "utilidad_maxima"),
    ],
)
def test_la_medida_sigue_al_metodo(
    demanda_sintetica: DemandConfig, metodo: str, esperada: str
) -> None:
    sim = _sim_small(demanda_sintetica)
    sim.assignment = metodo
    res = run_coupled(sim=sim, land_use_config=_land_use_config(), outer_max_iter=1, outer_tol=0.1)
    assert res.iterations[-1].metrics.sistema.medida_bienestar == esperada


def test_el_nucleo_decide_la_medida_una_sola_vez(demanda_sintetica: DemandConfig) -> None:
    """La página acoplada y el Sandbox deben coincidir para la misma config.

    Es el punto del refactor: una sola implementación (`medidas_de_utilidad`) y
    un solo criterio (`medida_emparejada`). Si alguien reintroduce un logsum
    local en `coupled_metrics`, este test no lo ve — pero sí ve que el criterio
    se bifurque, que es como empezaría.
    """
    from titirilquen_core.bienestar import medida_emparejada

    sim = _sim_small(demanda_sintetica)
    sim.assignment = "todo_o_nada"
    res = run_coupled(sim=sim, land_use_config=_land_use_config(), outer_max_iter=1, outer_tol=0.1)
    acoplada = res.iterations[-1].metrics.sistema.medida_bienestar
    assert acoplada == medida_emparejada(sim.assignment)
