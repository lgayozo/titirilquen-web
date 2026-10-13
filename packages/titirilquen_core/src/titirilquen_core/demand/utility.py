"""Funciones de utilidad por modo — logit multinomial.

Portado de `titirilquen-repo/app.py:281-338`. Incluye la descomposición
(breakdown) de cada utilidad para facilitar la visualización educativa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, GlobalConfig, StratumId
from titirilquen_core.constantes import VIAJES_POR_TOUR

Modo = Literal["Auto", "Metro", "Bici", "Caminata"]

UTIL_IMPOSIBLE = -9999.0
"""Valor que representa utilidad `−∞` para modos fuera de dominio
(caminata > 30 min, bici > 45 min, auto sin tenencia)."""


@dataclass(frozen=True)
class TiemposObservados:
    """Tiempos observados desde la oferta para una celda específica.

    Si `None` para toda una simulación, se usan tiempos de flujo libre
    (iteración 0 del loop de equilibrio).
    """

    auto_total: float
    bici_total: float
    tren_acceso: float
    tren_espera: float
    tren_viaje: float
    #: Tiempo de bici con la red VACÍA (BPR(0), con pendiente). Sobre él se
    #: evalúan los escalones y el corte de la bici, no sobre `bici_total` (D9):
    #: miden esfuerzo físico —distancia y pendiente—, como los de la caminata.
    #: Evaluados sobre el tiempo congestionado hacían discontinua la demanda
    #: como función de los tiempos, y sin continuidad no hay garantía de punto
    #: fijo (Boyles et al., p. 311). La congestión sigue entrando, por
    #: `b_tiempo_viaje · bici_total`.
    bici_libre: float


@dataclass(frozen=True)
class UtilityBreakdown:
    """Descomposición de la utilidad de un modo. Útil para visualización."""

    modo: Modo
    valor: float
    asc: float
    v_tiempo: float
    v_costo: float
    v_penalizaciones: float = 0.0
    feasible: bool = True


def costo_monetario_auto(dist_km: float, globales: GlobalConfig) -> float:
    """Dinero ($) de un viaje de ida en auto: bencina y peaje por km recorrido,
    más medio parking, que es por tour (día). Única fuente: la usan la elección
    modal y los agregados de bienestar, que antes tenían cada uno su copia."""
    por_km = globales.costo_combustible_km + globales.peaje_km
    return dist_km * por_km + globales.costo_parking / VIAJES_POR_TOUR


def _tiempos_flujo_libre(dist_km: float, globales) -> TiemposObservados:
    return TiemposObservados(
        auto_total=(dist_km / globales.v_auto) * 60,
        bici_total=(dist_km / globales.v_bici) * 60,
        bici_libre=(dist_km / globales.v_bici) * 60,
        tren_acceso=10.0,
        tren_espera=5.0,
        tren_viaje=(dist_km / globales.v_metro) * 60,
    )


def calcular_utilidades(
    *,
    estrato: StratumId,
    celda_origen: int,
    tiene_auto: bool,
    ciudad: CiudadLineal,
    config: DemandConfig,
    tiempos_observados: TiemposObservados | None,
    modos_habilitados: tuple[Modo, ...] | frozenset[Modo] | None = None,
) -> dict[Modo, UtilityBreakdown]:
    """Calcula la utilidad de cada modo para un agente en una celda dada.

    Si `tiempos_observados is None` (iteración 0), se asumen tiempos de flujo libre.

    `modos_habilitados` restringe el set de elección: cualquier modo fuera del
    conjunto se marca infeasible (utilidad −∞). `None` ⇒ todos habilitados.
    """
    betas = config.estratos[estrato].betas
    penal = betas.penalizaciones_fisicas
    gl = config.globales

    dist_km = abs(ciudad.cbd_index - celda_origen) * ciudad.ancho_celda_km

    tiempos = (
        tiempos_observados if tiempos_observados is not None else _tiempos_flujo_libre(dist_km, gl)
    )
    t_cam = (dist_km / gl.v_caminata) * 60

    # AUTO
    c_auto = costo_monetario_auto(dist_km, gl)
    asc_auto = betas.asc_auto
    v_t_auto = betas.b_tiempo_viaje * tiempos.auto_total
    v_c_auto = betas.b_costo * c_auto
    if tiene_auto:
        v_auto = asc_auto + v_t_auto + v_c_auto
        auto_breakdown = UtilityBreakdown(
            "Auto", v_auto, asc_auto, v_t_auto, v_c_auto, feasible=True
        )
    else:
        auto_breakdown = UtilityBreakdown("Auto", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)

    # METRO
    c_metro = gl.costo_tarifa_metro
    asc_metro = betas.asc_metro
    v_t_metro = (
        betas.b_tiempo_viaje * tiempos.tren_viaje
        + betas.b_tiempo_espera * tiempos.tren_espera
        + betas.b_tiempo_acceso * tiempos.tren_acceso
    )
    v_c_metro = betas.b_costo * c_metro
    v_metro = asc_metro + v_t_metro + v_c_metro
    # Sin tramo en tren no hay viaje en metro. `tren_viaje == 0` significa que la
    # estación más cercana es la del CBD, o sea el destino: "tomar el metro"
    # sería caminar hasta donde uno va y no subirse a nada. Ese caso entraba como
    # factible y esquivaba el corte de 30 min de la caminata, porque el acceso no
    # tiene umbral: con 3 estaciones (espaciado 10 km) la celda a 15 km asignaba
    # 10,9% de sus viajes a un "metro" de 62 min de caminata y 0 min de tren, y
    # la banda 12-15 km rondaba 11-17%. La caminata pura de esa misma distancia
    # estaba prohibida. Ver también `paradas_intermedias` en supply/train.py.
    # La regla hace saltar el logsum —y la T del suelo— a media distancia entre
    # el CBD y la primera estación. Es deliberado (D-69): usar ahí la estación
    # siguiente elimina el salto pero le da al logit viajes de metro dominados
    # (caminar alejándose del destino), así que la regla actúa como filtro de
    # dominancia.
    if tiempos.tren_viaje <= 0:
        metro_breakdown = UtilityBreakdown("Metro", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)
    else:
        metro_breakdown = UtilityBreakdown(
            "Metro", v_metro, asc_metro, v_t_metro, v_c_metro, feasible=True
        )

    # BICI — penalizaciones aditivas escalonadas (ver D-02), sobre el tiempo de
    # red vacía; el tiempo congestionado entra sólo por b_tiempo (D9).
    t_esfuerzo = tiempos.bici_libre
    if t_esfuerzo > gl.corte_bici_min:
        bici_breakdown = UtilityBreakdown("Bici", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)
    else:
        p = 0.0
        if t_esfuerzo > 10:
            p += penal.bici_10
        if t_esfuerzo > 20:
            p += penal.bici_20
        if t_esfuerzo > 30:
            p += penal.bici_30
        asc_bici = betas.asc_bici
        v_t_bici = betas.b_tiempo_viaje * tiempos.bici_total
        v_bici = asc_bici + v_t_bici + p
        bici_breakdown = UtilityBreakdown(
            "Bici", v_bici, asc_bici, v_t_bici, 0.0, v_penalizaciones=p, feasible=True
        )

    # CAMINATA — usa b_tiempo_caminata (no b_tiempo_viaje); ver D-03
    if t_cam > gl.corte_caminata_min:
        cam_breakdown = UtilityBreakdown("Caminata", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)
    else:
        p = 0.0
        if t_cam > 5:
            p += penal.walk_5
        if t_cam > 15:
            p += penal.walk_15
        if t_cam > 25:
            p += penal.walk_25
        asc_cam = betas.asc_caminata
        v_t_cam = betas.b_tiempo_caminata * t_cam
        v_cam = asc_cam + v_t_cam + p
        cam_breakdown = UtilityBreakdown(
            "Caminata", v_cam, asc_cam, v_t_cam, 0.0, v_penalizaciones=p, feasible=True
        )

    resultado = {
        "Auto": auto_breakdown,
        "Metro": metro_breakdown,
        "Bici": bici_breakdown,
        "Caminata": cam_breakdown,
    }

    if modos_habilitados is not None:
        habilitados = set(modos_habilitados)
        for m, bd in resultado.items():
            if m not in habilitados and bd.feasible:
                resultado[m] = UtilityBreakdown(m, UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)

    return resultado
