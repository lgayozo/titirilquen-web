"""El contrato de salida del core: claves, tipos y JSON válido.

Sustituye al test provisional que comparaba a mano las claves de los dos
serializadores gemelos (uno en la API, otro embebido como texto dentro de
`pyodide.worker.ts`). Ya no hay dos: ambos runtimes importan
`titirilquen_core.serializacion`, así que lo único que queda por vigilar es
que la forma declarada en los `TypedDict` sea la que realmente se emite.

Las claves se leen de los propios `TypedDict` — si alguien agrega un campo al
tipo y olvida emitirlo (o al revés), el test falla sin tener que mantener una
lista a mano en ninguna parte.
"""

from __future__ import annotations

import json
import math
from typing import get_type_hints

import pytest

from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.serializacion import (
    AgenteDict,
    LandUseResultDict,
    LandUseSolveDict,
    SnapshotDict,
    TraceDict,
    iteration_to_dict,
    land_use_city_to_dict,
    trace_to_dict,
)


@pytest.fixture(scope="module")
def trace(demanda_sintetica_modulo: DemandConfig) -> ConvergenceTrace:
    """Una corrida chica, reutilizada por todos los tests del módulo."""
    cfg = SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=10, densidad_hab_km=400),
        supply=SupplyConfig(),
        demand=demanda_sintetica_modulo,
        max_iter=2,
        seed=7,
        assignment="expected",
    )
    tr = ConvergenceTrace()
    for _ in iter_msa(cfg, tr):
        pass
    return tr


def test_trace_emite_exactamente_las_claves_declaradas(trace: ConvergenceTrace) -> None:
    assert set(trace_to_dict(trace)) == set(get_type_hints(TraceDict))


def test_snapshot_emite_exactamente_las_claves_declaradas(trace: ConvergenceTrace) -> None:
    assert set(iteration_to_dict(trace.iteraciones[0])) == set(get_type_hints(SnapshotDict))


def test_agente_emite_exactamente_las_claves_declaradas(trace: ConvergenceTrace) -> None:
    agente = trace_to_dict(trace)["agentes"][0]
    assert set(agente) == set(get_type_hints(AgenteDict))


def test_el_resultado_es_json_serializable(trace: ConvergenceTrace) -> None:
    """Ningún `ndarray` ni `inf` puede filtrarse: al otro lado hay un JSON."""
    crudo = json.dumps(trace_to_dict(trace))
    assert "NaN" not in crudo and "Infinity" not in crudo


def test_el_residuo_infinito_de_la_primera_iteracion_sale_como_null(
    trace: ConvergenceTrace,
) -> None:
    """`inf` no es JSON válido, y la primera iteración no tiene con qué
    comparar. Se emite `None`."""
    assert math.isinf(trace.iteraciones[0].residuo)
    assert iteration_to_dict(trace.iteraciones[0])["residuo"] is None


def test_demanda_estrato_llega_como_cubo(trace: ConvergenceTrace) -> None:
    """La regresión que motivó unificar los serializadores: sin este campo,
    `agregados.ts` devuelve todos los KPI de bienestar en cero, sin error."""
    cubo = trace_to_dict(trace)["demanda_estrato"]
    assert cubo is not None
    assert len(cubo) == 3  # estratos
    assert len(cubo[0]) == 4  # modos
    assert len(cubo[0][0]) == 51  # celdas


def test_uso_de_suelo_emite_las_claves_declaradas() -> None:
    city = LandUseCity.build(
        L=51,
        CBD=25,
        cfg=LandUseConfig(H_por_estrato=(100, 200, 300)),
        ancho_celda_km=10 / 51,
    )
    salida = land_use_city_to_dict(city)
    assert set(salida) == set(get_type_hints(LandUseSolveDict))
    assert set(salida["result"]) == set(get_type_hints(LandUseResultDict))
    json.dumps(salida)  # y es serializable
