"""Accesibilidad para la puja por suelo: el logsum de transporte, mensual, por estrato.

Un hogar tiene UNA función de utilidad. El que elige modo en `demand/` es el
mismo que puja por una parcela en `land_use/`, así que lo que la parcela le vale
en accesibilidad es lo que el viaje desde ahí le vale a él: la utilidad esperada
del logit modal, `logsum_h(i) = ln Σ_m exp(V_hm(i))`, en utiles de transporte.
Es el ancla que traía el original —`construir_T_desde_csv` cargaba
`LogSuma_Utilidad` por (estrato, celda) y llamaba `actualizar(T, alpha=[1,1,1])`—
y que nunca llegó a ejecutarse (D-34).

    T_h(i) = −VIAJES_MES · logsum_h(i)          [utiles de transporte / mes]

El signo lo vuelve costo (crece con la distancia) y `VIAJES_MES` lo pone en la
misma escala mensual que el arriendo `p` y el ingreso `y` (D-27): un viaje contra
un mes de arriendo no es comparable; 44 viajes sí. Con `alpha = 1` la puja lee
esa cantidad tal cual, con `lambda_h = |b_costo_h|` la pasa a pesos, y `beta = 1`
significa exactamente «el mismo ruido Gumbel que un viaje».

Es POR ESTRATO, y eso es deliberado: la heterogeneidad de acceso (tener auto,
valorar más el tiempo) es justamente lo que el logsum captura. D-22 había fijado
una accesibilidad común por ubicación porque `T` en minutos por estrato invertía
Alonso —el auto del rico le aplanaba el tiempo y el bid-rent lo leía como «no le
molesta la distancia»—; con el logsum en pesos (`/λ_h`) el rico puja más
empinado aunque viaje más rápido, y la inversión desaparece. Medido y fijado en
`tests/test_accesibilidad.py`.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.constantes import VIAJES_MES
from titirilquen_core.demand.utility import (
    UTIL_IMPOSIBLE,
    TiemposObservados,
    calcular_utilidades,
)
from titirilquen_core.supply.oferta import resolver_red_vacia


def logsum_por_celda(
    demand: DemandConfig,
    ciudad: CiudadLineal,
    tiempos_por_celda: list[TiemposObservados] | None = None,
    modos_habilitados: tuple[str, ...] | None = None,
) -> NDArray[np.float64]:
    """`logsum[h, i]`: utilidad esperada del viaje desde la celda `i` para el
    estrato `h`, ponderada por la tenencia de auto (`prob_auto`), en utiles de
    transporte. `tiempos_por_celda=None` ⇒ flujo libre (iteración 0 del MSA).

    Una rama (con/sin auto) sin ningún modo factible no aporta; si ninguna
    aporta, la celda vale `UTIL_IMPOSIBLE` (nadie puede viajar desde ahí)."""
    n = ciudad.n_celdas
    estratos = sorted(demand.estratos)
    out = np.full((len(estratos), n), UTIL_IMPOSIBLE, dtype=float)
    for h, estrato in enumerate(estratos):
        p_a = float(demand.estratos[estrato].prob_auto)
        for i in range(n):
            tiempos = tiempos_por_celda[i] if tiempos_por_celda is not None else None
            num = 0.0
            den = 0.0
            for tiene_auto, w in ((True, p_a), (False, 1.0 - p_a)):
                if w <= 0:
                    continue
                utils = calcular_utilidades(
                    estrato=estrato,
                    celda_origen=i,
                    tiene_auto=tiene_auto,
                    ciudad=ciudad,
                    config=demand,
                    tiempos_observados=tiempos,
                    modos_habilitados=modos_habilitados,
                )
                v = np.array(
                    [b.valor for b in utils.values() if b.feasible and b.valor > UTIL_IMPOSIBLE]
                )
                if v.size == 0:
                    continue
                mx = float(v.max())
                num += w * (mx + float(np.log(np.sum(np.exp(v - mx)))))
                den += w
            if den > 0:
                out[h, i] = num / den
    return out


def T_desde_logsum(logsum: NDArray[np.float64]) -> NDArray[np.float64]:
    """`T = −VIAJES_MES · logsum`: costo de accesibilidad mensual, en utiles de
    transporte. Es lo que entra a `f_h(i) = −alpha_h·T_h(i) − rho_h·dens(i)`."""
    return -float(VIAJES_MES) * np.asarray(logsum, dtype=float)


def tiempos_red_vacia(sim: SimulationConfig, ciudad: CiudadLineal) -> list[TiemposObservados]:
    """Tiempos por celda con la **red vacía** (demanda cero): BPR(0) en auto y
    bici, tren a frecuencia mínima con las estaciones configuradas. Es el
    contrafactual «la misma infraestructura sin nadie usándola», el baseline del
    ΔCS del acoplado y —desde D-42— la accesibilidad del suelo standalone."""
    oferta = resolver_red_vacia(sim, ciudad)
    car0, bike0, train0 = oferta.auto, oferta.bici, oferta.tren
    return [
        TiemposObservados(
            auto_total=float(car0.t_usuarios_min[i]),
            bici_total=float(bike0.t_usuarios_min[i]),
            tren_acceso=float(train0.t_acceso_min[i]),
            tren_espera=float(train0.t_espera_min[i]),
            tren_viaje=float(train0.t_viaje_min[i]),
        )
        for i in range(ciudad.n_celdas)
    ]


def T_flujo_libre(
    demand: DemandConfig,
    L: int,
    CBD: int,
    ancho_celda_km: float,
    modos_habilitados: tuple[str, ...] | None = None,
    *,
    supply: SupplyConfig,
) -> NDArray[np.float64]:
    """La `T` del módulo de suelo *standalone* y del arranque del acoplado: la
    accesibilidad de la **red vacía configurada** (estaciones, frecuencia mínima,
    velocidades de la oferta), sin congestión.

    Hasta D-42 usaba `_tiempos_flujo_libre` —velocidades de la demanda y 10 min
    de acceso + 5 de espera fijos—, así que cambiar la oferta del metro no movía
    el suelo standalone. La oferta es obligatoria a propósito: sin ella no hay
    una accesibilidad honesta que devolver. `CBD` se acepta por simetría con
    `LandUseCity.build`; `CiudadLineal` lo fija en `n_celdas // 2`."""
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=ancho_celda_km * L)
    if ciudad.cbd_index != CBD:
        raise ValueError(f"CBD={CBD} pero la ciudad lineal lo pone en {ciudad.cbd_index}")
    sim = SimulationConfig(
        city=CityConfig(n_celdas=L, largo_ciudad_km=ancho_celda_km * L),
        supply=supply,
        demand=demand,
    )
    tiempos = tiempos_red_vacia(sim, ciudad)
    return T_desde_logsum(logsum_por_celda(demand, ciudad, tiempos, modos_habilitados))
