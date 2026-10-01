"""Aprendizaje por instancias (IBL) para el tiempo percibido de un modo.

Las dos ecuaciones del documento «IBL Leandro»:

    b_ni(t) = Σ_{t'=0}^{t-1} w_ni(t', t) · x_i(t')

    w_ni(t', t) = a_ni(t') · (t − t')^{−d} / Σ_{τ=0}^{t-1} a_ni(τ) · (t − τ)^{−d}

`b_ni(t)` es el tiempo que la persona `n` percibe para el modo `i` al decidir en
el día `t`; `x_i(t')` el tiempo que experimentó en `t'`; `a_ni(t') = 1` si ese
día eligió `i`; `d ≥ 0` la tasa de decaimiento (d = 0: promedio simple; d
grande: sólo cuenta lo reciente).

**Supuesto declarado — el prior.** Un modo nunca elegido tiene la suma vacía y
la fórmula da 0/0. Se resuelve tratando la información exógena del día 1 como
una instancia más: en `t' = 0` todos los modos tienen `a = 1` y `x` igual al
tiempo «de buena calidad sobre el promedio». Así el prior decae con `d` igual
que cualquier experiencia, y `b_ni(t)` queda definido siempre.

Todo es vectorizado sobre `(n personas, t' días, i modos)`; para una persona
sola las matrices tienen `n = 1`.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def pesos_ibl(a: NDArray[np.bool_], t: int, d: float) -> NDArray[np.float64]:
    """Pesos `w[n, t', i]` sobre los días `t' < t`, normalizados por (n, i).

    `a[n, t', i]` marca si la persona n eligió el modo i en t'. Las filas sin
    ninguna experiencia (Σ a = 0) devuelven peso cero — el llamador decide qué
    hacer; con el prior en t' = 0 nunca pasa.
    """
    if t < 1:
        raise ValueError("t debe ser ≥ 1: en t = 0 no hay pasado")
    a_t = a[:, :t, :].astype(float)
    antiguedad = (t - np.arange(t)).astype(float)  # t − t' ∈ {t, …, 1}
    decaido = a_t * antiguedad[None, :, None] ** (-d)
    suma = decaido.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.where(suma > 0, decaido / suma, 0.0)
    return w


def tiempo_percibido(
    x: NDArray[np.float64], a: NDArray[np.bool_], t: int, d: float
) -> NDArray[np.float64]:
    """`b[n, i]`: la mezcla IBL de los tiempos experimentados hasta `t − 1`.

    `x[n, t', i]` es el tiempo experimentado (sólo importa donde `a` es True).
    """
    w = pesos_ibl(a, t, d)
    return np.einsum("nti,nti->ni", w, x[:, :t, :])
