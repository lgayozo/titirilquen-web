"""Resolver los tres modos congestionables de una vez.

Los módulos `car`, `bike` y `train` son funciones puras, y a propósito: no
conocen `SimulationConfig` ni `CiudadLineal`, así que se leen y se testean
aisladas. El precio de eso es que llamarlas exige desarmar la configuración
campo por campo — unas cuarenta líneas de reenvío que estaban escritas **tres
veces**: en el loop del MSA, en el cálculo de la red vacía de
`coupled_metrics`, y en el script que audita el método determinístico.

No es una duplicación inocente. Cuando se retiró `tasa_carga` del esquema hubo
que tocar los tres sitios, y el que vive en un script no lo cubre ningún test:
si se hubiera olvidado, habría fallado recién al correrlo a mano.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.supply.bike import BikeSupplyResult, demora_bici_tramo
from titirilquen_core.supply.car import CarSupplyResult, demora_auto_tramo
from titirilquen_core.supply.train import TrainSupplyResult, oferta_tren


@dataclass(frozen=True)
class OfertaResuelta:
    """Los tres modos congestionables para una demanda dada."""

    auto: CarSupplyResult
    bici: BikeSupplyResult
    tren: TrainSupplyResult


def resolver_oferta(
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    demanda_auto: NDArray[np.float64],
    demanda_bici: NDArray[np.float64],
    demanda_metro: NDArray[np.float64],
) -> OfertaResuelta:
    """Tiempos de viaje que resultan de cargar la red con esa demanda.

    La caminata no aparece: es puramente geométrica (distancia / velocidad) y no
    se congestiona, así que cada consumidor la deriva por su cuenta.
    """
    car_p, bike_p, train_p = sim.supply.car, sim.supply.bike, sim.supply.train
    return OfertaResuelta(
        auto=demora_auto_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            demanda=demanda_auto,
            v_max_kmh=car_p.v_max_kmh,
            ancho_pista_m=car_p.ancho_pista_m,
            largo_vehiculo_m=car_p.largo_vehiculo_m,
            gap_m=car_p.gap_m,
            L_ciudad_km=ciudad.largo_total_km,
            num_pistas=car_p.num_pistas,
            alpha_bpr=car_p.alpha_bpr,
            beta_bpr=car_p.beta_bpr,
            capacidad_pista=car_p.capacidad_pista,
        ),
        bici=demora_bici_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            capacidad=bike_p.capacidad_pista,
            demanda=demanda_bici,
            v_media=bike_p.v_media_kmh,
            L_ciudad_km=ciudad.largo_total_km,
            alpha=bike_p.alpha_bpr,
            beta=bike_p.beta_bpr,
            pendiente_porcentaje=sim.city.pendiente_porcentaje,
            v_caminata=sim.demand.globales.v_caminata,
        ),
        tren=oferta_tren(
            demanda=demanda_metro,
            L_ciudad_km=ciudad.largo_total_km,
            x_centro_km=ciudad.cbd_km,
            v_tren_kmh=train_p.v_tren_kmh,
            capacidad_tren=train_p.capacidad_tren,
            num_estaciones=train_p.num_estaciones,
            v_caminata_kmh=train_p.v_caminata_kmh,
            tiempo_detencion_min=train_p.tiempo_detencion_min,
            frec_min=train_p.frec_min,
            frec_max=train_p.frec_max,
            anden_alpha=train_p.anden_alpha,
            anden_beta=train_p.anden_beta,
        ),
    )


def resolver_red_vacia(sim: SimulationConfig, ciudad: CiudadLineal) -> OfertaResuelta:
    """La red sin nadie encima: el contrafactual «no existe la ciudad».

    Es el ancla contra la que el módulo acoplado mide el excedente. El metro sin
    pasajeros opera a `frec_min` (su frecuencia es endógena a la demanda), que
    es justamente lo que hace informativo el contrafactual.
    """
    cero = np.zeros(ciudad.n_celdas)
    return resolver_oferta(sim, ciudad, cero, cero, cero)
