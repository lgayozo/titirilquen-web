"""Pruebas de la oferta de metro — recorte de la frecuencia endogena.

La frecuencia es `f_op = clip(carga_maxima / capacidad_tren, frec_min, frec_max)`.
El resultado expone ADEMAS la teorica sin recortar, y de esas dos cifras depende
el indicador de la UI que dice si un tope esta mordiendo (AT-08/AT-09): sin la
teorica el usuario no distingue «subi el tope y no paso nada» de «el tope no
estaba activo». Estos tests fijan las tres ramas del indicador.
"""

from __future__ import annotations

import numpy as np

from titirilquen_core.supply.train import oferta_tren

BASE = {
    "L_ciudad_km": 20.0,
    "x_centro_km": 10.0,
    "v_tren_kmh": 35.0,
    "num_estaciones": 10,
    "v_caminata_kmh": 4.8,
    "anden_alpha": 0.5,
    "anden_beta": 4.0,
}


def _correr(demanda_por_celda: float, capacidad_tren: int, frec_min: float, frec_max: float):
    demanda = np.full(101, demanda_por_celda, dtype=float)
    return oferta_tren(
        demanda=demanda, capacidad_tren=capacidad_tren, frec_min=frec_min, frec_max=frec_max, **BASE
    )


def test_frecuencia_teorica_es_carga_maxima_sobre_capacidad() -> None:
    """La teorica es exactamente el cociente, sin recortar. Es la definicion de
    la que depende el indicador; si cambia, el hint de la UI miente."""
    r = _correr(demanda_por_celda=10.0, capacidad_tren=300, frec_min=1.0, frec_max=1000.0)
    esperado = float(np.max(r.carga_por_tramo)) / 300
    assert r.frecuencia_teorica == esperado
    # Con topes holgados no hay recorte: operativa == teorica.
    assert r.frecuencia_operativa == r.frecuencia_teorica


def test_demanda_alta_topa_por_frec_max() -> None:
    # Con 101 celdas la carga maxima del tramo critico es ~45x la demanda por
    # celda, asi que d=250 => f_teorica ~37.5, sobre el tope de 30.
    r = _correr(demanda_por_celda=250.0, capacidad_tren=300, frec_min=6.0, frec_max=30.0)
    assert r.frecuencia_teorica > 30.0
    assert r.frecuencia_operativa == 30.0


def test_demanda_baja_topa_por_frec_min() -> None:
    r = _correr(demanda_por_celda=0.5, capacidad_tren=300, frec_min=6.0, frec_max=30.0)
    assert r.frecuencia_teorica < 6.0
    assert r.frecuencia_operativa == 6.0


def test_demanda_intermedia_no_topa_por_ningun_extremo() -> None:
    """Rama «libre»: la demanda fija la frecuencia y mover los topes no hace
    nada hasta cruzarla."""
    # d=100 => f_teorica ~15, dentro de [6, 30].
    r = _correr(demanda_por_celda=100.0, capacidad_tren=300, frec_min=6.0, frec_max=30.0)
    assert 6.0 < r.frecuencia_teorica < 30.0
    assert r.frecuencia_operativa == r.frecuencia_teorica


def test_subir_capacidad_del_tren_baja_la_frecuencia() -> None:
    """AT-06: `capacidad_tren` es el DIVISOR de la frecuencia, no una
    restriccion de confort. Trenes mas grandes => menos frecuencia => mas
    espera. Se fija para que el signo invertido no se pierda de vista."""
    chico = _correr(demanda_por_celda=10.0, capacidad_tren=100, frec_min=1.0, frec_max=1000.0)
    grande = _correr(demanda_por_celda=10.0, capacidad_tren=1000, frec_min=1.0, frec_max=1000.0)
    assert grande.frecuencia_teorica < chico.frecuencia_teorica
