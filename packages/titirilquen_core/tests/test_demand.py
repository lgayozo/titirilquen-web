from __future__ import annotations

import numpy as np
import pytest

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, StratumBetas, StratumConfig, PhysicalPenalties
from titirilquen_core.demand.choice import probabilidades_logit, elegir_modo
from titirilquen_core.demand.utility import calcular_utilidades


def _make_demand_config() -> DemandConfig:
    penal = PhysicalPenalties(
        bici_10=-0.09, bici_20=-0.15, bici_30=-0.5,
        walk_5=-0.09, walk_15=-0.18, walk_25=-0.4,
    )
    betas = StratumBetas(
        asc_auto=1.5, asc_metro=-0.2, asc_bici=-0.9, asc_caminata=-0.5,
        b_tiempo_viaje=-0.055, b_costo=-0.00008,
        b_tiempo_espera=-0.05, b_tiempo_caminata=-0.15,
        penalizaciones_fisicas=penal,
    )
    s1 = StratumConfig(prob_teletrabajo=0.4, prob_auto=0.9, betas=betas)
    return DemandConfig(estratos={1: s1, 2: s1, 3: s1})


def test_sin_auto_no_se_elige_auto() -> None:
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    utils = calcular_utilidades(
        estrato=1, celda_origen=5, tiene_auto=False,
        ciudad=ciudad, config=cfg, tiempos_observados=None,
    )
    assert utils["Auto"].feasible is False
    probs = probabilidades_logit(utils)
    assert probs["Auto"] == 0.0


def test_caminata_infeasible_si_mayor_30_min() -> None:
    # Ciudad larga: caminata al CBD > 30 min
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=20)
    cfg = _make_demand_config()
    utils = calcular_utilidades(
        estrato=1, celda_origen=0, tiene_auto=True,
        ciudad=ciudad, config=cfg, tiempos_observados=None,
    )
    assert utils["Caminata"].feasible is False


def test_probs_suman_uno() -> None:
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    utils = calcular_utilidades(
        estrato=2, celda_origen=5, tiene_auto=True,
        ciudad=ciudad, config=cfg, tiempos_observados=None,
    )
    probs = probabilidades_logit(utils)
    assert abs(sum(probs.values()) - 1.0) < 1e-9


def test_eleccion_reproducible_con_seed() -> None:
    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    utils = calcular_utilidades(
        estrato=2, celda_origen=5, tiene_auto=True,
        ciudad=ciudad, config=cfg, tiempos_observados=None,
    )
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    assert elegir_modo(utils, rng=rng1) == elegir_modo(utils, rng=rng2)


def test_penalizacion_bici_escalonada() -> None:
    """D-02: la penalización es aditiva escalonada, no multiplicativa."""
    from titirilquen_core.demand.utility import TiemposObservados

    ciudad = CiudadLineal(n_celdas=21, largo_total_km=10)
    cfg = _make_demand_config()
    penal = cfg.estratos[1].betas.penalizaciones_fisicas

    # Sin penalización (t < 10)
    t0 = TiemposObservados(auto_total=5, bici_total=5, tren_acceso=1, tren_espera=1, tren_viaje=5)
    u0 = calcular_utilidades(
        estrato=1, celda_origen=5, tiene_auto=True,
        ciudad=ciudad, config=cfg, tiempos_observados=t0,
    )
    # Con penalización > 30
    t35 = TiemposObservados(auto_total=5, bici_total=35, tren_acceso=1, tren_espera=1, tren_viaje=5)
    u35 = calcular_utilidades(
        estrato=1, celda_origen=5, tiene_auto=True,
        ciudad=ciudad, config=cfg, tiempos_observados=t35,
    )
    esperado = penal.bici_10 + penal.bici_20 + penal.bici_30
    assert abs(u35["Bici"].v_penalizaciones - esperado) < 1e-9
    assert abs(u0["Bici"].v_penalizaciones - 0.0) < 1e-9
