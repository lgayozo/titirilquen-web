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


def test_capacidad_explicita_desacopla_velocidad() -> None:
    """S-04: con `capacidad_pista` explícita, subir v_max cambia el free-flow
    pero NO la capacidad (en Greenshields C ∝ v_l y la velocidad nunca puede
    empeorar la congestión)."""
    kwargs = dict(
        ubicacion_centro_km=10.0,
        demanda=np.full(21, 200.0),
        ancho_pista_m=3.5,
        largo_vehiculo_m=5,
        gap_m=2,
        L_ciudad_km=20.0,
        num_pistas=2,
        alpha_bpr=0.8,
        beta_bpr=2.0,
        capacidad_pista=900.0,
    )
    lento = demora_auto_tramo(v_max_kmh=31, **kwargs)
    rapido = demora_auto_tramo(v_max_kmh=62, **kwargs)
    # Capacidad fija e independiente de la velocidad.
    assert lento.capacidad_direccion == rapido.capacidad_direccion == 1800.0
    # El free-flow sí mejora con la velocidad.
    assert rapido.t_usuarios_min.sum() < lento.t_usuarios_min.sum()
    # Y None conserva Greenshields: C ∝ v_l.
    g1 = demora_auto_tramo(v_max_kmh=31, **{**kwargs, "capacidad_pista": None})
    g2 = demora_auto_tramo(v_max_kmh=62, **{**kwargs, "capacidad_pista": None})
    assert abs(g2.capacidad_direccion - 2 * g1.capacidad_direccion) < 1e-6
