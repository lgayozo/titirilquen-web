"""Las fórmulas cerradas del informe contra la simulación y contra `ibl.py`."""

from __future__ import annotations

import numpy as np
import pytest

from experimentos import (
    Caso,
    delta_critico,
    gauss_logistica,
    p_post_analitica,
    peso_shocks,
    simular,
    vida_media,
)
from ibl import pesos_ibl


def _caso() -> Caso:
    # Auto mejor por 1 útil (P = 0,731), β = −0,0331 → A = 30,2 min.
    return Caso(
        nombre="T",
        estrato=1,
        celda=0,
        km=0.0,
        tau=np.array([10.0, 20.0]),
        t_total=np.array([10.0, 30.0]),
        v_ref=np.array([0.0, -1.0]),
        beta=-0.0331,
    )


@pytest.mark.parametrize("d", [0.0, 0.5, 1.28])
@pytest.mark.parametrize("k", [1, 3, 10])
def test_w_k_es_el_peso_de_ibl_con_k_dias_seguidos(k: int, d: float) -> None:
    a = np.ones((1, k + 1, 1), dtype=bool)  # prior + k días consecutivos
    w = pesos_ibl(a, t=k + 1, d=d)
    assert w[0, 1:, 0].sum() == pytest.approx(peso_shocks(k, d))


def test_con_d_cero_w_k_es_k_sobre_k_mas_uno() -> None:
    for k in (1, 2, 5):
        assert peso_shocks(k, 0.0) == pytest.approx(k / (k + 1))


def test_delta_critico_anula_la_ventaja() -> None:
    c = _caso()
    for k in (1, 3):
        assert p_post_analitica(c, k, 0.5, delta_critico(c, k, 0.5)) == pytest.approx(0.5)


def test_con_d_cero_la_simulacion_reproduce_la_formula_exacta() -> None:
    # Sin ruido y con d = 0 la percepción tras k shocks no depende de cuándo ocurrieron.
    c = _caso()
    for k, delta in ((1, 40.0), (3, 20.0)):
        r = simular(c, d=0.0, k=k, delta=delta, replicas=200, dias=40)
        ok = ~np.isnan(r["p_post"])
        assert ok.mean() > 0.9
        assert r["p_post"][ok] == pytest.approx(p_post_analitica(c, k, 0.0, delta))


def test_sin_ruido_ni_shock_la_persona_no_aprende_nada() -> None:
    c = _caso()
    r = simular(c, d=0.5, replicas=50, dias=30)
    assert r["p"] == pytest.approx(c.p_verdadera)


def test_el_ruido_simetrico_acerca_la_probabilidad_a_un_medio() -> None:
    # La base del efecto de variabilidad: E[Λ(m + sZ)] baja hacia 1/2 al crecer s.
    for m in (0.4, 1.1, 1.8):
        serie = [gauss_logistica(m, s) for s in np.linspace(0.0, 6.0, 25)]
        assert serie[0] == pytest.approx(1 / (1 + np.exp(-m)))
        assert np.all(np.diff(serie) < 0)
        assert serie[-1] > 0.5


def test_vida_media() -> None:
    # Cae hasta −0,2 el día 4 y recupera 0,01 por día: la mitad (−0,1) el día 14.
    brecha = np.concatenate([np.linspace(0, -0.2, 5), np.linspace(-0.2, 0, 21)[1:]])
    assert vida_media(brecha) == pytest.approx(10.0)
    assert vida_media(np.zeros(10)) == 0.0
    assert vida_media(np.full(10, -0.2)) is None
