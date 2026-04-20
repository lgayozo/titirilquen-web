"""Generador de población sintética — ciudad lineal.

Modo V1 (sin uso de suelo): reparte hogares por estrato proporcionalmente a
`share_estratos` y uniformemente en el espacio excluyendo el CBD.

Ver D-11 del registro de discrepancias: NO portamos `generar_poblacion` del
código original (uniforme en estratos), usamos los shares configurables.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, StratumId
from titirilquen_core.land_use.ciudad import LandUseCity


@dataclass
class Agente:
    id: int
    celda_origen: int
    estrato: StratumId
    teletrabaja: bool
    tiene_auto: bool
    modo_elegido: str | None = None
    utilidad_elegida: float = 0.0


def generar_poblacion(
    *,
    ciudad: CiudadLineal,
    densidad_por_celda: int,
    share_estratos: tuple[float, float, float],
    demand_config: DemandConfig,
    teletrabajo_factor: float = 1.0,
    rng: np.random.Generator | None = None,
) -> list[Agente]:
    """Genera agentes según densidad y shares configurados."""
    if rng is None:
        rng = np.random.default_rng()

    agentes: list[Agente] = []
    id_counter = 1
    estratos: tuple[StratumId, ...] = (1, 2, 3)

    for i in range(ciudad.n_celdas):
        if i == ciudad.cbd_index:
            continue
        for _ in range(densidad_por_celda):
            estrato_idx = int(rng.choice(3, p=share_estratos))
            estrato: StratumId = estratos[estrato_idx]
            s = demand_config.estratos[estrato]

            prob_tele = min(1.0, s.prob_teletrabajo * teletrabajo_factor)
            teletrabaja = bool(rng.random() < prob_tele)
            tiene_auto = bool(rng.random() < s.prob_auto)

            agentes.append(
                Agente(
                    id=id_counter,
                    celda_origen=i,
                    estrato=estrato,
                    teletrabaja=teletrabaja,
                    tiene_auto=tiene_auto,
                )
            )
            id_counter += 1

    return agentes


def generar_poblacion_desde_land_use(
    *,
    land_use_city: LandUseCity,
    demand_config: DemandConfig,
    teletrabajo_factor: float = 1.0,
    rng: np.random.Generator | None = None,
) -> list[Agente]:
    """Genera agentes respetando la asignación espacial del uso de suelo.

    Cada hogar en `land_use_city.parcelas[i]` se convierte en un agente en la
    celda `i`. Los atributos teletrabajo/auto se sortean según la config del
    estrato. Los hogares en el CBD se omiten (no trabajan yendo hacia sí
    mismos).
    """
    if rng is None:
        rng = np.random.default_rng()

    agentes: list[Agente] = []
    id_counter = 1
    estratos_valid: tuple[StratumId, ...] = (1, 2, 3)

    for i, parcela in enumerate(land_use_city.parcelas):
        if i == land_use_city.cbd_index:
            continue
        for h in parcela:
            if h not in (1, 2, 3):
                continue
            estrato: StratumId = estratos_valid[h - 1]
            s = demand_config.estratos[estrato]
            prob_tele = min(1.0, s.prob_teletrabajo * teletrabajo_factor)
            agentes.append(
                Agente(
                    id=id_counter,
                    celda_origen=i,
                    estrato=estrato,
                    teletrabaja=bool(rng.random() < prob_tele),
                    tiene_auto=bool(rng.random() < s.prob_auto),
                )
            )
            id_counter += 1

    return agentes
