"""Emisiones de CO₂ — metro por tren-km (D-29)."""

from __future__ import annotations

import numpy as np

from titirilquen_core.emissions import calcular_emisiones


def _run(flujos: np.ndarray, frecuencia: float) -> object:
    return calcular_emisiones(
        flujos_auto=flujos,
        frecuencia_metro=frecuencia,
        estaciones_km=np.array([0.0, 10.0, 20.0]),
        capacidad_auto=1000.0,
        alpha_bpr=0.8,
        beta_bpr=2.0,
        v_libre_kmh=31.0,
        largo_ciudad_km=20.0,
        n_celdas=101,
        factor_emision_metro_tren_km=2.5,
    )


def test_metro_emite_por_tren_km() -> None:
    """Emisión del metro = factor · f_op · span · 2 (ida y vuelta), exacta."""
    em = _run(np.zeros(101), frecuencia=6.0)
    esperado = 2.5 * 6.0 * 20.0 * 2.0  # 600 kg/h
    assert abs(em.metro_kg_hora - esperado) < 1e-9


def test_metro_independiente_de_la_carga_de_pasajeros() -> None:
    """D-29: a frecuencia fija, más autos/pasajeros NO cambian la emisión del
    metro (es costo fijo del servicio); solo la frecuencia la mueve."""
    em_vacio = _run(np.zeros(101), frecuencia=6.0)
    em_cargado = _run(np.full(101, 500.0), frecuencia=6.0)
    assert abs(em_vacio.metro_kg_hora - em_cargado.metro_kg_hora) < 1e-9
    # ...pero la frecuencia sí (Mohring de emisiones): el doble de servicio
    # emite el doble.
    em_doble = _run(np.zeros(101), frecuencia=12.0)
    assert abs(em_doble.metro_kg_hora - 2 * em_vacio.metro_kg_hora) < 1e-9


def test_perfil_espacial_suma_el_total() -> None:
    em = _run(np.full(101, 200.0), frecuencia=8.0)
    assert abs(float(em.perfil_espacial_kg.sum()) - em.total_kg_hora) < 1e-6
    assert em.total_kg_hora == em.auto_kg_hora + em.metro_kg_hora


def test_sin_servicio_sin_emisiones_de_metro() -> None:
    em = _run(np.zeros(101), frecuencia=0.0)
    assert em.metro_kg_hora == 0.0
