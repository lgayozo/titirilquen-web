"""La subasta heteroscedástica, reimplementada desde cero para este caso.

No importa nada del núcleo a propósito: si el demo usara `titirilquen_core`
demostraría que el núcleo es consistente consigo mismo, que no prueba nada. Acá
se reescribe la matemática desde el papel y en `pasos.py` se contrasta contra el
núcleo como verificación independiente.

Referencia: Train (2009) §4.5, siguiendo a Bhat (1995), y Martínez (2018) ecs.
(4.26), (5.1) y (5.8).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from caso import Caso

# --------------------------------------------------------------------------- #
# La cuadratura                                                                #
# --------------------------------------------------------------------------- #

#: Mismas constantes que `titirilquen_core/land_use/hev.py`, para que el
#: contraste del paso 6 mida el modelo y no una diferencia de discretización.
W_MIN, W_MAX, N_NODOS = -10.0, 40.0, 401
_W = np.linspace(W_MIN, W_MAX, N_NODOS)
_PESO = np.exp(-np.exp(-_W)) * np.exp(-_W) * (_W[1] - _W[0])
_PESO[0] *= 0.5
_PESO[-1] *= 0.5
_TOPE = 40.0


def q_hev(loc: NDArray[np.float64], theta: NDArray[np.float64]) -> NDArray[np.float64]:
    """Probabilidad de que cada estrato gane cada parcela. `(2, 5)`

    Condicionando en el ruido `w` del candidato, gana si todos los demás quedan
    por debajo; eso es un producto de CDFs. Se promedia sobre `w` contra la
    densidad de valor extremo, que es la integral que resuelve la cuadratura.
    """
    n_estratos, n_parcelas = loc.shape
    acum = np.zeros((n_estratos, n_parcelas))
    for h in range(n_estratos):
        z = np.ones((N_NODOS, n_parcelas))
        for g in range(n_estratos):
            if g == h:
                continue
            arg = (loc[h] - loc[g])[None, :] + theta[h] * _W[:, None]
            np.multiply(z, np.exp(-np.exp(-np.clip(arg / theta[g], -_TOPE, _TOPE))), out=z)
        acum[h] = _PESO @ z
    total = acum.sum(axis=0)
    return acum / np.where(total > 0, total, 1.0)


def q_logit(loc: NDArray[np.float64], theta: NDArray[np.float64]) -> NDArray[np.float64]:
    """La forma cerrada, válida sólo si los `θ` son iguales. `(2, 5)`

    Se usa para el contraste del paso 6: donde vale, tiene que coincidir con
    `q_hev` hasta el último bit.
    """
    z = loc / theta[0]
    z = z - z.max(axis=0, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=0, keepdims=True)


def precio(loc: NDArray[np.float64], theta: NDArray[np.float64]) -> NDArray[np.float64]:
    """Precio de cada parcela: el máximo esperado de las pujas. `(5,)`

    Ec. (5.8) de Martínez. Sin forma cerrada para el máximo, se integra
    `E[X] = Σ w·dF` sobre la CDF del máximo, que es el producto de las CDFs.
    """
    esc = float(theta.max())
    w = np.linspace(float(loc.min()) - 14.0 * esc, float(loc.max()) + 34.0 * esc, 4001)
    cdf = np.ones((len(w), loc.shape[1]))
    for g in range(loc.shape[0]):
        arg = (w[:, None] - loc[g][None, :]) / theta[g]
        np.multiply(cdf, np.exp(-np.exp(-np.clip(arg, -_TOPE, _TOPE))), out=cdf)
    w_medio = 0.5 * (w[:-1] + w[1:])
    return w_medio @ np.diff(cdf, axis=0)


# --------------------------------------------------------------------------- #
# La condición de equilibrio                                                   #
# --------------------------------------------------------------------------- #


def localizacion(caso: Caso, u: NDArray[np.float64]) -> NDArray[np.float64]:
    """`loc_hi = w_hi − ū_h + θ_h·ln(H_h)`. `(2, 5)`

    El tercer término es el corrimiento por el número de postores: el máximo de
    `H_h` Gumbel i.i.d. de escala `θ_h` es Gumbel con la localización corrida en
    `θ_h·ln(H_h)`. Con θ común reproduce el peso `H_h` de la ec. (4.26).
    """
    return caso.score() - u[:, None] + (caso.theta() * np.log(caso.H))[:, None]


def colocados(caso: Caso, u: NDArray[np.float64]) -> NDArray[np.float64]:
    """Hogares que cada estrato coloca con esas utilidades, `Σ_i S_i·Q_{h/i}`. `(2,)`"""
    return q_hev(localizacion(caso, u), caso.theta()) @ caso.S


def exceso(caso: Caso, delta: float) -> float:
    """La ÚNICA ecuación del problema, en función de la ÚNICA incógnita.

    Con dos estratos, `ū` tiene dos componentes pero el modelo la determina sólo
    salvo una constante aditiva, así que se fija `ū_Alto = 0` y queda un solo
    número libre, `delta = ū_Bajo`. Y de las dos condiciones de equilibrio sólo
    una es independiente: sumarlas da `ΣS = ΣH`, que es una condición sobre los
    datos y no sobre `ū`.

    Queda entonces una función escalar cuya raíz es el equilibrio. Es monótona
    creciente: subir `ū_Bajo` baja la puja del estrato bajo, así que el alto gana
    más parcelas.
    """
    return float(colocados(caso, np.array([0.0, delta]))[0] - caso.H[0])


# --------------------------------------------------------------------------- #
# Los dos solvers                                                              #
# --------------------------------------------------------------------------- #


@dataclass
class Traza:
    """Todo lo que pasó en cada iteración, para poder dibujarlo."""

    delta: list[float] = field(default_factory=list)
    exceso: list[float] = field(default_factory=list)
    paso: list[float] = field(default_factory=list)
    convergio: bool = False
    iteraciones: int = 0


def resuelve_balanceo(caso: Caso, tol: float = 1e-10, max_iter: int = 200) -> Traza:
    """El algoritmo del núcleo: balanceo multiplicativo sobre la ec. (5.1).

        ū_h ← ū_h + θ_h · ln( colocados_h / H_h )

    Si un estrato coloca de más, su `ū` sube, su puja baja y coloca menos. El
    logaritmo es lo que hace que el paso sea del tamaño correcto en vez de una
    constante arbitraria: en el caso homoscedástico este esquema es EXACTAMENTE
    el punto fijo de la forma cerrada, escrito de una manera que no necesita
    despejar `ū` de adentro del logaritmo.

    Arranca de `ū = 0`. El núcleo, en cambio, arranca del equilibrio cerrado,
    porque con ingresos de millones las pujas difieren en 10⁶ y `Q` satura en
    `[1, 0]`: el balanceo se queda sin dirección. Acá los números son chicos y no
    hace falta — lo que también muestra que el warm start es una necesidad
    numérica, no parte del modelo.
    """
    tr = Traza()
    u = np.zeros(2)
    tr.iteraciones = max_iter
    for it in range(max_iter):
        tr.delta.append(float(u[1]))
        tr.exceso.append(exceso(caso, float(u[1])))
        col = colocados(caso, u)
        paso = np.where(col > 0, caso.theta() * np.log(np.maximum(col, 1e-300) / caso.H), 0.0)
        u_new = u + paso
        u_new -= u_new[0]
        tr.paso.append(float(u_new[1] - u[1]))
        d = float(np.linalg.norm(u_new - u))
        u = u_new
        if d < tol:
            tr.convergio = True
            tr.iteraciones = it + 1
            tr.delta.append(float(u[1]))
            tr.exceso.append(exceso(caso, float(u[1])))
            break
    return tr


def resuelve_brent(caso: Caso, ancho: float = 30.0) -> tuple[float, int]:
    """Bisección sobre la función de exceso: un algoritmo sin nada en común.

    No usa el gradiente, ni la estructura del modelo, ni el logaritmo del paso;
    sólo que `exceso` cambia de signo. Que llegue al mismo número que el
    balanceo es la verificación de que ese número es el equilibrio y no un punto
    fijo espurio del esquema iterativo.

    Se implementa a mano —bisección pura— para no depender de scipy y para que
    se vea que no hay ningún truco adentro.
    """
    lo, hi = -ancho, ancho
    f_lo = exceso(caso, lo)
    if f_lo * exceso(caso, hi) > 0:
        raise ValueError("la funcion de exceso no cambia de signo en el intervalo")
    n = 0
    while hi - lo > 1e-14:
        med = 0.5 * (lo + hi)
        if exceso(caso, med) * f_lo > 0:
            lo = med
        else:
            hi = med
        n += 1
    return 0.5 * (lo + hi), n


def equilibrio(caso: Caso, delta: float) -> tuple[NDArray, NDArray, NDArray]:
    """`(Q, colocados, precios)` en el `delta` dado."""
    u = np.array([0.0, delta])
    loc = localizacion(caso, u)
    Q = q_hev(loc, caso.theta())
    return Q, Q @ caso.S, precio(loc, caso.theta())
