"""La lente Transporte de Comparar corre cada política con la `Q` de la tarjeta
base (D11c): estática comparativa de corto plazo, la misma gente en el mismo
lugar. Estos tests fijan las dos propiedades que lo hacen honesto: entregar la
`Q` de una corrida la reproduce exacta, y con la `Q` congelada una política que
sí mueve la localización a flujo libre ya no la mueve.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.test_linea_base import _config_web, _land_use_web
from titirilquen_core.equilibrium.msa import ConvergenceTrace, run_msa


def _gente(tr: ConvergenceTrace) -> list[tuple[int, int]]:
    return sorted((a.celda_origen, int(a.estrato)) for a in tr.agentes)


@pytest.fixture(scope="module")
def base() -> ConvergenceTrace:
    return run_msa(_config_web(), _land_use_web(), "equilibrio")


@pytest.fixture(scope="module")
def con_peaje():
    d = _config_web().model_dump()
    d["demand"]["globales"]["peaje_km"] = 275
    return type(_config_web()).model_validate(d)


def test_la_corrida_publica_la_q_con_que_se_poblo(base):
    Q = base.localizacion_Q
    assert Q is not None and Q.shape == (3, 201)
    original = run_msa(_config_web(), _land_use_web(), "original").localizacion_Q
    assert original is not None
    assert np.allclose(original, np.array([0.2, 0.5, 0.3])[:, None])


def test_la_q_de_una_corrida_la_reproduce_exacta(base):
    otra = run_msa(_config_web(), _land_use_web(), "equilibrio", Q_dada=base.localizacion_Q)
    assert [a.modo_elegido for a in otra.agentes] == [a.modo_elegido for a in base.agentes]
    assert otra.iteraciones[-1].modal_split == base.iteraciones[-1].modal_split
    assert len(otra.iteraciones) == len(base.iteraciones)


def test_con_la_q_congelada_la_politica_no_reubica_hogares(base, con_peaje):
    # Sin congelar, el peaje cambia la accesibilidad a flujo libre y la `Q`.
    propia = run_msa(con_peaje, _land_use_web(), "equilibrio")
    assert propia.localizacion_Q is not None and base.localizacion_Q is not None
    assert np.abs(propia.localizacion_Q - base.localizacion_Q).max() > 0.01
    assert _gente(propia) != _gente(base)
    # Congelada, la gente queda donde estaba y sólo cambia el transporte.
    congelada = run_msa(con_peaje, _land_use_web(), "equilibrio", Q_dada=base.localizacion_Q)
    assert _gente(congelada) == _gente(base)
    assert congelada.iteraciones[-1].modal_split != base.iteraciones[-1].modal_split


def test_q_dada_se_valida(base):
    Q = base.localizacion_Q
    assert Q is not None
    with pytest.raises(ValueError, match="forma"):
        run_msa(_config_web(), _land_use_web(), "equilibrio", Q_dada=Q[:, :-1])
    negativa = Q.copy()
    negativa[0, 100] = -0.1
    with pytest.raises(ValueError, match="no negativa"):
        run_msa(_config_web(), _land_use_web(), "equilibrio", Q_dada=negativa)
    with pytest.raises(ValueError, match="sumar 1"):
        run_msa(_config_web(), _land_use_web(), "equilibrio", Q_dada=Q * 0.9)
    with pytest.raises(ValueError, match="original"):
        run_msa(_config_web(), _land_use_web(), "original", Q_dada=Q)
