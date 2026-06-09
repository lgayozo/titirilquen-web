"""Solvers de equilibrio — logit y Frechét.

Portados de `titirilquen-repo/Ciudad2.py:249-479`. La matemática se preserva
verbatim; se cambian sólo los interfaces para devolver un dataclass tipado.

Ambos solvers implementan el mismo operador de punto fijo sobre el vector de
utilidades promedio `ū ∈ R^H`:

    F(ū)_h = (1/β) log( Σ_i S_i · exp(βz_hi) / Σ_g exp(β(z_gi - ū_g)) )

donde z_hi = H_h · exp(β(y_h + f_h(i)/λ_h)) en la formulación logit.

Diferencia: la versión Frechét usa `log w_hi` directo en lugar de `z_hi`, lo
que introduce una inconsistencia si `λ_h` es heterogéneo (ver D-08 y
Suelo.tex sec. Notas).
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
    """Precios implícitos por parcela — p ∈ R^I (salvo constante)."""

    Q: NDArray[np.float64]
    """Matriz de probabilidades de subasta Q[h, i] — columnas suman 1."""

    converged: bool
    iterations: int


def _f(
    T: NDArray[np.float64],
    S: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Atractividad de la parcela f_h(i) = -α_h·T(i) - ρ_h·S(i)."""
    return -alpha[:, None] * T - rho[:, None] * S[None, :]


def _f_div_lambda(
    T: NDArray[np.float64],
    S: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
    lambda_h: NDArray[np.float64],
) -> NDArray[np.float64]:
    """f_h(i) / λ_h."""
    return _f(T, S, alpha, rho) / lambda_h[:, None]


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
    F(ū)=ū sobre las utilidades ū. `logit` usa `score = y + f/λ` (espacio de
    pujas); `heteroscedastic` usa `score = λ·y + f` (espacio de utilidad, escala
    por estrato β_h = β·λ_h). Coinciden cuando λ_h = 1 ∀h."""
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

    Q = np.zeros((n_strata, I))
    for i in range(I):
        if not mask_S_pos[i]:
            continue
        log_q = np.log(S_arr[i]) + beta * (score[:, i] - u_bar - p[i])
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
) -> LandUseResult:
    """Equilibrio vía punto fijo logit (ec. 5.4 Martínez). Puja `y_h + f_h(i)/λ_h`.

    Aplica un β **uniforme** a las pujas; con `λ_h` heterogéneo el ruido de la
    puja queda con escala `1/(β·λ_h)` por estrato → es **inconsistente** (ver
    D‑08). Se conserva para comparación didáctica con `solve_heteroscedastic`.
    """
    H_arr = np.asarray(H, dtype=float)
    S_arr = np.asarray(S, dtype=float).reshape(-1)
    score = y[:, None] + _f_div_lambda(T, S_arr, alpha, rho, lambda_h)
    return _solve_fixed_point(score, H_arr, S_arr, beta, tol, max_iter)


def solve_heteroscedastic(
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
) -> LandUseResult:
    """Equilibrio con **logit heteroscedástico** — la corrección del λ (ver D‑08).

    La utilidad es `U_hi = λ_h(y_h − p_i) + f_h(i) + ε_hi` con ε Gumbel de escala
    `1/β` (homoscedástica **en utilidad**). La puja (WTP) divide por λ_h, lo que
    en `solve_logit` deja el ruido con escala `1/(β·λ_h)` por estrato. La versión
    consistente usa una **escala por estrato `β_h = β·λ_h`**, equivalente a
    trabajar en el espacio de utilidad con `score = λ_h·y_h + f_h(i)` (sin dividir
    por λ). Propiedades (validadas): coincide con `solve_logit` cuando `λ_h = 1`;
    es **invariante a la escala común de λ** (a diferencia del logit); y separa
    la utilidad marginal del ingreso (λ_h) del ruido de elección (β).
    """
    H_arr = np.asarray(H, dtype=float)
    S_arr = np.asarray(S, dtype=float).reshape(-1)
    score = (lambda_h * y)[:, None] + _f(T, S_arr, alpha, rho)
    return _solve_fixed_point(score, H_arr, S_arr, beta, tol, max_iter)
