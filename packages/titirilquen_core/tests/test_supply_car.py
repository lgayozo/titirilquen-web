from __future__ import annotations

import numpy as np

from titirilquen_core.supply.car import _factor_ancho, demora_auto_tramo


def test_factor_ancho() -> None:
    assert _factor_ancho(3.5) == 1.0
    assert _factor_ancho(3.2) == 0.9
    assert _factor_ancho(2.9) == 0.75


def test_mas_pistas_baja_congestion() -> None:
    N = 21
    demanda = np.full(N, 200.0)
    kwargs = dict(
        ubicacion_centro_km=10.0,
        demanda=demanda,
        v_max_kmh=31,
        ancho_pista_m=3.5,
        largo_vehiculo_m=5,
        gap_m=2,
        L_ciudad_km=20.0,
        alpha_bpr=0.8,
        beta_bpr=2.0,
    )
    r1 = demora_auto_tramo(num_pistas=1, **kwargs)
    r3 = demora_auto_tramo(num_pistas=3, **kwargs)
    assert r3.t_usuarios_min.sum() < r1.t_usuarios_min.sum()
    assert r3.capacidad_direccion > r1.capacidad_direccion


def test_capacidad_escala_con_pistas() -> None:
    kwargs = dict(
        ubicacion_centro_km=10.0,
        demanda=np.zeros(21),
        v_max_kmh=31,
        ancho_pista_m=3.5,
        largo_vehiculo_m=5,
        gap_m=2,
        L_ciudad_km=20.0,
        alpha_bpr=0.8,
        beta_bpr=2.0,
    )
    r1 = demora_auto_tramo(num_pistas=1, **kwargs)
    r2 = demora_auto_tramo(num_pistas=2, **kwargs)
    assert abs(r2.capacidad_direccion - 2 * r1.capacidad_direccion) < 1e-6
