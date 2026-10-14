"""Todo o nada llega al equilibrio de usuario (D-70).

Hasta D-70 el MSA promediaba TIEMPOS también bajo `todo_o_nada`, y con 1 a 3
pistas el reparto oscilaba sin converger: el grupo marginal saltaba entero de
modo. Ahora promedia los FLUJOS de cada grupo —el MSA clásico del equilibrio de
usuario— y para cuando el costo en exceso medio (minutos que cada viajero paga
sobre el mínimo de su grupo) baja de `tolerance`.

Se corre la ciudad de la aplicación porque es ahí donde se midió la falla
(D-70, `docs/DISCREPANCIES.md`).
"""

from __future__ import annotations

from collections import Counter

import pytest

from tests.test_linea_base import _config_web, _land_use_web
from titirilquen_core.config import SimulationConfig
from titirilquen_core.constantes import MODOS
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo


def _corre(pistas: int) -> tuple[SimulationConfig, ConvergenceTrace]:
    d = _config_web().model_dump()
    d["supply"]["car"]["num_pistas"] = pistas
    d["assignment"] = "todo_o_nada"
    d["max_iter"] = 100  # el tope que la interfaz pone al elegir todo o nada
    sim = SimulationConfig.model_validate(d)
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, _land_use_web(), tr, localizacion="original"):
        pass
    return sim, tr


@pytest.fixture(scope="module", params=[1, 2, 3])
def corrida(request: pytest.FixtureRequest) -> tuple[SimulationConfig, ConvergenceTrace]:
    """Las pistas con que el MSA que promediaba tiempos no convergía."""
    return _corre(request.param)


def test_converge_bajo_la_tolerancia(corrida: tuple[SimulationConfig, ConvergenceTrace]) -> None:
    sim, tr = corrida
    assert tr.converged, f"agotó {len(tr.iteraciones)} iteraciones"
    assert len(tr.iteraciones) < sim.max_iter
    assert tr.iteraciones[-1].residuo < sim.tolerance
    # La brecha final es el mismo costo en exceso, sobre los tiempos que el
    # loop entrega.
    assert tr.gap_final_min < sim.tolerance


def test_el_costo_en_exceso_cae(corrida: tuple[SimulationConfig, ConvergenceTrace]) -> None:
    """No es monótono iteración a iteración, pero con el paso 1/n cae: lo de
    la última iteración es una fracción chica de lo de la primera."""
    _, tr = corrida
    residuos = [s.residuo for s in tr.iteraciones]
    assert residuos[-1] < residuos[0] / 5


def test_el_estado_final_es_el_reparto_promediado(
    corrida: tuple[SimulationConfig, ConvergenceTrace],
) -> None:
    """La demanda por estrato, el reparto de la última iteración y los modos por
    agente salen del mismo reparto promediado, no de una respuesta todo-o-nada
    nueva a los tiempos finales (que mandaría entero al grupo indiferente)."""
    _, tr = corrida
    split = tr.iteraciones[-1].modal_split
    assert tr.demanda_estrato is not None
    por_modo = tr.demanda_estrato.sum(axis=(0, 2))
    for k, m in enumerate(MODOS):
        assert por_modo[k] == pytest.approx(split[m], rel=1e-9)

    # Por agente: cuotas enteras de cada grupo, así que cada modo se aleja del
    # esperado a lo más en un viajero por grupo.
    viajeros = [a for a in tr.agentes if not a.teletrabaja]
    grupos = {(a.estrato, a.celda_origen, a.tiene_auto) for a in viajeros}
    conteo = Counter(a.modo_elegido for a in viajeros)
    for m in MODOS:
        assert abs(conteo[m] - split[m]) <= len(grupos)
    assert sum(conteo.values()) == len(viajeros)


def test_quedan_grupos_repartidos(corrida: tuple[SimulationConfig, ConvergenceTrace]) -> None:
    """En el equilibrio de usuario un grupo indiferente entre dos modos queda
    repartido: es la diferencia con tomar la respuesta todo-o-nada final."""
    _, tr = corrida
    modos: dict[tuple, set[str | None]] = {}
    for a in tr.agentes:
        if not a.teletrabaja:
            modos.setdefault((a.estrato, a.celda_origen, a.tiene_auto), set()).add(a.modo_elegido)
    assert sum(len(s) > 1 for s in modos.values()) > 0
