"""Elección de modo — logit multinomial con numerical stabilization.

Portado de `titirilquen-repo/app.py:341-350`. Es el único reparto del modelo:
la carga determinística (`probabilidades_todo_o_nada`) se retiró en nov-2026.
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
        return dict.fromkeys(utilidades, 0.0)

    valores: NDArray[np.float64] = np.array([utilidades[m].valor for m in modos_feasibles])
    valores = valores - np.max(valores)
    exp_v = np.exp(valores)
    probs = exp_v / np.sum(exp_v)

    out: dict[Modo, float] = dict.fromkeys(utilidades, 0.0)
    for m, p in zip(modos_feasibles, probs, strict=True):
        out[m] = float(p)
    return out
