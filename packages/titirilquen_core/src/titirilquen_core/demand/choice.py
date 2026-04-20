"""Elección de modo — logit multinomial con numerical stabilization.

Portado de `titirilquen-repo/app.py:341-350`. El sorteo usa el RNG de numpy
para reproducibilidad si se fija `seed`.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.demand.utility import UtilityBreakdown

Modo = Literal["Auto", "Metro", "Bici", "Caminata"]


def probabilidades_logit(utilidades: dict[Modo, UtilityBreakdown]) -> dict[Modo, float]:
    """Convierte un dict de `UtilityBreakdown` en probabilidades de elección.

    Modos infeasibles (feasible=False) se excluyen — equivalente al filtrado
    `utils_filtradas.pop("Auto")` del código original cuando `tiene_auto = False`.
    """
    modos_feasibles = [m for m, u in utilidades.items() if u.feasible]
    if not modos_feasibles:
        return {m: 0.0 for m in utilidades}

    valores: NDArray[np.float64] = np.array([utilidades[m].valor for m in modos_feasibles])
    valores = valores - np.max(valores)
    exp_v = np.exp(valores)
    probs = exp_v / np.sum(exp_v)

    out: dict[Modo, float] = {m: 0.0 for m in utilidades}
    for m, p in zip(modos_feasibles, probs, strict=True):
        out[m] = float(p)
    return out


def elegir_modo(
    utilidades: dict[Modo, UtilityBreakdown],
    *,
    rng: np.random.Generator | None = None,
) -> Modo:
    """Sortea un modo según sus probabilidades logit."""
    probs = probabilidades_logit(utilidades)
    modos = list(probs.keys())
    weights = np.array([probs[m] for m in modos])

    if rng is None:
        rng = np.random.default_rng()
    idx = rng.choice(len(modos), p=weights)
    return modos[idx]  # type: ignore[return-value]
