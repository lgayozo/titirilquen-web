"""La brecha no amortiguada del MSA (D-39).

El MSA promedia con paso 1/n y su `residuo` mide el cambio del promedio, que
subestima el desajuste real en ~n veces. `gap_final_min` recalcula demanda y
oferta al estado final y mide cuánto se moverían los tiempos sin amortiguar:
es la cifra que acota lo que «convergió» sugiere.
"""

from __future__ import annotations

import math

from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.equilibrium.msa import run_msa


def _sim(demand: DemandConfig, **kw) -> SimulationConfig:
    base = {
        "city": CityConfig(n_celdas=41, largo_ciudad_km=8, densidad_hab_km=300),
        "supply": SupplyConfig(),
        "demand": demand,
        "max_iter": 8,
        "tolerance": 0.1,
        "seed": 11,
        "assignment": "expected",
    }
    base.update(kw)
    return SimulationConfig(**base)


def test_la_brecha_existe_y_es_finita(demanda_sintetica: DemandConfig) -> None:
    trace = run_msa(_sim(demanda_sintetica))
    assert math.isfinite(trace.gap_final_min) and trace.gap_final_min >= 0.0


def test_la_brecha_supera_al_residuo_amortiguado(demanda_sintetica: DemandConfig) -> None:
    """Es la razón de ser del indicador: si fuera menor o igual que el residuo,
    el residuo ya acotaría el desajuste y no haría falta."""
    trace = run_msa(_sim(demanda_sintetica))
    assert trace.gap_final_min >= trace.iteraciones[-1].residuo - 1e-9


def test_una_tolerancia_mas_estricta_cierra_la_brecha(demanda_sintetica: DemandConfig) -> None:
    laxa = run_msa(_sim(demanda_sintetica, max_iter=8, tolerance=0.1))
    estricta = run_msa(_sim(demanda_sintetica, max_iter=100, tolerance=1e-4))
    assert estricta.gap_final_min < laxa.gap_final_min
