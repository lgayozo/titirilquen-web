"""El peaje de Pigou y la frecuencia de Mohring, contra sus propias definiciones."""

import numpy as np
import pytest

from titirilquen_core.constantes import FACTOR_CAPACIDAD_PRACTICA
from titirilquen_core.optimos import (
    costo_marginal_externo_auto_min,
    frecuencia_mohring_tph,
    peaje_pigou_clp_km,
)

BPR = {"capacidad_direccion": 4000.0, "v_libre_kmh": 30.0, "ancho_celda_km": 0.1}


def _tiempo_min(q: float, alpha: float, beta: float) -> float:
    c = FACTOR_CAPACIDAD_PRACTICA * BPR["capacidad_direccion"]
    t0 = BPR["ancho_celda_km"] / BPR["v_libre_kmh"] * 60
    return t0 * (1 + alpha * (q / c) ** beta)


@pytest.mark.parametrize("q", [500.0, 2000.0, 3200.0, 4500.0])
def test_el_costo_externo_es_q_por_la_derivada_del_tiempo(q: float) -> None:
    """`CMgE = q · dt/dq`, comprobado contra la derivada numérica de la BPR."""
    alpha, beta = 0.15, 4.0
    h = 1e-3
    derivada = (_tiempo_min(q + h, alpha, beta) - _tiempo_min(q - h, alpha, beta)) / (2 * h)
    cmge = costo_marginal_externo_auto_min(np.array([q]), alpha=alpha, beta=beta, **BPR)
    assert cmge[0] == pytest.approx(q * derivada, rel=1e-6)


def test_sin_flujo_no_hay_externalidad() -> None:
    cmge = costo_marginal_externo_auto_min(np.zeros(5), alpha=0.15, beta=4.0, **BPR)
    assert np.all(cmge == 0)


def test_el_costo_externo_crece_mas_que_el_flujo() -> None:
    """Con β = 4, el doble de flujo impone 16 veces más demora a los demás:
    por eso el peaje se concentra en los tramos cargados."""
    cmge = costo_marginal_externo_auto_min(np.array([1000.0, 2000.0]), alpha=0.15, beta=4.0, **BPR)
    assert cmge[1] == pytest.approx(16 * cmge[0])


def test_el_peaje_es_ese_tiempo_al_valor_del_tiempo() -> None:
    """Un minuto de demora externa en un tramo de 100 m, a 3.000 $/h, son
    50 $ por tramo: 500 $/km."""
    peaje = peaje_pigou_clp_km(np.array([1.0]), vot_clp_hora=3000.0, ancho_celda_km=0.1)
    assert peaje[0] == pytest.approx(500.0)


def test_la_frecuencia_de_mohring_minimiza_el_costo_total() -> None:
    """`f*` es el mínimo de `c·ℓ·f + Q·V_e/(2f)`: moverse a cualquier lado
    cuesta más."""
    q, v, c, km = 8000.0, 6676.0, 12000.0, 40.0
    f = frecuencia_mohring_tph(
        pasajeros_hora=q, valor_espera_clp_hora=v, costo_tren_km_clp=c, tren_km_por_vuelta=km
    )

    def total(x: float) -> float:
        return c * km * x + q * v / (2 * x)

    assert f == pytest.approx(np.sqrt(q * v / (2 * c * km)))
    assert total(f) < total(f * 0.9)
    assert total(f) < total(f * 1.1)


def test_la_frecuencia_crece_con_la_raiz_de_la_demanda() -> None:
    base = {
        "valor_espera_clp_hora": 6676.0,
        "costo_tren_km_clp": 12000.0,
        "tren_km_por_vuelta": 40.0,
    }
    f1 = frecuencia_mohring_tph(pasajeros_hora=5000.0, **base)
    f4 = frecuencia_mohring_tph(pasajeros_hora=20000.0, **base)
    assert f4 == pytest.approx(2 * f1)


def test_sin_costo_de_operacion_no_hay_optimo() -> None:
    assert (
        frecuencia_mohring_tph(
            pasajeros_hora=5000.0,
            valor_espera_clp_hora=6676.0,
            costo_tren_km_clp=0.0,
            tren_km_por_vuelta=40.0,
        )
        == 0.0
    )
