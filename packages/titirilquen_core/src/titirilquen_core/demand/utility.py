"""Funciones de utilidad por modo — logit multinomial.

Portado de `titirilquen-repo/app.py:281-338`. Incluye la descomposición
(breakdown) de cada utilidad para facilitar la visualización educativa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, StratumId

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


def _tiempos_flujo_libre(dist_km: float, globales) -> TiemposObservados:
    return TiemposObservados(
        auto_total=(dist_km / globales.v_auto) * 60,
        bici_total=(dist_km / globales.v_bici) * 60,
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
) -> dict[Modo, UtilityBreakdown]:
    """Calcula la utilidad de cada modo para un agente en una celda dada.

    Si `tiempos_observados is None` (iteración 0), se asumen tiempos de flujo libre.
    """
    betas = config.estratos[estrato].betas
    penal = betas.penalizaciones_fisicas
    gl = config.globales

    dist_km = abs(ciudad.cbd_index - celda_origen) * ciudad.ancho_celda_km

    tiempos = tiempos_observados if tiempos_observados is not None else _tiempos_flujo_libre(dist_km, gl)
    t_cam = (dist_km / gl.v_caminata) * 60

    # AUTO
    c_auto = dist_km * gl.costo_combustible_km + gl.costo_parking
    asc_auto = betas.asc_auto
    v_t_auto = betas.b_tiempo_viaje * tiempos.auto_total
    v_c_auto = betas.b_costo * c_auto
    if tiene_auto:
        v_auto = asc_auto + v_t_auto + v_c_auto
        auto_breakdown = UtilityBreakdown("Auto", v_auto, asc_auto, v_t_auto, v_c_auto, feasible=True)
    else:
        auto_breakdown = UtilityBreakdown("Auto", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)

    # METRO
    c_metro = gl.costo_tarifa_metro
    asc_metro = betas.asc_metro
    v_t_metro = (
        betas.b_tiempo_viaje * tiempos.tren_viaje
        + betas.b_tiempo_espera * tiempos.tren_espera
        + betas.b_tiempo_caminata * tiempos.tren_acceso
    )
    v_c_metro = betas.b_costo * c_metro
    v_metro = asc_metro + v_t_metro + v_c_metro
    metro_breakdown = UtilityBreakdown("Metro", v_metro, asc_metro, v_t_metro, v_c_metro, feasible=True)

    # BICI — penalizaciones aditivas escalonadas (ver D-02)
    if tiempos.bici_total > 45:
        bici_breakdown = UtilityBreakdown("Bici", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)
    else:
        p = 0.0
        if tiempos.bici_total > 10:
            p += penal.bici_10
        if tiempos.bici_total > 20:
            p += penal.bici_20
        if tiempos.bici_total > 30:
            p += penal.bici_30
        asc_bici = betas.asc_bici
        v_t_bici = betas.b_tiempo_viaje * tiempos.bici_total
        v_bici = asc_bici + v_t_bici + p
        bici_breakdown = UtilityBreakdown("Bici", v_bici, asc_bici, v_t_bici, 0.0, v_penalizaciones=p, feasible=True)

    # CAMINATA — usa b_tiempo_caminata (no b_tiempo_viaje); ver D-03
    if t_cam > 30:
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
        cam_breakdown = UtilityBreakdown("Caminata", v_cam, asc_cam, v_t_cam, 0.0, v_penalizaciones=p, feasible=True)

    return {
        "Auto": auto_breakdown,
        "Metro": metro_breakdown,
        "Bici": bici_breakdown,
        "Caminata": cam_breakdown,
    }
