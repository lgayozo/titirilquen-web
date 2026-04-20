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


def _f_div_lambda(
    T: NDArray[np.float64],
    S: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
    lambda_h: NDArray[np.float64],
) -> NDArray[np.float64]:
    """f_h(i) / λ_h donde f_h(i) = -α_h·T(i) - ρ_h·S(i)."""
    return (-alpha[:, None] * T - rho[:, None] * S[None, :]) / lambda_h[:, None]


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
    """Resolver el equilibrio vía iteración de punto fijo logit (ec. 5.4 Martínez)."""
    H_arr = np.asarray(H, dtype=float)
    S_arr = np.asarray(S, dtype=float).reshape(-1)
    I = len(S_arr)
    n_strata = len(H_arr)

    f_dl = _f_div_lambda(T, S_arr, alpha, rho, lambda_h)

    mask_S_pos = S_arr > 0
    log_S = np.full(I, -np.inf, dtype=float)
    log_S[mask_S_pos] = np.log(S_arr[mask_S_pos])

    logZ = np.log(H_arr)[:, None] + beta * (y[:, None] + f_dl)
    assert logZ.shape == (n_strata, I)

    def F(u_bar: NDArray[np.float64]) -> NDArray[np.float64]:
        log_denom = logsumexp(logZ - beta * u_bar[:, None], axis=0)
        log_num = beta * (y[:, None] + f_dl) - log_denom[None, :] + log_S[None, :]
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
        np.log(H_arr)[:, None] + beta * (y[:, None] - u_bar[:, None] + f_dl),
        axis=0,
    )
    p = log_p / beta

    Q = np.zeros((n_strata, I))
    for i in range(I):
        if not mask_S_pos[i]:
            continue
        log_q = np.log(S_arr[i]) + beta * (y + f_dl[:, i] - u_bar - p[i])
        Q[:, i] = np.exp(log_q - logsumexp(log_q))

    return LandUseResult(u=u_bar, p=p, Q=Q, converged=converged, iterations=iterations)


def solve_frechet(
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
    """Variante Frechét (marcada "MALA" en el código original).

    Útil didácticamente: permite mostrar empíricamente la divergencia cuando
    los λ_h no son uniformes.
    """
    H_arr = np.asarray(H, dtype=float)
    S_arr = np.asarray(S, dtype=float).reshape(-1)
    I = len(S_arr)
    n_strata = len(H_arr)

    f_dl = _f_div_lambda(T, S_arr, alpha, rho, lambda_h)
    logw = y[:, None] + f_dl
    logZ = np.log(H_arr)[:, None] + beta * logw

    mask_S_pos = S_arr > 0
    log_S = np.full(I, -np.inf, dtype=float)
    log_S[mask_S_pos] = np.log(S_arr[mask_S_pos])

    def F(u_bar: NDArray[np.float64]) -> NDArray[np.float64]:
        log_denom = logsumexp(logZ - beta * u_bar[:, None], axis=0)
        log_num = log_S[None, :] + beta * logw - log_denom[None, :]
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

    log_p = logsumexp(np.log(H_arr)[:, None] + beta * (logw - u_bar[:, None]), axis=0)
    p = log_p / beta

    Q = np.zeros((n_strata, I))
    for i in range(I):
        if not mask_S_pos[i]:
            continue
        log_q = np.log(S_arr[i]) + beta * (logw[:, i] - u_bar - p[i])
        Q[:, i] = np.exp(log_q - logsumexp(log_q))

    return LandUseResult(u=u_bar, p=p, Q=Q, converged=converged, iterations=iterations)
