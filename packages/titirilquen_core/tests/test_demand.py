from __future__ import annotations

import pytest

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, PhysicalPenalties, StratumBetas, StratumConfig
from titirilquen_core.demand.choice import probabilidades_logit
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades


def _make_demand_config() -> DemandConfig:
    penal = PhysicalPenalties(
        bici_10=-0.09,
        bici_20=-0.15,
        bici_30=-0.5,
        walk_5=-0.09,
        walk_15=-0.18,
        walk_25=-0.4,
    )
    betas = StratumBetas(
        asc_auto=1.5,
        asc_metro=-0.2,
        asc_bici=-0.9,
        asc_caminata=-0.5,
        b_tiempo_viaje=-0.055,
        b_costo=-0.00008,
        b_tiempo_espera=-0.05,
        b_tiempo_acceso=-0.15,
        b_tiempo_caminata=-0.15,
        penalizaciones_fisicas=penal,
    )
    s1 = StratumConfig(prob_teletrabajo=0.4, prob_auto=0.9, betas=betas)
    return DemandConfig(estratos={1: s1, 2: s1, 3: s1})


def test_sin_auto_no_se_elige_auto() -> None:
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    utils = calcular_utilidades(
        estrato=1,
        celda_origen=5,
        tiene_auto=False,
        ciudad=ciudad,
        config=cfg,
        tiempos_observados=None,
    )
    assert utils["Auto"].feasible is False
    probs = probabilidades_logit(utils)
    assert probs["Auto"] == 0.0


def test_caminata_infeasible_si_mayor_30_min() -> None:
    # Ciudad larga: caminata al CBD > 30 min
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=20)
    cfg = _make_demand_config()
    utils = calcular_utilidades(
        estrato=1,
        celda_origen=0,
        tiene_auto=True,
        ciudad=ciudad,
        config=cfg,
        tiempos_observados=None,
    )
    assert utils["Caminata"].feasible is False


def test_probs_suman_uno() -> None:
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    utils = calcular_utilidades(
        estrato=2,
        celda_origen=5,
        tiene_auto=True,
        ciudad=ciudad,
        config=cfg,
        tiempos_observados=None,
    )
    probs = probabilidades_logit(utils)
    assert abs(sum(probs.values()) - 1.0) < 1e-9


def test_penalizacion_bici_escalonada() -> None:
    """D-02: la penalización es aditiva escalonada, no multiplicativa."""
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    penal = cfg.estratos[1].betas.penalizaciones_fisicas

    # Sin penalización (t < 10)
    t0 = TiemposObservados(
        auto_total=5, bici_total=5, bici_libre=5, tren_acceso=1, tren_espera=1, tren_viaje=5
    )
    u0 = calcular_utilidades(
        estrato=1,
        celda_origen=5,
        tiene_auto=True,
        ciudad=ciudad,
        config=cfg,
        tiempos_observados=t0,
    )
    # Con penalización > 30
    t35 = TiemposObservados(
        auto_total=5, bici_total=35, bici_libre=35, tren_acceso=1, tren_espera=1, tren_viaje=5
    )
    u35 = calcular_utilidades(
        estrato=1,
        celda_origen=5,
        tiene_auto=True,
        ciudad=ciudad,
        config=cfg,
        tiempos_observados=t35,
    )
    esperado = penal.bici_10 + penal.bici_20 + penal.bici_30
    assert abs(u35["Bici"].v_penalizaciones - esperado) < 1e-9
    assert abs(u0["Bici"].v_penalizaciones - 0.0) < 1e-9


def test_los_escalones_de_la_bici_no_ven_la_congestion() -> None:
    """D9: escalones y corte se evalúan sobre el tiempo de red vacía. Con 25 min
    de esfuerzo físico, 12 min de congestión (37 en total) no agregan el escalón
    de 30 ni, con 44 → 56, sacan a la bici del conjunto: sólo pesan por b_tiempo."""
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    betas = cfg.estratos[1].betas
    kw = {"estrato": 1, "celda_origen": 5, "tiene_auto": True, "ciudad": ciudad, "config": cfg}

    def bici(libre: float, total: float):
        t = TiemposObservados(
            auto_total=5,
            bici_total=total,
            bici_libre=libre,
            tren_acceso=1,
            tren_espera=1,
            tren_viaje=5,
        )
        return calcular_utilidades(**kw, tiempos_observados=t)["Bici"]

    libre, congestionada = bici(25, 25), bici(25, 37)
    assert congestionada.v_penalizaciones == pytest.approx(libre.v_penalizaciones)
    assert congestionada.valor - libre.valor == pytest.approx(betas.b_tiempo_viaje * 12)
    assert bici(44, 56).feasible
    assert not bici(46, 46).feasible


def test_el_peaje_por_km_entra_al_costo_del_auto_y_a_nada_mas() -> None:
    """D7: el peaje suma `peaje_km · distancia` al dinero del auto, a mano.
    Celda 5 de 21 en 10 km: el CBD es la 10, así que la distancia es 5 celdas
    de 10/21 km."""
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    sin = _make_demand_config()
    con = sin.model_copy(update={"globales": sin.globales.model_copy(update={"peaje_km": 100.0})})
    kw = {"estrato": 1, "celda_origen": 5, "tiene_auto": True, "ciudad": ciudad}
    u0 = calcular_utilidades(config=sin, tiempos_observados=None, **kw)
    u1 = calcular_utilidades(config=con, tiempos_observados=None, **kw)
    dist_km = 5 * 10 / 21
    b_costo = sin.estratos[1].betas.b_costo
    assert u1["Auto"].v_costo - u0["Auto"].v_costo == pytest.approx(b_costo * 100.0 * dist_km)
    assert u1["Auto"].v_tiempo == u0["Auto"].v_tiempo
    for modo in ("Metro", "Bici", "Caminata"):
        assert u1[modo].valor == u0[modo].valor
