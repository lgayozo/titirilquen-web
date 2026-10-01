"""Las propiedades del IBL que tienen respuesta conocida."""

from __future__ import annotations

import numpy as np
import pytest

from ibl import pesos_ibl, tiempo_percibido


def _historia() -> tuple[np.ndarray, np.ndarray]:
    """Una persona, 4 días, 2 modos. Modo 0 elegido en t' = 0, 1, 3; modo 1 sólo en t' = 0 (prior) y 2."""
    x = np.array([[[10.0, 20.0], [16.0, 0.0], [0.0, 26.0], [13.0, 0.0]]])
    a = np.array([[[True, True], [True, False], [False, True], [True, False]]])
    return x, a


def test_d_cero_es_el_promedio_simple() -> None:
    x, a = _historia()
    b = tiempo_percibido(x, a, t=4, d=0.0)
    assert b[0, 0] == pytest.approx((10 + 16 + 13) / 3)
    assert b[0, 1] == pytest.approx((20 + 26) / 2)


def test_una_sola_experiencia_se_devuelve_exacta() -> None:
    x, a = _historia()
    b = tiempo_percibido(x, a, t=1, d=1.0)  # sólo el prior
    assert b[0].tolist() == [10.0, 20.0]


def test_los_pesos_suman_uno_y_solo_pesan_lo_elegido() -> None:
    _, a = _historia()
    w = pesos_ibl(a, t=4, d=0.7)
    assert w.sum(axis=1) == pytest.approx(np.ones((1, 2)))
    assert np.all(w[~a[:, :4, :]] == 0.0)


def test_el_decaimiento_favorece_lo_reciente() -> None:
    x, a = _historia()
    w = pesos_ibl(a, t=4, d=1.0)
    # modo 0: días 0, 1, 3 con antigüedad 4, 3, 1 → pesos ∝ 1/4, 1/3, 1
    esperado = np.array([1 / 4, 1 / 3, 1.0])
    assert w[0, [0, 1, 3], 0] == pytest.approx(esperado / esperado.sum())
    # y por lo tanto la percepción se acerca a la última experiencia
    b = tiempo_percibido(x, a, t=4, d=1.0)
    assert abs(b[0, 0] - 13.0) < abs(b[0, 0] - 10.0)


def test_un_modo_nunca_elegido_da_peso_cero_no_nan() -> None:
    a = np.array([[[True, False], [True, False]]])
    w = pesos_ibl(a, t=2, d=0.5)
    assert np.all(np.isfinite(w))
    assert w[0, :, 1].sum() == 0.0


def test_t_cero_no_tiene_pasado() -> None:
    _, a = _historia()
    with pytest.raises(ValueError):
        pesos_ibl(a, t=0, d=0.5)
