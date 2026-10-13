"""Estática comparativa del equilibrio de transporte: los signos que la teoría
exige a los efectos PROPIOS de cada palanca (criterio de aceptación del libro,
cap. 5). Encarecer un modo le quita viajes; mejorar su oferta se los da.

Sobre la configuración de la app con la localización «original» (población
fija), para que el efecto sea sólo de transporte. No se pinea magnitud: eso lo
hacen `test_linea_base.py` y los datos del libro; acá sólo el sentido.
"""

from __future__ import annotations

import pytest

from tests.test_linea_base import _config_web, _land_use_web
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo


def _reparto(cfg) -> dict[str, float]:
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(cfg, _land_use_web(), tr, localizacion="original"):
        pass
    assert tr.converged
    s = tr.iteraciones[-1].modal_split
    total = sum(s.values())
    return {m: 100.0 * v / total for m, v in s.items()}


def _con(ruta: tuple[str, str, str], valor: float):
    d = _config_web().model_dump()
    a, b, c = ruta
    d[a][b][c] = valor
    return type(_config_web()).model_validate(d)


@pytest.fixture(scope="module")
def base() -> dict[str, float]:
    return _reparto(_config_web())


@pytest.mark.parametrize(
    ("ruta", "valor", "modo", "signo"),
    [
        (("demand", "globales", "peaje_km"), 150.0, "Auto", -1),
        (("demand", "globales", "costo_tarifa_metro"), 0.0, "Metro", +1),
        (("supply", "car", "num_pistas"), 3, "Auto", +1),
        (("supply", "bike", "capacidad_pista"), 6000, "Bici", +1),
    ],
    ids=["peaje-baja-auto", "tarifa-cero-sube-metro", "pista-sube-auto", "ciclovia-sube-bici"],
)
def test_el_efecto_propio_tiene_el_signo_de_la_teoria(base, ruta, valor, modo, signo) -> None:
    cambio = _reparto(_con(ruta, valor))[modo] - base[modo]
    assert signo * cambio > 0.1, f"{modo}: {cambio:+.3f} pp"
