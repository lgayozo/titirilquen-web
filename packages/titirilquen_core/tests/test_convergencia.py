"""La brecha no amortiguada del MSA (D-39, D8).

Hasta D8 el `residuo` medía el cambio del promedio, que con paso 1/n subestima
el desajuste real en ~n veces; desde D8 mide la brecha misma,
`max |c(x(t)) − t|`, y es lo que decide la parada. `gap_final_min` la recalcula
una vez más sobre los tiempos que el loop entrega. Desde la auditoría B
(oct-2026) el loop promedia flujos con paso halving y mide la brecha sobre el
objetivo. El sorteo por agente, que promediaba tiempos con 1/n, se retiró en
nov-2026.
"""

from __future__ import annotations

import math

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
    }
    base.update(kw)
    return SimulationConfig(**base)


def test_la_brecha_existe_y_es_finita(demanda_sintetica: DemandConfig) -> None:
    trace = run_msa(_sim(demanda_sintetica), SUELO)
    assert math.isfinite(trace.gap_final_min) and trace.gap_final_min >= 0.0


def test_una_tolerancia_mas_estricta_cierra_la_brecha(demanda_sintetica: DemandConfig) -> None:
    laxa = run_msa(_sim(demanda_sintetica, max_iter=8, tolerance=0.1), SUELO)
    estricta = run_msa(_sim(demanda_sintetica, max_iter=100, tolerance=1e-4), SUELO)
    assert estricta.gap_final_min < laxa.gap_final_min
