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


def probabilidades_wardrop(utilidades: dict[Modo, UtilityBreakdown]) -> dict[Modo, float]:
    """Elección DETERMINÍSTICA: toda la probabilidad al modo de mayor utilidad.

    Es el límite del logit cuando la escala de los coeficientes tiende a
    infinito, o sea cuando la heterogeneidad de gustos no observada se desvanece.
    Combinado con el promediado del MSA, el punto fijo es un equilibrio de
    Wardrop: todo modo usado termina con el mismo costo generalizado, porque
    mientras uno sea mejor la iteración sigue moviéndole demanda.

    La diferencia con `probabilidades_logit` no es de precisión sino de
    supuesto, y decide resultados: bajo Wardrop los usuarios arbitran hasta
    igualar costos, así que una mejora vial se disipa por completo; bajo logit el
    trasvase se detiene antes y el usuario del modo que mejoró conserva una
    ganancia. De ahí que la paradoja de Downs-Thomson aparezca con el primero y
    no con el segundo (docs/CONTINUAR.md §5).

    Empates: se reparte en partes iguales entre los modos empatados. Sin eso, un
    desempate arbitrario por orden de diccionario introduciría un sesgo estable
    entre iteraciones.
    """
    feasibles = [m for m, u in utilidades.items() if u.feasible]
    out: dict[Modo, float] = dict.fromkeys(utilidades, 0.0)
    if not feasibles:
        return out
    mejor = max(utilidades[m].valor for m in feasibles)
    empatados = [m for m in feasibles if utilidades[m].valor >= mejor - _TOL_EMPATE]
    for m in empatados:
        out[m] = 1.0 / len(empatados)
    return out


_TOL_EMPATE = 1e-12
"""Tolerancia para considerar empatadas dos utilidades en `probabilidades_wardrop`."""


def elegir_modo(
    utilidades: dict[Modo, UtilityBreakdown],
    *,
    rng: np.random.Generator | None = None,
) -> Modo | None:
    """Sortea un modo según sus probabilidades logit.

    Devuelve `None` si el agente no tiene ningún modo feasible (p.ej. sin auto y
    con todos los demás modos deshabilitados): es un viaje "varado" que no se
    asigna a ningún modo.
    """
    probs = probabilidades_logit(utilidades)
    modos = list(probs.keys())
    weights = np.array([probs[m] for m in modos])

    if weights.sum() <= 0:
        return None

    if rng is None:
        rng = np.random.default_rng()
    idx = rng.choice(len(modos), p=weights)
    return modos[idx]  # type: ignore[return-value]
