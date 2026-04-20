"""Pruebas de la oferta de bicicletas.

Las fórmulas se portaron verbatim desde el repo original; estas pruebas fijan
el comportamiento para detectar regresiones si alguien las toca.
"""

from __future__ import annotations

import numpy as np

from titirilquen_core.supply.bike import _velocidad_con_pendiente, demora_bici_tramo


def test_velocidad_sin_pendiente_es_la_base() -> None:
    assert _velocidad_con_pendiente(14, 0) == 14


def test_velocidad_sube_en_bajada() -> None:
    # pendiente negativa = bajada => factor > 1
    assert _velocidad_con_pendiente(14, -5) > 14


def test_velocidad_baja_en_subida() -> None:
    assert _velocidad_con_pendiente(14, 5) < 14


def test_velocidad_acotada_entre_5_y_45() -> None:
    assert _velocidad_con_pendiente(200, 0) == 45
    assert _velocidad_con_pendiente(2, 0) == 5


def test_demanda_cero_produce_tiempos_flujo_libre_no_negativos() -> None:
    N = 11
    demanda = np.zeros(N)
    res = demora_bici_tramo(
        ubicacion_centro_km=5.0,
        capacidad=800,
        demanda=demanda,
        v_media=14,
        L_ciudad_km=10.0,
        alpha=0.5,
        beta=2.0,
    )
    assert res.flujos_bici_por_hora.sum() == 0
    assert np.all(res.t_usuarios_min >= 0)


def test_centro_tiene_tiempo_cero() -> None:
    N = 11
    demanda = np.full(N, 100.0)
    res = demora_bici_tramo(
        ubicacion_centro_km=5.0,
        capacidad=800,
        demanda=demanda,
        v_media=14,
        L_ciudad_km=10.0,
        alpha=0.5,
        beta=2.0,
    )
    idx_centro = int((5.0 / 10.0) * N)
    assert res.t_usuarios_min[idx_centro] == 0
    assert res.flujos_bici_por_hora[idx_centro] == 0


def test_demora_creciente_con_distancia() -> None:
    N = 21
    demanda = np.full(N, 50.0)
    res = demora_bici_tramo(
        ubicacion_centro_km=10.0,
        capacidad=800,
        demanda=demanda,
        v_media=14,
        L_ciudad_km=20.0,
        alpha=0.5,
        beta=2.0,
    )
    idx_centro = int((10.0 / 20.0) * N)
    # Celda contigua al centro debe tener menos demora que el extremo
    assert res.t_usuarios_min[0] > res.t_usuarios_min[idx_centro - 1]
    assert res.t_usuarios_min[-1] > res.t_usuarios_min[idx_centro + 1]
