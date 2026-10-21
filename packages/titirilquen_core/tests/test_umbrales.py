"""Las dos especificaciones de los umbrales físicos (`globales.umbrales`).

«escalones» es la simplificada: penalizaciones escalonadas, cortes duros de
factibilidad y metro infactible donde la estación más cercana es la del CBD
(D-69). «suaves» cambia cada discontinuidad por su versión continua. Estos tests
fijan lo que distingue a una de la otra; los repartos de cada una están en
`test_linea_base.py`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig
from titirilquen_core.constantes import A_DOMINANCIA_METRO, OMEGA_CORTE_SUAVE
from titirilquen_core.demand.utility import (
    TiemposObservados,
    _escalones,
    _rampa,
    calcular_utilidades,
)
from titirilquen_core.presets import DEFAULT_STRATA
from titirilquen_core.supply.train import oferta_tren

CIUDAD = CiudadLineal(n_celdas=1001, largo_total_km=20)


def _config(umbrales: str) -> DemandConfig:
    return DemandConfig.model_validate(
        {"estratos": DEFAULT_STRATA, "globales": {"umbrales": umbrales}}
    )


def _utilidades(config: DemandConfig, celda: int, **tiempos: float):
    dist = abs(CIUDAD.cbd_index - celda) * CIUDAD.ancho_celda_km
    gl = config.globales
    base = {
        "auto_total": dist / gl.v_auto * 60,
        "bici_total": dist / gl.v_bici * 60,
        "bici_libre": dist / gl.v_bici * 60,
        "tren_acceso": 5.0,
        "tren_espera": 3.0,
        "tren_viaje": dist / gl.v_metro * 60 + 1.0,
    }
    return calcular_utilidades(
        estrato=1,
        celda_origen=celda,
        tiene_auto=True,
        ciudad=CIUDAD,
        config=config,
        tiempos_observados=TiemposObservados(**(base | tiempos)),
    )


def test_la_rampa_pasa_por_el_centro_de_cada_escalon() -> None:
    """Conserva el nivel medio de cada tramo: en 10 y 20 min de caminata
    (centros de los tramos 5-15 y 15-25) vale lo mismo que el escalón, y es
    monótona no creciente porque las penalizaciones son negativas."""
    umbrales, pen = (5, 15, 25), (-0.1, -0.2, -0.3)
    assert _rampa(0, umbrales, pen) == 0.0
    for t in (10, 20):
        assert _rampa(t, umbrales, pen) == pytest.approx(_escalones(t, umbrales, pen))
    valores = [_rampa(t, umbrales, pen) for t in np.linspace(0, 60, 241)]
    assert max(np.diff(valores)) <= 1e-12


def test_escalones_saca_la_caminata_del_conjunto_y_suaves_no() -> None:
    """Sobre el corte de 30 min: infactible con escalones; con suaves sigue en el
    conjunto, castigada por el corte CMNL (−ln 2 justo en el corte)."""
    lejos = CIUDAD.cbd_index + 200  # 4 km = 50 min a pie
    assert not _utilidades(_config("escalones"), lejos)["Caminata"].feasible
    assert _utilidades(_config("suaves"), lejos)["Caminata"].feasible


@pytest.mark.parametrize("modo", ["Caminata", "Bici"])
def test_con_suaves_la_utilidad_es_continua_en_la_distancia(modo: str) -> None:
    """Cota de Lipschitz celda a celda: ningún salto mayor que lo que permiten
    las pendientes del tiempo, de la rampa y del corte. Con escalones hay saltos
    (o el modo desaparece), y esa es toda la diferencia que se busca."""
    config = _config("suaves")
    gl = config.globales
    b = config.estratos[1].betas
    v = gl.v_caminata if modo == "Caminata" else gl.v_bici
    dt = CIUDAD.ancho_celda_km / v * 60
    pendiente = abs(b.b_tiempo_caminata if modo == "Caminata" else b.b_tiempo_viaje)
    pendiente += 0.1 + OMEGA_CORTE_SUAVE  # rampa (|Δp|/10 min ≤ 0,1) + CMNL
    vs = [_utilidades(config, c)[modo].valor for c in range(CIUDAD.cbd_index, CIUDAD.n_celdas)]
    assert max(abs(np.diff(vs))) <= pendiente * dt


def test_dominancia_suave_del_metro() -> None:
    """En la frontera GT_metro = a·GT_caminata la penalización es −ln 2; con un
    metro mucho mejor que caminar es despreciable; con escalones no existe."""
    celda = CIUDAD.cbd_index + 50  # 1 km
    config = _config("suaves")
    b = config.estratos[1].betas
    t_cam = CIUDAD.ancho_celda_km * 50 / config.globales.v_caminata * 60
    frontera = A_DOMINANCIA_METRO * b.b_tiempo_caminata / b.b_tiempo_viaje * t_cam
    metro = _utilidades(config, celda, tren_acceso=0, tren_espera=0, tren_viaje=frontera)["Metro"]
    assert metro.v_penalizaciones == pytest.approx(-math.log(2))
    lejos = _utilidades(config, CIUDAD.cbd_index + 400)["Metro"]
    assert -0.01 < lejos.v_penalizaciones <= 0
    assert _utilidades(_config("escalones"), celda)["Metro"].v_penalizaciones == 0.0


@pytest.mark.parametrize("excluir", [False, True])
def test_la_estacion_del_cbd_solo_sirve_a_su_celda_si_se_excluye(excluir: bool) -> None:
    """Sin exclusión (escalones), las celdas a menos de media interestación del
    CBD acceden por la estación del CBD y su tramo en tren es 0 (D-69). Con
    exclusión (suaves), sólo la celda del CBD tiene tramo nulo."""
    r = oferta_tren(
        demanda=np.zeros(101),
        L_ciudad_km=20.0,
        x_centro_km=10.0,
        v_tren_kmh=35.0,
        capacidad_tren=1000,
        num_estaciones=10,
        v_caminata_kmh=4.8,
        frec_min=4.0,
        frec_max=30.0,
        excluir_estacion_cbd=excluir,
    )
    nulos = int(np.sum(r.t_viaje_min <= 0))
    assert nulos == 1 if excluir else nulos > 1
