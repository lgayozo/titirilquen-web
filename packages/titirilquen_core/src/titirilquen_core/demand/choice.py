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


_TOL_EMPATE = 1e-12
"""Tolerancia para considerar empatadas dos utilidades en `probabilidades_todo_o_nada`."""


def probabilidades_todo_o_nada(utilidades: dict[Modo, UtilityBreakdown]) -> dict[Modo, float]:
    """Elección DETERMINÍSTICA: toda la probabilidad al modo de mayor utilidad.

    Es el límite del logit cuando la escala de los coeficientes tiende a
    infinito, o sea cuando la heterogeneidad de gustos no observada se desvanece.

    **NO produce un equilibrio de Wardrop en el sentido agregado**, y el valor
    `"todo_o_nada"` del schema es sólo el nombre histórico de la opción (se mantiene
    porque cambiarlo rompería los escenarios `.ttrq.json` ya guardados). El
    principio de equilibrio de usuario, en su enunciado formal —Boyles, Lownes &
    Unnikrishnan, "Transportation Network Analysis", Corollary 4.1, p. 89— dice:

        Every used route connecting an origin and destination has equal and
        minimal travel time.

    y aclara explícitamente que rutas usadas de pares origen-destino DISTINTOS
    pueden tener tiempos distintos. Acá cada celda es un origen distinto y cada
    estrato una clase de usuario distinta, así que la condición no dice nada
    sobre el agregado. Medido con `scripts/auditoria_wardrop.py` sobre la base
    default (942 grupos, 29.002 agentes):

      * el costo generalizado del modo elegido tiene desviación estándar de
        15,3 min entre grupos, sobre una media de 34,6 — y pasar de logit a
        determinístico apenas la mueve (15,7 -> 15,3);
      * los cuatro modos están usados a la vez con costos que difieren hasta
        32 min (caminata 12,1 · auto 25,0 · bici 37,6 · metro 44,3);
      * el 91% de los agentes está a más de 0,5 min de la indiferencia.

    Ese último número es el que explica el resto: como cada grupo pone toda su
    masa en un solo modo, la condición se satisface AL VACÍO — un par OD con una
    sola alternativa usada la cumple trivialmente (el caso `h1 = 0` de la p. 92
    del mismo libro). El reparto modal interior que se ve en el agregado es
    COMPOSICIÓN entre grupos heterogéneos, no arbitraje.

    Qué sí cambia respecto de `probabilidades_logit`, y decide resultados: el
    grupo marginal salta ENTERO al cruzar su umbral de indiferencia, en vez de
    trasvasar una fracción. Por eso una mejora vial puede disiparse — no porque
    alguien arbitre hasta igualar costos, sino porque los grupos que estaban
    cerca del margen se mudan de golpe (docs/CONTINUAR.md §5).

    Empates: se reparte en partes iguales entre los modos empatados. Sin eso, un
    desempate arbitrario por orden de diccionario introduciría un sesgo estable
    entre iteraciones. El libro admite este grado de libertad: "whenever there is
    a tie between shortest paths, you are free to choose among them" (p. 162).
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
