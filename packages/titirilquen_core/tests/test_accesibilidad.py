"""La accesibilidad de la puja es el logsum mensual de transporte, por estrato (D-34).

Tres cosas que tienen que ser ciertas para que el peso 1 sobre T signifique algo:
que el logsum sea el del logit modal (no otra cantidad), que `T` crezca con la
distancia (es un costo), y que por estrato NO invierta Alonso — que es lo que
D-22 temía y la razón por la que hasta sep-2026 la accesibilidad era común.
"""

from __future__ import annotations

import numpy as np

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.constantes import VIAJES_MES
from titirilquen_core.demand.choice import probabilidades_logit
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.land_use import LandUseCity, LandUseConfig
from titirilquen_core.land_use.accesibilidad import (
    T_desde_logsum,
    T_flujo_libre,
    lambda_desde_demanda,
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
    T = T_flujo_libre(_demanda(), L, CBD, DX, supply=SupplyConfig())
    assert T.shape == (3, L)
    assert np.all(np.isfinite(T))
    d = np.abs(np.arange(L) - CBD)
    fuera = np.arange(L) != CBD  # la celda del CBD no tiene vivienda ni entra a la puja
    for h in range(3):
        # Más lejos ⇒ más costo, como TENDENCIA: con la red vacía configurada
        # (D-42) la accesibilidad no es monótona celda a celda —cerca de cada
        # estación el acceso al metro se acorta—, pero sí sube con la distancia
        # en el grueso de la ciudad. Se exige correlación alta y que el borde
        # cueste más que el centro.
        corr = np.corrcoef(d[fuera], T[h, fuera])[0, 1]
        assert corr > 0.9, f"estrato {h}: corr(T, distancia) = {corr:.3f}"
        assert T[h, CBD + 1] < T[h, -1] and T[h, CBD - 1] < T[h, 0]
    # escala: VIAJES_MES veces el logsum por viaje sobre la red VACÍA, con
    # signo cambiado (D-42: no el flujo libre de 10 min de acceso fijos).
    from titirilquen_core.land_use.accesibilidad import tiempos_red_vacia

    ciudad = CiudadLineal(n_celdas=L, largo_total_km=LARGO)
    sim = SimulationConfig(
        city=CityConfig(n_celdas=L, largo_ciudad_km=LARGO), supply=SupplyConfig(), demand=_demanda()
    )
    ls = logsum_por_celda(_demanda(), ciudad, tiempos_red_vacia(sim, ciudad))
    p_tele = np.array([_demanda().estratos[e].prob_teletrabajo for e in (1, 2, 3)])
    np.testing.assert_allclose(T, -VIAJES_MES * (1 - p_tele)[:, None] * ls)
    assert T_desde_logsum(ls, _demanda()).shape == (3, L)


def test_el_teletrabajo_aplana_la_accesibilidad() -> None:
    """D11: `T_h` cobra los viajes ESPERADOS, `VIAJES_MES·(1 − p_tele,h)`. Con
    el doble de teletrabajo el gradiente de cada estrato se escala por
    `(1 − 2p)/(1 − p)`, y si todos teletrabajan la ubicación no cuesta nada.
    Los defaults no traen teletrabajo (oct-2026): las tasas son ilustrativas."""
    base = _demanda()
    for e, p in zip(base.estratos.values(), (0.40, 0.20, 0.05), strict=True):
        e.prob_teletrabajo = p
    doble = base.model_copy(deep=True)
    doble.globales.teletrabajo_factor = 2.0
    todos = base.model_copy(deep=True)
    todos.globales.teletrabajo_factor = 5.0
    for e in todos.estratos.values():
        e.prob_teletrabajo = 1.0
    T1, T2, T5 = (T_flujo_libre(d, L, CBD, DX, supply=SupplyConfig()) for d in (base, doble, todos))
    for h, e in enumerate((1, 2, 3)):
        p = base.estratos[e].prob_teletrabajo
        assert 0 < p < 0.5, "la prueba necesita teletrabajo en todos los estratos"
        np.testing.assert_allclose(T2[h], T1[h] * (1 - 2 * p) / (1 - p))
    np.testing.assert_allclose(T5, 0.0, atol=1e-12)


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
    # Sin teletrabajo (D11), explícito aunque desde oct-2026 sea el default: con
    # él, un estrato que teletrabaja más paga menos viajes y su gradiente se
    # aplana; ese es otro mecanismo, real, que no es el que este guard vigila.
    dem = _demanda().model_copy(deep=True)
    dem.globales.teletrabajo_factor = 0.0
    city = LandUseCity.build(
        L=L,
        CBD=CBD,
        cfg=cfg,
        ancho_celda_km=DX,
        T=T_flujo_libre(dem, L, CBD, DX, supply=SupplyConfig()),
        lambda_h=lambda_desde_demanda(dem),
        rng=np.random.default_rng(42),
    )
    assert city.result is not None and city.result.converged
    d = _distancias(city)
    assert d[0] < d[1] < d[2], (
        f"Alonso invertido o revuelto: d = {d.round(2)} km (alto, medio, bajo)"
    )


def test_la_oferta_de_metro_mueve_la_accesibilidad_standalone() -> None:
    """D-42: la accesibilidad es la de la red vacía CONFIGURADA. Cambiar las
    estaciones del metro tiene que cambiar `T`; con los 10 min de acceso fijos
    de antes no lo hacía."""
    dem = _demanda()
    base = T_flujo_libre(dem, L, CBD, DX, supply=SupplyConfig())
    pocas = SupplyConfig()
    pocas.train.num_estaciones = 3
    otra = T_flujo_libre(dem, L, CBD, DX, supply=pocas)
    assert np.max(np.abs(otra - base)) > 1.0, "las estaciones no movieron la accesibilidad"


def test_la_pendiente_mueve_la_accesibilidad_y_la_localizacion() -> None:
    """La pendiente del escenario llega a la `T` del suelo (standalone y vuelta 0
    del acoplado) y a la localización «equilibrio» de Transporte. Hasta oct-2026
    no llegaba: la accesibilidad salía siempre con terreno plano."""
    from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo

    dem = _demanda()
    plano = T_flujo_libre(dem, L, CBD, DX, supply=SupplyConfig())
    cuesta = T_flujo_libre(dem, L, CBD, DX, supply=SupplyConfig(), pendiente_porcentaje=8.0)
    assert np.max(np.abs(cuesta - plano)) > 1.0, "la pendiente no movió T"

    def ubicacion(pendiente: float) -> list[tuple[int, int]]:
        sim = SimulationConfig(
            city=CityConfig(n_celdas=51, largo_ciudad_km=LARGO, pendiente_porcentaje=pendiente),
            demand=dem,
            max_iter=1,
            seed=1,
            assignment="expected",
        )
        trace = ConvergenceTrace()
        lu = LandUseConfig(H_por_estrato=(720, 1800, 1080))
        for _ in iter_msa_desde_suelo(sim, lu, trace, localizacion="equilibrio"):
            pass
        return sorted((a.estrato, a.celda_origen) for a in trace.agentes)

    # La ubicación de los hogares sale sólo del suelo (la T de red vacía), no
    # del reparto: si difiere, la pendiente llegó a la localización.
    assert ubicacion(0.0) != ubicacion(8.0), "la pendiente no movió la localización"
