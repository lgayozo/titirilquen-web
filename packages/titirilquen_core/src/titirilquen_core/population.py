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
    densidad_hab_km: float,
    share_estratos: tuple[float, float, float],
    demand_config: DemandConfig,
    teletrabajo_factor: float = 1.0,
    rng: np.random.Generator | None = None,
) -> list[Agente]:
    """Genera agentes según la densidad FÍSICA (hab/km) y shares configurados.

    Población total = densidad · largo de las celdas válidas, **independiente de
    la resolución de la grilla** (D-28): antes era hab/celda y refinar la grilla
    multiplicaba la población. El reparto por celda usa el método del mayor
    residuo sobre el objetivo uniforme densidad·Δx (determinista).

    El sorteo está **vectorizado** (3 llamadas a `rng` en total en vez de 3 por
    agente): clave para que el costo no explote con densidad alta.
    """
    if rng is None:
        rng = np.random.default_rng()

    estratos: tuple[StratumId, ...] = (1, 2, 3)
    celdas_validas = np.array(
        [i for i in range(ciudad.n_celdas) if i != ciudad.cbd_index], dtype=np.int64
    )
    objetivo_por_celda = densidad_hab_km * ciudad.ancho_celda_km
    total = int(round(objetivo_por_celda * celdas_validas.size))
    if total <= 0:
        return []
    conteo_por_celda = _mayor_residuo(
        np.full(celdas_validas.size, objetivo_por_celda), total
    )

    # Sorteos vectorizados (mismo orden conceptual: celda externa, densidad interna).
    estrato_idx = rng.choice(3, size=total, p=share_estratos)
    u_tele = rng.random(total)
    u_auto = rng.random(total)

    prob_tele_por = np.array(
        [
            min(1.0, demand_config.estratos[e].prob_teletrabajo * teletrabajo_factor)
            for e in estratos
        ]
    )
    prob_auto_por = np.array([demand_config.estratos[e].prob_auto for e in estratos])

    teletrabaja = u_tele < prob_tele_por[estrato_idx]
    tiene_auto = u_auto < prob_auto_por[estrato_idx]
    celda_de = np.repeat(celdas_validas, conteo_por_celda)

    return [
        Agente(
            id=k + 1,
            celda_origen=int(celda_de[k]),
            estrato=estratos[int(estrato_idx[k])],
            teletrabaja=bool(teletrabaja[k]),
            tiene_auto=bool(tiene_auto[k]),
        )
        for k in range(total)
    ]


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


def generar_poblacion_desde_densidad(
    *,
    Q: np.ndarray,
    densidad_celda: np.ndarray,
    ancho_celda_km: float,
    cbd_index: int,
    demand_config: DemandConfig,
    teletrabajo_factor: float = 1.0,
) -> list[Agente]:
    """Población **determinista** desde la densidad por celda del equilibrio.

    `densidad_celda[i]` (hab/km) es endógena del precio del suelo (ver
    `LandUseCity.densidad_por_celda`); la composición `Q[:,i]` reparte esa
    población de la celda entre estratos:

        N[h, i] = round( Q[h, i] · densidad_celda[i] · Δx )

    así que el total por celda es `densidad_celda(i)·Δx`. El CBD se omite (no se
    viaja hacia sí mismo). Teletrabajo/auto se fijan por conteos redondeados,
    igual que la versión `_det`."""
    Q = np.asarray(Q, dtype=float)
    dens = np.asarray(densidad_celda, dtype=float)
    n_strata, n_celdas = Q.shape

    agentes: list[Agente] = []
    id_counter = 1
    estratos_valid: tuple[StratumId, ...] = (1, 2, 3)

    for i in range(n_celdas):
        if i == cbd_index:
            continue
        # hogares por estrato: la composición Q reparte la densidad de la celda i
        N_h = np.round(Q[:, i] * dens[i] * ancho_celda_km).astype(int)
        for h in range(n_strata):
            n = int(N_h[h])
            if n <= 0:
                continue
            estrato: StratumId = estratos_valid[h]
            s = demand_config.estratos[estrato]
            prob_tele = min(1.0, s.prob_teletrabajo * teletrabajo_factor)
            n_tele = int(round(n * prob_tele))
            n_work = n - n_tele
            n_auto = int(round(n_work * s.prob_auto))
            for k in range(n):
                tele = k < n_tele
                tiene_auto = (not tele) and (k - n_tele) < n_auto
                agentes.append(
                    Agente(
                        id=id_counter,
                        celda_origen=i,
                        estrato=estrato,
                        teletrabaja=tele,
                        tiene_auto=tiene_auto,
                    )
                )
                id_counter += 1

    return agentes


def _mayor_residuo(target: np.ndarray, total: int) -> np.ndarray:
    """Redondea `target` (que suma ~`total`) a enteros que suman EXACTO `total`,
    por el método del mayor residuo. Determinista."""
    base = np.floor(target).astype(int)
    falta = total - int(base.sum())
    if falta > 0:
        frac = target - np.floor(target)
        orden = np.argsort(-frac, kind="stable")
        for k in range(falta):
            base[orden[k % len(orden)]] += 1
    elif falta < 0:  # raro (fp): quitar del menor residuo
        frac = target - np.floor(target)
        orden = np.argsort(frac, kind="stable")
        for k in range(-falta):
            base[orden[k % len(orden)]] = max(0, base[orden[k % len(orden)]] - 1)
    return base


def generar_poblacion_desde_land_use_det(
    *,
    Q: np.ndarray,
    S: np.ndarray,
    cbd_index: int,
    demand_config: DemandConfig,
    teletrabajo_factor: float = 1.0,
) -> list[Agente]:
    """Versión **determinista** (sin rng) de `generar_poblacion_desde_land_use`.

    Reparte los `S_i` hogares de cada celda entre estratos por **mayor residuo**
    sobre `S_i·Q[:,i]` (Σ_h = S_i exacto), y fija teletrabajo/auto por conteos
    redondeados (no por sorteo). La usa el loop acoplado para que el equilibrio
    suelo↔transporte sea reproducible y **converja** (sin el piso estocástico del
    remuestreo; ver D-14). El CBD se omite (no se viaja hacia sí mismo).
    """
    Q = np.asarray(Q, dtype=float)
    S = np.asarray(S, dtype=int)
    n_strata, n_celdas = Q.shape

    agentes: list[Agente] = []
    id_counter = 1
    estratos_valid: tuple[StratumId, ...] = (1, 2, 3)

    for i in range(n_celdas):
        if i == cbd_index:
            continue
        Si = int(S[i])
        if Si <= 0:
            continue
        N_h = _mayor_residuo(Q[:, i] * Si, Si)  # hogares por estrato en la celda i
        for h in range(n_strata):
            n = int(N_h[h])
            if n <= 0:
                continue
            estrato: StratumId = estratos_valid[h]
            s = demand_config.estratos[estrato]
            prob_tele = min(1.0, s.prob_teletrabajo * teletrabajo_factor)
            n_tele = int(round(n * prob_tele))
            n_work = n - n_tele
            n_auto = int(round(n_work * s.prob_auto))
            for k in range(n):
                tele = k < n_tele
                # entre los trabajadores, los primeros `n_auto` tienen auto
                tiene_auto = (not tele) and (k - n_tele) < n_auto
                agentes.append(
                    Agente(
                        id=id_counter,
                        celda_origen=i,
                        estrato=estrato,
                        teletrabaja=tele,
                        tiene_auto=tiene_auto,
                    )
                )
                id_counter += 1

    return agentes
