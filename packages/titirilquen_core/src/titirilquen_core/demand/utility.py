"""Funciones de utilidad por modo — logit multinomial.

Portado de `titirilquen-repo/app.py:281-338`. Incluye la descomposición
(breakdown) de cada utilidad para facilitar la visualización educativa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, GlobalConfig, StratumId
from titirilquen_core.constantes import (
    A_DOMINANCIA_METRO,
    OMEGA_CORTE_SUAVE,
    OMEGA_DOMINANCIA_METRO,
    VIAJES_POR_TOUR,
)

Modo = Literal["Auto", "Metro", "Bici", "Caminata"]

UTIL_IMPOSIBLE = -9999.0
"""Valor que representa utilidad `−∞` para modos fuera de dominio
(auto sin tenencia, metro desde la celda del CBD y, con `umbrales="escalones"`,
caminata y bici sobre su corte)."""


def _escalones(
    t: float, umbrales: tuple[float, float, float], penal: tuple[float, float, float]
) -> float:
    """Penalización física escalonada (D-02): suma `p_k` por cada umbral cruzado."""
    return sum(p for u, p in zip(umbrales, penal, strict=True) if t > u)


def _rampa(
    t: float, umbrales: tuple[float, float, float], penal: tuple[float, float, float]
) -> float:
    """Penalización física continua (`umbrales="suaves"`).

    Interpola la penalización acumulada de los escalones por sus PUNTOS MEDIOS:
    el escalón k (de `u_k` a `u_{k+1}`) se reemplaza por una rampa que vale lo
    mismo en su centro, así que el nivel medio de cada tramo se conserva y la
    calibración de los `p_k` sigue significando lo mismo. Con umbrales cada 10
    min los nodos son `u_k − 5`. Más allá del último sigue con la última
    pendiente; pendientes crecientes (|p| creciente) ⇒ convexa.
    """
    h0 = (umbrales[1] - umbrales[0]) / 2
    h2 = (umbrales[2] - umbrales[1]) / 2
    xs = (umbrales[0] - h0, umbrales[1] - h0, umbrales[2] - h2, umbrales[2] + h2)
    ys = (0.0, penal[0], penal[0] + penal[1], penal[0] + penal[1] + penal[2])
    if t <= xs[-1]:
        return float(np.interp(t, xs, ys))
    return ys[-1] + (t - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])


def _ln_phi(x: float, omega: float) -> float:
    """Corte suave tipo CMNL (Martínez, Aguila y Hurtubia 2009; Martínez,
    *Microeconomic Modeling in Urban Science*, ec. 5.33): `ln φ` con
    `φ = 1/(1 + e^{ωx})`. ≈0 para x ≪ 0, −ln 2 en x = 0 y ≈ −ωx para x ≫ 0.
    Entra sumado a la utilidad, en la escala del logit de transporte (μ = 1)."""
    return -float(np.logaddexp(0.0, omega * x))


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
    #
    # Con `umbrales="suaves"` la oferta ya no asigna la estación del CBD fuera de
    # la celda del CBD (`excluir_estacion_cbd` en supply/train.py) y el filtro es
    # suave: dominancia de Pareto sobre (tiempo generalizado, tarifa) con umbral
    # de percepción multiplicativo `a` (Cascetta y Papola 2009, ec. 3). Como la
    # tarifa del metro ya es mayor que la de caminar (cero), basta comparar
    # tiempos: el metro es dominado por caminar directo cuando
    # GT_metro ≥ a·GT_caminata, y ahí se desvanece por un corte CMNL. Los pesos
    # del tiempo generalizado son las razones de los coeficientes del estrato
    # (minutos equivalentes en vehículo). Comparar UTILIDADES no serviría: el
    # ASC y el ruido Gumbel ya están en ellas, y lo que se filtra es la
    # alternativa que ningún viajero sensato consideraría.
    suaves = gl.umbrales == "suaves"
    if tiempos.tren_viaje <= 0:
        metro_breakdown = UtilityBreakdown("Metro", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)
    else:
        p_metro = 0.0
        if suaves:
            bv = betas.b_tiempo_viaje
            gt_metro = (
                betas.b_tiempo_acceso / bv * tiempos.tren_acceso
                + betas.b_tiempo_espera / bv * tiempos.tren_espera
                + tiempos.tren_viaje
            )
            gt_cam = betas.b_tiempo_caminata / bv * t_cam
            p_metro = _ln_phi(gt_metro - A_DOMINANCIA_METRO * gt_cam, OMEGA_DOMINANCIA_METRO)
        metro_breakdown = UtilityBreakdown(
            "Metro",
            v_metro + p_metro,
            asc_metro,
            v_t_metro,
            v_c_metro,
            v_penalizaciones=p_metro,
            feasible=True,
        )

    # BICI y CAMINATA — penalizaciones físicas aditivas (D-02) y corte. Con
    # «escalones», saltos en 10/20/30 min de bici y 5/15/25 a pie, y sobre el
    # corte el modo sale del conjunto de elección. Con «suaves», rampas por los
    # puntos medios de esos escalones (`_rampa`) y el corte como penalización
    # CMNL, de modo que la utilidad es continua en la distancia.
    #
    # La bici se evalúa sobre su tiempo de red vacía; el congestionado entra
    # sólo por b_tiempo (D9). La caminata usa b_tiempo_caminata (D-03).
    def _fisica(t: float, umbrales, pen, corte: float) -> float | None:
        if suaves:
            return _rampa(t, umbrales, pen) + _ln_phi(t - corte, OMEGA_CORTE_SUAVE)
        if t > corte:
            return None
        return _escalones(t, umbrales, pen)

    t_esfuerzo = tiempos.bici_libre
    p = _fisica(
        t_esfuerzo, (10, 20, 30), (penal.bici_10, penal.bici_20, penal.bici_30), gl.corte_bici_min
    )
    if p is None:
        bici_breakdown = UtilityBreakdown("Bici", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)
    else:
        asc_bici = betas.asc_bici
        v_t_bici = betas.b_tiempo_viaje * tiempos.bici_total
        v_bici = asc_bici + v_t_bici + p
        bici_breakdown = UtilityBreakdown(
            "Bici", v_bici, asc_bici, v_t_bici, 0.0, v_penalizaciones=p, feasible=True
        )

    p = _fisica(
        t_cam, (5, 15, 25), (penal.walk_5, penal.walk_15, penal.walk_25), gl.corte_caminata_min
    )
    if p is None:
        cam_breakdown = UtilityBreakdown("Caminata", UTIL_IMPOSIBLE, 0, 0, 0, feasible=False)
    else:
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
