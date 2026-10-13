"""La brecha no amortiguada del MSA (D-39, D8).

El MSA promedia con paso 1/n. Hasta D8 su `residuo` medía el cambio del
promedio, que subestima el desajuste real en ~n veces; desde D8 mide la brecha
misma, `max |c(x(t)) − t|`, y es lo que decide la parada. `gap_final_min` la
recalcula una vez más sobre los tiempos que el loop entrega.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from tests._poblacion import suelo_uniforme
from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.equilibrium.msa import run_msa

SUELO = suelo_uniforme(2400)  # 300 hab/km × 8 km, como antes


def _sim(demand: DemandConfig, **kw) -> SimulationConfig:
    base = {
        "city": CityConfig(n_celdas=41, largo_ciudad_km=8),
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
    trace = run_msa(_sim(demanda_sintetica), SUELO)
    assert math.isfinite(trace.gap_final_min) and trace.gap_final_min >= 0.0


def test_el_residuo_es_la_brecha_no_amortiguada(demanda_sintetica: DemandConfig) -> None:
    """D8: con promedio de tiempos, `t_nuevo − t = f·(c(x(t)) − t)`, así que el
    cambio del iterado entre dos iteraciones es EXACTAMENTE `f · residuo`. Si el
    residuo volviera a ser el cambio amortiguado, la igualdad fallaría por un
    factor 1/f — que es justo lo que aflojaba la tolerancia sola."""
    trace = run_msa(_sim(demanda_sintetica, max_iter=6, tolerance=0.0), SUELO)

    def metro(s):
        return s.t_tren_acceso + s.t_tren_espera + s.t_tren_viaje

    for prev, snap in zip(trace.iteraciones[:-1], trace.iteraciones[1:], strict=True):
        cambio = max(
            np.max(np.abs(snap.t_auto - prev.t_auto)),
            np.max(np.abs(snap.t_bici - prev.t_bici)),
            np.max(np.abs(metro(snap) - metro(prev))),
        )
        assert snap.f_msa * snap.residuo == pytest.approx(cambio, rel=1e-9, abs=1e-12)


def test_una_tolerancia_mas_estricta_cierra_la_brecha(demanda_sintetica: DemandConfig) -> None:
    laxa = run_msa(_sim(demanda_sintetica, max_iter=8, tolerance=0.1), SUELO)
    estricta = run_msa(_sim(demanda_sintetica, max_iter=100, tolerance=1e-4), SUELO)
    assert estricta.gap_final_min < laxa.gap_final_min
