"""Solver de equilibrio de uso de suelo — subasta logit sobre la puja.

Portado de `titirilquen-repo/Ciudad2.py:249-479`. La matemática se preserva
verbatim; se cambian sólo los interfaces para devolver un dataclass tipado.

Operador de punto fijo sobre el vector de utilidades promedio `ū ∈ R^H`:

    F(ū)_h = (1/β) · log Σ_i  S_i · e^{β·s_hi} / ( Σ_g H_g · e^{β(s_gi − ū_g)} )

donde `s_hi = y_h + f_h(i)/λ_h` es la puja del estrato h por la parcela i y
f_h(i) = −α_h·T(i) − ρ_h·dens(i) la atractividad. El peso H_g aparece SOLO en el
denominador (la subasta la disputan H_g postores de cada tipo; ver la
ponderación de `Q`).

**Limitación (D-08): `λ` no está identificado.** β es uniforme sobre las pujas y
`f` es lineal en alpha y rho, así que dividir por `λ_h` es **idéntico** a
re-escalar `(alpha_h, rho_h)` por `1/λ_h`, y de paso escala el ruido a
`1/(β·λ_h)`. Mover λ no es un efecto-ingreso: es re-parametrizar preferencias y
ruido a la vez. Hay que leerlo como una limitación del modelo. **No hay
corrección implementada** — ver el docstring de `solve_logit`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.special import logsumexp


@dataclass(frozen=True)
class LandUseResult:
    """Resultado del equilibrio de uso de suelo."""

    u: NDArray[np.float64]
    """Utilidades normalizadas por estrato — ū ∈ R^H. u[0]=0 (normalización)."""

    p: NDArray[np.float64]
    """Precios implícitos por parcela — p ∈ R^I (salvo constante).

    El score es la puja `y + f/λ` en $ (WTP), así que p está en $. Solo el
    *gradiente* espacial es informativo: el nivel queda determinado salvo una
    constante."""

    Q: NDArray[np.float64]
    """Matriz de probabilidades de subasta Q[h, i] — columnas suman 1.

    Ponderada por el tamaño del estrato (Suelo.tex ec. 3):
    `Q[h,i] = H_h·e^{β(s_hi − ū_h)} / Σ_g H_g·e^{β(s_gi − ū_g)}` — más postores
    de un tipo ⇒ más probable que ganen la parcela. En el equilibrio conserva
    los hogares por estrato: `Σ_i S_i·Q[h,i] = H_h` (ver D-25)."""

    converged: bool
    iterations: int


def _f(
    T: NDArray[np.float64],
    S: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
    ancho_celda_km: float = 1.0,
) -> NDArray[np.float64]:
    """Atractividad de la parcela f_h(i) = -α_h·T(i) - ρ_h·dens(i).

    **Unidades físicas (D-26)**: `T` en minutos y la densidad `dens = S/Δx` en
    hogares/km — NO la capacidad por celda. Así el equilibrio es invariante a
    la resolución de la grilla: refinarla no cambia ni T(x) ni dens(x), solo
    los muestrea más fino. Con `ancho_celda_km=1` (default) dens = S, lo que
    reproduce el comportamiento previo (útil para tests con unidades
    arbitrarias)."""
    dens = S[None, :] / ancho_celda_km
    return -alpha[:, None] * T - rho[:, None] * dens


def _f_div_lambda(
    T: NDArray[np.float64],
    S: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
    lambda_h: NDArray[np.float64],
    ancho_celda_km: float = 1.0,
) -> NDArray[np.float64]:
    """f_h(i) / λ_h."""
    return _f(T, S, alpha, rho, ancho_celda_km) / lambda_h[:, None]


def _solve_fixed_point(
    score: NDArray[np.float64],
    H_arr: NDArray[np.float64],
    S_arr: NDArray[np.float64],
    beta: float,
    tol: float,
    max_iter: int,
) -> LandUseResult:
    """Punto fijo de subasta logit sobre el `score[h, i]` (la puja de cada estrato
    por cada parcela, en las unidades que defina el solver):

        Q[h,i] ∝ S_i·exp(β·(score_hi − ū_h − p_i)),   columnas de Q suman 1.

    Equilibrio: cada estrato coloca exactamente H_h hogares, vía el punto fijo
    F(ū)=ū sobre las utilidades ū. `β` es **escalar** (uniforme entre estratos):
    una escala por estrato `β_h` requeriría cambiar este solver, no solo el
    `score` — ver la limitación de λ en `solve_logit`."""
    I = len(S_arr)
    n_strata = len(H_arr)

    mask_S_pos = S_arr > 0
    log_S = np.full(I, -np.inf, dtype=float)
    log_S[mask_S_pos] = np.log(S_arr[mask_S_pos])

    logZ = np.log(H_arr)[:, None] + beta * score
    assert logZ.shape == (n_strata, I)

    def F(u_bar: NDArray[np.float64]) -> NDArray[np.float64]:
        log_denom = logsumexp(logZ - beta * u_bar[:, None], axis=0)
        log_num = beta * score - log_denom[None, :] + log_S[None, :]
        u_new = (1 / beta) * logsumexp(log_num, axis=1)
        u_new -= u_new[0]
        return u_new

    u_bar = np.zeros(n_strata)
    converged = False
    iterations = max_iter

    for it in range(max_iter):
        u_new = F(u_bar)
        if np.linalg.norm(u_new - u_bar) < tol:
            converged = True
            iterations = it
            u_bar = u_new
            break
        u_bar = u_new

    log_p = logsumexp(
        np.log(H_arr)[:, None] + beta * (score - u_bar[:, None]),
        axis=0,
    )
    p = log_p / beta

    # Q ponderado por H (Suelo.tex ec. 3): la subasta la disputan H_h postores
    # de cada tipo, así que P(gana h) ∝ H_h·e^{β(s_hi − ū_h)}. Sin el log(H) la
    # composición no conserva los hogares por estrato (Σ_i S_i·Q_hi ≠ H_h) en
    # cuanto H es heterogéneo — ver D-25. (El término −p_i es constante por
    # columna; se deja por estabilidad numérica y la normalización hace el resto.)
    log_H = np.log(H_arr)
    Q = np.zeros((n_strata, I))
    for i in range(I):
        if not mask_S_pos[i]:
            continue
        log_q = log_H + beta * (score[:, i] - u_bar - p[i])
        Q[:, i] = np.exp(log_q - logsumexp(log_q))

    return LandUseResult(u=u_bar, p=p, Q=Q, converged=converged, iterations=iterations)


def solve_logit(
    *,
    H: NDArray[np.int_],
    S: NDArray[np.int_],
    y: NDArray[np.float64],
    T: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
    lambda_h: NDArray[np.float64],
    beta: float = 1.0,
    tol: float = 1e-8,
    max_iter: int = 10000,
    ancho_celda_km: float = 1.0,
) -> LandUseResult:
    """Equilibrio vía punto fijo logit (ec. 5.4 Martínez). Puja `y_h + f_h(i)/λ_h`.

    Único solver del módulo. `T` en minutos; `ancho_celda_km` convierte S a
    densidad (ver D-26).

    **Limitación conocida (D-08).** Aplica un β **uniforme** a las pujas, así
    que `λ_h` entra dividiendo `f_h` entero. Consecuencia exacta:

        y_h + f_h(i)/λ_h  ==  y_h + f(i; alpha_h/λ_h, rho_h/λ_h)

    o sea **mover `λ_h` es idénticamente re-escalar `(alpha_h, rho_h)` por
    `1/λ_h`**
    —verificado: Q coincide dígito a dígito— y, a la vez, escalar el ruido de
    elección de ese estrato a `1/(β·λ_h)`. Las tres cosas se mueven juntas y no
    se pueden separar, así que `λ` no es un parámetro económico independiente:
    es una re-parametrización redundante de las preferencias.

    El efecto **no es un efecto-ingreso**: el ingreso `y` entra como constante
    por estrato, se absorbe en la utilidad de equilibrio ū_h y no reasigna a
    nadie. Y no es suave: bajar `λ` amplifica `rho_eff = rho/λ`, que castiga
    justamente las celdas centrales (las densas), de modo que el estrato de
    alpha más alto **huye del centro** — en la base el salto ocurre entre
    λ ≈ 0.8 y λ ≈ 0.95. Es una limitación del modelo implementado y debe leerse
    como tal; ver `scripts/auditoria_suelo.py` §4 y docs/AUDITORIA_USO_SUELO.md
    (AU-06).

    **No hay corrección implementada.** Hubo un segundo solver que decía
    corregirlo y no lo hacía: metía `λ` solo como `λ_h·y_h`, una constante por
    estrato que el punto fijo absorbe, dejando `λ` completamente inerte (Q
    idéntica con λ de 0.01 a 100). No corregía el artefacto: lo borraba. Se
    eliminó por eso. Cualquier corrección futura tendría que escalar el ruido
    por estrato, lo que exige cambiar este solver —`_solve_fixed_point` toma un
    β escalar—, no solo el `score`.
    """
    H_arr = np.asarray(H, dtype=float)
    S_arr = np.asarray(S, dtype=float).reshape(-1)
    score = y[:, None] + _f_div_lambda(T, S_arr, alpha, rho, lambda_h, ancho_celda_km)
    return _solve_fixed_point(score, H_arr, S_arr, beta, tol, max_iter)
