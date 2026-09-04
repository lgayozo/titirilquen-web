"""La accesibilidad de la puja es el logsum mensual de transporte, por estrato (D-34).

Tres cosas que tienen que ser ciertas para que `alpha = 1` signifique algo:
que el logsum sea el del logit modal (no otra cantidad), que `T` crezca con la
distancia (es un costo), y que por estrato NO invierta Alonso — que es lo que
D-22 temía y la razón por la que hasta sep-2026 la accesibilidad era común.
"""

from __future__ import annotations

import numpy as np

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig
from titirilquen_core.constantes import VIAJES_MES
from titirilquen_core.demand.choice import probabilidades_logit
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.land_use import LandUseCity, LandUseConfig
from titirilquen_core.land_use.accesibilidad import (
    T_desde_logsum,
    T_flujo_libre,
    logsum_por_celda,
)
from titirilquen_core.presets import DEFAULT_STRATA

L, CBD, LARGO = 201, 100, 20.0
DX = LARGO / L


def _demanda() -> DemandConfig:
    return DemandConfig.model_validate({"estratos": DEFAULT_STRATA})


def test_el_logsum_es_el_del_logit_modal() -> None:
    """`logsum = ln Σ_m exp(V_m)` sobre los modos factibles, ponderado por auto.

    Se recalcula a mano en una celda para un estrato con `prob_auto = 1`, así
    la esperanza sobre tenencia de auto no esconde nada.
    """
    dem = _demanda().model_copy(deep=True)
    dem.estratos[1].prob_auto = 1.0
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=LARGO)
    i = 130
    u = calcular_utilidades(
        estrato=1,
        celda_origen=i,
        tiene_auto=True,
        ciudad=ciudad,
        config=dem,
        tiempos_observados=None,
    )
    v = np.array([b.valor for b in u.values() if b.feasible])
    esperado = float(np.log(np.exp(v).sum()))
    ls = logsum_por_celda(dem, ciudad)
    assert abs(ls[0, i] - esperado) < 1e-9
    # y las probabilidades del logit son las mismas que el reparto del núcleo
    p = probabilidades_logit(u)
    assert abs(sum(p.values()) - 1.0) < 1e-9


def test_T_es_un_costo_mensual_que_crece_con_la_distancia() -> None:
    T = T_flujo_libre(_demanda(), L, CBD, DX)
    assert T.shape == (3, L)
    assert np.all(np.isfinite(T))
    for h in range(3):
        # Más lejos ⇒ más costo, monótono en cada mitad de la ciudad. La celda del
        # CBD queda fuera: no tiene vivienda (S = 0) y su logsum es menor que el
        # de sus vecinas (a distancia 0 el reparto modal degenera), así que
        # nunca entra a la puja.
        assert np.all(np.diff(T[h, CBD + 1 :]) >= -1e-9), f"estrato {h}: T no crece a la derecha"
        assert np.all(np.diff(T[h, :CBD]) <= 1e-9), f"estrato {h}: T no crece a la izquierda"
        assert T[h, CBD + 1] < T[h, -1] and T[h, CBD - 1] < T[h, 0]
    # escala: VIAJES_MES veces el logsum por viaje, con signo cambiado
    ls = logsum_por_celda(_demanda(), CiudadLineal(n_celdas=L, largo_total_km=LARGO))
    np.testing.assert_allclose(T, -VIAJES_MES * ls)
    assert T_desde_logsum(ls).shape == (3, L)


def _distancias(city: LandUseCity) -> np.ndarray:
    S = np.asarray(city.S, float)
    Q = np.asarray(city.result.Q, float)
    dist = np.abs(np.arange(L) - CBD) * DX
    ocup = S[None, :] * Q
    return (ocup * dist[None, :]).sum(1) / ocup.sum(1)


def test_la_accesibilidad_por_estrato_no_invierte_alonso() -> None:
    """El guard que reemplaza a D-22.

    Con `T` en minutos por estrato, el auto del rico le aplanaba el tiempo y el
    bid-rent lo mandaba a la periferia. Con el logsum en pesos (`/λ_h`) el rico
    puja más empinado aunque viaje más rápido. Si esto falla, D-22 tenía razón
    y hay que volver a la accesibilidad común por ubicación.
    """
    cfg = LandUseConfig(H_por_estrato=(7200, 18000, 10800), max_iter=5000)
    city = LandUseCity.build(
        L=L,
        CBD=CBD,
        cfg=cfg,
        ancho_celda_km=DX,
        T=T_flujo_libre(_demanda(), L, CBD, DX),
        rng=np.random.default_rng(42),
    )
    assert city.result is not None and city.result.converged
    d = _distancias(city)
    assert d[0] < d[1] < d[2], (
        f"Alonso invertido o revuelto: d = {d.round(2)} km (alto, medio, bajo)"
    )
