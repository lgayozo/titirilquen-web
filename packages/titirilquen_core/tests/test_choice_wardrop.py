"""Elección determinística (Wardrop) — el reparto degenerado del grupo.

Se testea la función pura, con utilidades armadas a mano: es el punto donde
`assignment="wardrop"` se separa del logit, y el resto del MSA no cambia.
"""

from __future__ import annotations

import pytest

from titirilquen_core.demand.choice import (
    probabilidades_logit,
    probabilidades_wardrop,
)
from titirilquen_core.demand.utility import UTIL_IMPOSIBLE, UtilityBreakdown


def _u(valor: float, feasible: bool = True) -> UtilityBreakdown:
    return UtilityBreakdown("Auto", valor, 0.0, 0.0, 0.0, feasible=feasible)


def test_toda_la_masa_al_mejor_modo() -> None:
    utils = {"Auto": _u(-2.0), "Metro": _u(-1.0), "Bici": _u(-5.0)}
    p = probabilidades_wardrop(utils)  # type: ignore[arg-type]
    assert p == {"Auto": 0.0, "Metro": 1.0, "Bici": 0.0}


def test_ignora_modos_infeasibles_aunque_tengan_mejor_valor() -> None:
    """Un modo fuera de dominio no puede ganar: `calcular_utilidades` le pone
    UTIL_IMPOSIBLE, pero el filtro real es la bandera `feasible`."""
    utils = {
        "Auto": _u(10.0, feasible=False),
        "Metro": _u(-1.0),
        "Bici": _u(UTIL_IMPOSIBLE, feasible=False),
    }
    p = probabilidades_wardrop(utils)  # type: ignore[arg-type]
    assert p["Metro"] == 1.0
    assert p["Auto"] == 0.0


def test_empate_se_reparte_en_partes_iguales() -> None:
    """Sin esto, el desempate saldría del orden del diccionario y metería un
    sesgo estable entre iteraciones del MSA."""
    utils = {"Auto": _u(-1.0), "Metro": _u(-1.0), "Bici": _u(-3.0)}
    p = probabilidades_wardrop(utils)  # type: ignore[arg-type]
    assert p["Auto"] == pytest.approx(0.5)
    assert p["Metro"] == pytest.approx(0.5)
    assert p["Bici"] == 0.0


def test_sin_modos_factibles_devuelve_todo_cero() -> None:
    utils = {"Auto": _u(1.0, feasible=False), "Metro": _u(1.0, feasible=False)}
    p = probabilidades_wardrop(utils)  # type: ignore[arg-type]
    assert sum(p.values()) == 0.0


def test_es_el_limite_del_logit_al_escalar_las_utilidades() -> None:
    """Multiplicar todas las utilidades por c -> infinito lleva el logit al
    reparto de Wardrop. Es la razón por la que la paradoja de Downs-Thomson
    aparece con betas x20 y no con los estimados (docs/CONTINUAR.md §5)."""
    base = {"Auto": -2.0, "Metro": -1.0, "Bici": -5.0}
    escalado = {m: _u(v * 200) for m, v in base.items()}
    logit = probabilidades_logit(escalado)  # type: ignore[arg-type]
    wardrop = probabilidades_wardrop({m: _u(v) for m, v in base.items()})  # type: ignore[arg-type]
    for m in base:
        assert logit[m] == pytest.approx(wardrop[m], abs=1e-9)


def test_las_probabilidades_suman_uno() -> None:
    utils = {"Auto": _u(-2.0), "Metro": _u(-1.0), "Bici": _u(-5.0, feasible=False)}
    assert sum(probabilidades_wardrop(utils).values()) == pytest.approx(1.0)  # type: ignore[arg-type]
