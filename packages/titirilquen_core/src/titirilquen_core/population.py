"""Los agentes del transporte, generados desde el uso de suelo.

Una sola fábrica: `generar_poblacion_desde_land_use_det` reparte los `S_i`
hogares que la ciudad ofrece en cada celda entre estratos según `Q`, y sortea
teletrabajo y tenencia de auto una vez por agente. Hasta sep-2026 convivía con
`generar_poblacion`, que poblaba con una densidad plana (`densidad_hab_km` ×
`share_estratos`) sin pasar por el suelo: dos fuentes de población para la
misma ciudad, y la app sólo usaba una (D-46). La densidad plana se reproduce
con `forma="uniforme"` y `localizacion="original"`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from titirilquen_core.config import DemandConfig, StratumId


@dataclass
class Agente:
    id: int
    celda_origen: int
    estrato: StratumId
    teletrabaja: bool
    tiene_auto: bool
    modo_elegido: str | None = None
    utilidad_elegida: float = 0.0


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
    """Genera la población a partir del uso de suelo, de forma **determinista**.

    Existió una variante estocástica (`generar_poblacion_desde_land_use`, que
    remuestreaba con `rng`); se retiró por no tener llamadores: el piso de ruido
    del remuestreo impedía que el loop acoplado convergiera (D-14), así que en
    la práctica siempre se usó esta.

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
            n_tele = round(n * prob_tele)
            n_work = n - n_tele
            n_auto = round(n_work * s.prob_auto)
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
