"""Solver de equilibrio de uso de suelo — subasta logit sobre la puja.

Portado de `titirilquen-repo/Ciudad2.py:249-479`. La matemática se preserva
verbatim; se cambian sólo los interfaces para devolver un dataclass tipado.

Operador de punto fijo sobre el vector de utilidades de reserva `u ∈ R^H`:

    F(u)_h = (1/β) · log Σ_i  S_i · e^{β·s_hi} / ( Σ_g H_g · e^{β(s_gi − u_g)} )

donde `s_hi = y_h + f_h(z_i)/λ_h` es la puja del estrato h por la parcela i y
f_h(z_i) = −α_h·T_h(i) − ρ_h·dens(i) la atractividad. El peso H_g aparece SOLO
en el denominador (la subasta la disputan H_g postores de cada tipo; ver la
ponderación de `Q`).

**Notación: la de Martínez (2018, §4.3–4.6), sin cambios de letra.**

* `μ` (`mu`): precisión del ruido de la UTILIDAD, el `μ_h` de la ec. (4.2),
  `ε_hi ~ Gumbel(0, μ_h)`. Aquí común a los estratos.
* `β_h = λ_h·μ_h`: precisión del ruido de la PUJA, en dinero, ec. (4.3). Es la
  que ve la subasta. En la forma cerrada (4.25)–(4.27) Martínez la indexa por
  localización, `β_i`, común a los postores de una parcela; aquí es además
  común a toda la ciudad (`beta_i`, un escalar).
* `θ` (`theta`) en la rama HEV: la ESCALA de Train (2009, §4.5), `θ_h = 1/β_h`.
  Ojo: en Martínez `θ_hi` es otra cosa, la puja aleatoria de (4.3); aquí `theta`
  sigue a Train porque implementa su integral.

Hasta sep-2026 la configuración llamaba `beta` a `μ` y el código usaba `b`
para `β`: las letras corridas un lugar respecto de Martínez (D-31).

**Limitación (D-08): `λ` no está identificado en la forma cerrada.** β es
uniforme sobre las pujas y `f` es lineal en alpha y rho, así que dividir por
`λ_h` es **idéntico** a re-escalar `(alpha_h, rho_h)` por `1/λ_h`, y de paso
escala el ruido a `1/(μ·λ_h)`. Mover λ no es un efecto-ingreso: es
re-parametrizar preferencias y ruido a la vez. La corrección es la rama HEV;
ver los docstrings de `solve_logit` y `solve_subasta`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.special import logsumexp

from titirilquen_core.land_use.hev import e_max_hev, q_hev


@dataclass(frozen=True)
class LandUseResult:
    """Resultado del equilibrio de uso de suelo."""

    u: NDArray[np.float64]
    """Utilidades normalizadas por estrato — ū ∈ R^H. u[0]=0 (normalización)."""

    p: NDArray[np.float64]
    """Precio esperado por parcela, el `p*_i` de Martínez (4.27): el máximo
    esperado de las pujas, en $, salvo constante.

    Las dos ramas devuelven la MISMA cantidad. La cerrada calcula la moda del
    máximo, `p_i = (1/β)·ln Σ H_h e^{β w_hi}`, y le suma `γ/β` (constante de
    Euler); la HEV integra el máximo esperado directamente (`e_max_hev`).
    Hasta sep-2026 la cerrada devolvía sólo la moda, y el nivel de precios
    saltaba `γ/β` al pasar de una rama a la otra. Solo el *gradiente* espacial
    es informativo: el nivel depende de la normalización `u[0] = 0`."""

    Q: NDArray[np.float64]
    """Matriz de probabilidades de subasta Q[h, i] — columnas suman 1.

    Ponderada por el tamaño del estrato (Martínez 4.26):
    `Q[h,i] = H_h·e^{β(s_hi − u_h)} / Σ_g H_g·e^{β(s_gi − u_g)}` — más postores
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
    arbitrarias).

    **`dens` es EXÓGENA (D-32).** Es la oferta `S`, generada una vez, no la
    población resultante — y como el mercado se vacía (columnas de `Q` que suman
    1, `Σ S = Σ H`), la densidad realizada es idénticamente `S/Δx`: el
    equilibrio decide *quién* vive en cada celda, nunca *cuántos*. Además esta
    función se evalúa una sola vez, antes del punto fijo. Así que `ρ·dens` NO
    modela congestión residencial: ningún hogar puede mover la magnitud por la
    que se lo penaliza. No hay externalidad de localización en el sentido de
    Martínez, donde la atractividad es endógena y genera cascadas.

    Consecuencia práctica (AU-12): `dens` es una función fija de la parcela y,
    en las formas monocéntricas, casi proporcional a `T` —`corr = −0,996` con la
    forma `normal`—, de modo que `f ≈ −(α − ρ·b)·T + cte`: la localización
    identifica sobre todo esa combinación, no `alpha` y `rho` por separado.

    Ojo con la fuerza de esa afirmación: `corr = −0,996` es varianza explicada,
    no equivalencia de efecto. Medido (`sandbox/impacto-rho`, E3), construir el
    equivalente `α' = α − b·ρ` reproduce el **70,5 %** del efecto de una `rho`
    heterogénea en `normal`, no el 99,6 %: al residuo le queda ~30 % porque la
    subasta amplifica diferencias chicas (AU-10). En `valle`, donde la
    colinealidad es exacta, sí reproduce el 99,3 %; en `bimodal` y `meseta` el
    equivalente no sirve."""
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
    beta_i: float,
    tol: float,
    max_iter: int,
) -> LandUseResult:
    """Punto fijo de subasta logit sobre el `score[h, i]` (la puja de cada estrato
    por cada parcela, **en dinero**):

        Q[h,i] ∝ S_i·exp(β·(score_hi − u_h − p_i)),   columnas de Q suman 1.

    `beta_i` es la **precisión en dinero** del ruido de la puja: el `β_i` de
    las ecs. (4.25)–(4.27) de Martínez (pp. 85–86), que en (4.3) es
    `β_h = λ_h·μ_h`. No es el `mu` de la configuración —la precisión en
    útiles— y la conversión la hace el que llama. Confundirlos hacía saltar el
    despacho de `solve_subasta` al pasar de λ uniforme a λ heterogéneo (ver ahí).

    Es **escalar**, o sea uniforme entre estratos: una precisión por estrato
    `β_h` requeriría cambiar este solver, no sólo el `score`, y es exactamente
    lo que hace el HEV (`hev.py`).

    Equilibrio: cada estrato coloca exactamente H_h hogares, vía el punto fijo
    F(ū)=ū sobre las utilidades ū."""
    I = len(S_arr)
    n_strata = len(H_arr)

    mask_S_pos = S_arr > 0
    log_S = np.full(I, -np.inf, dtype=float)
    log_S[mask_S_pos] = np.log(S_arr[mask_S_pos])

    logZ = np.log(H_arr)[:, None] + beta_i * score
    assert logZ.shape == (n_strata, I)

    def F(u_bar: NDArray[np.float64]) -> NDArray[np.float64]:
        log_denom = logsumexp(logZ - beta_i * u_bar[:, None], axis=0)
        log_num = beta_i * score - log_denom[None, :] + log_S[None, :]
        u_new = (1 / beta_i) * logsumexp(log_num, axis=1)
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

    # Moda del precio, `p_i` de (4.27): la localización del máximo de las pujas.
    log_p = logsumexp(
        np.log(H_arr)[:, None] + beta_i * (score - u_bar[:, None]),
        axis=0,
    )
    p = log_p / beta_i

    # Q ponderado por H (Suelo.tex ec. 3): la subasta la disputan H_h postores
    # de cada tipo, así que P(gana h) ∝ H_h·e^{β(s_hi − u_h)}. Sin el log(H) la
    # composición no conserva los hogares por estrato (Σ_i S_i·Q_hi ≠ H_h) en
    # cuanto H es heterogéneo — ver D-25. (El término −p_i es constante por
    # columna; se deja por estabilidad numérica y la normalización hace el resto.)
    log_H = np.log(H_arr)
    Q = np.zeros((n_strata, I))
    for i in range(I):
        if not mask_S_pos[i]:
            continue
        log_q = log_H + beta_i * (score[:, i] - u_bar - p[i])
        Q[:, i] = np.exp(log_q - logsumexp(log_q))

    # Precio esperado, `p*_i = p_i + γ/β_i` (4.27): la misma cantidad que
    # devuelve la rama HEV (`e_max_hev`), para que el nivel no salte entre ramas.
    p_esperado = p + np.euler_gamma / beta_i
    return LandUseResult(u=u_bar, p=p_esperado, Q=Q, converged=converged, iterations=iterations)


def solve_logit(
    *,
    H: NDArray[np.int_],
    S: NDArray[np.int_],
    y: NDArray[np.float64],
    T: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
    lambda_h: NDArray[np.float64],
    beta_i: float = 1.0,
    tol: float = 1e-8,
    max_iter: int = 10000,
    ancho_celda_km: float = 1.0,
) -> LandUseResult:
    """Equilibrio vía punto fijo logit (ec. 5.4 Martínez). Puja `y_h + f_h(i)/λ_h`.

    `T` en minutos; `ancho_celda_km` convierte S a densidad (ver D-26).

    **Recibe `beta_i`, no `mu`.** Es la precisión en dinero de la puja, el `β_i`
    de Martínez (4.25), y se aplica tal cual. `solve_subasta` —la puerta que usa
    la app— recibe `mu` y hace la conversión `β_h = λ_h·μ`. Se deja así a
    propósito: es la referencia homoscedástica pura con la que se demuestra
    D-08, y meterle λ rompería justamente la identidad que D-08 exhibe. Para
    comparar contra `solve_subasta` hay que pasarle `beta_i = μ·λ`.

    **Limitación conocida (D-08).** Aplica un β **uniforme** a las pujas, así
    que `λ_h` entra dividiendo `f_h` entero. Consecuencia exacta:

        y_h + f_h(i)/λ_h  ==  y_h + f(i; alpha_h/λ_h, rho_h/λ_h)

    o sea **mover `λ_h` es idénticamente re-escalar `(alpha_h, rho_h)` por
    `1/λ_h`**
    —verificado: Q coincide dígito a dígito— y, a la vez, escalar el ruido de
    elección de ese estrato a `1/(μ·λ_h)`. Las tres cosas se mueven juntas y no
    se pueden separar, así que `λ` no es un parámetro económico independiente:
    es una re-parametrización redundante de las preferencias.

    El efecto **no es un efecto-ingreso**: el ingreso `y` entra como constante
    por estrato, se absorbe en la utilidad de equilibrio ū_h y no reasigna a
    nadie —verificado: triplicar `y` mueve `Q` en 8·10⁻¹⁰—. Lo que sí reasigna
    es `f_h/λ_h`, que **varía entre parcelas** y por eso ū no puede absorberlo.

    El canal dominante es `alpha_ef = alpha/λ`: subir el `λ` de un estrato achica
    cuánto valora el tiempo de viaje, deja de pujar por lo central y **se aleja**.
    Bajarlo lo acerca. Que el motor sea α y no ρ se comprueba anulando ρ: el
    patrón sobrevive y se refuerza.

    **Medir esto sólo tiene sentido con λ decreciente en el ingreso**, que es la
    condición realista (Martínez p. 77: «it is expected that λ_h decreases with
    income»): `λ_alto < λ_medio < λ_bajo`. En esa región la respuesta es suave y
    acotada — con `λ = (1/r, 1, r)`, d_alto va de 1,47 km en r = 1 a 1,05 km en
    r = 4, saturando:

        r        1      1,25     1,5      2       3       4
        d_alto   1,47   1,10     1,07    1,05    1,05    1,05

    Barrer `λ_alto` **por encima** de los otros da una transición mucho más
    violenta —hasta 6,25 km— pero es una configuración económicamente al revés y
    no debe leerse como el comportamiento del modelo. Ojo también con la
    documentación anterior a la recalibración de ρ (0,1 → 0,0025), que atribuía
    esto a `rho_ef` y daba la dirección invertida; ver AU-11 en
    docs/AUDITORIA_USO_SUELO.md.

    Es una limitación del modelo implementado y debe leerse como tal; ver
    `scripts/auditoria_suelo.py` §4 y docs/AUDITORIA_USO_SUELO.md (AU-06).

    **Corregido, pero no acá.** La corrección es la subasta heteroscedástica
    (`hev.py`), que sí escala el ruido por estrato y con eso identifica λ;
    `solve_subasta` la usa sola cuando los λ difieren. Esta función conserva la
    forma cerrada porque con λ uniformes es EXACTA y mucho más rápida.

    Hubo antes un segundo solver que decía corregirlo y no lo hacía: metía `λ`
    solo como `λ_h·y_h`, una constante por estrato que el punto fijo absorbe,
    dejando `λ` completamente inerte (Q idéntica con λ de 0.01 a 100). No
    corregía el artefacto: lo borraba. Se eliminó por eso.
    """
    H_arr = np.asarray(H, dtype=float)
    S_arr = np.asarray(S, dtype=float).reshape(-1)
    score = y[:, None] + _f_div_lambda(T, S_arr, alpha, rho, lambda_h, ancho_celda_km)
    return _solve_fixed_point(score, H_arr, S_arr, beta_i, tol, max_iter)


def _solve_hev(
    score: NDArray[np.float64],
    H_arr: NDArray[np.float64],
    S_arr: NDArray[np.float64],
    theta: NDArray[np.float64],
    tol: float,
    max_iter: int,
) -> LandUseResult:
    """Punto fijo de la subasta HETEROSCEDÁSTICA (ver `hev.py`).

    Sin forma cerrada para `Q` no se puede despejar `ū` dentro del logaritmo como
    hace `_solve_fixed_point`, así que se itera directamente sobre la condición
    de equilibrio de la ec. (5.1) —«todo hogar se localiza»—:

        Σ_i S_i · Q_h/i(u) = H_h

    con el balanceo

        u_h ← u_h + θ_h · ln( Σ_i S_i Q_h/i(u) / H_h )

    donde `θ_h = 1/β_h = 1/(λ_h·μ)` es la escala de Train (§4.5) del ruido de la
    puja del estrato h. Subir `u_h` baja la puja `w = score − u` y con ella `Q`,
    así que el signo reduce el exceso. **No es un esquema nuevo**: en el caso
    homoscedástico `θ_h = 1/β` y el álgebra da exactamente `u ← F(u)` de
    `_solve_fixed_point`
    —verificado en `test_hev_reduce_al_logit_cuando_lambda_es_uniforme`—, así que
    es la misma iteración escrita de una forma que no necesita la forma cerrada.

    **Arranca del equilibrio cerrado, no de cero.** Con ingresos de millones, en
    `u = 0` las pujas de los estratos difieren en ~2·10⁶ y `Q` satura en
    `[1, 0, 0]`: el balanceo pierde toda dirección y avanza a paso fijo hacia un
    objetivo que está seis órdenes de magnitud más lejos. La forma cerrada da en
    una corrida un `u` del orden correcto —es exacta si los λ son uniformes y una
    buena aproximación si no—, y desde ahí el HEV sólo corrige.
    """
    n_estratos = len(H_arr)
    con_oferta = S_arr > 0
    log_H = np.log(H_arr)

    # Warm start: el equilibrio homoscedástico con la precisión media, β = mean(1/θ).
    beta_medio = float(np.mean(1.0 / theta))
    u_bar = _solve_fixed_point(score, H_arr, S_arr, beta_medio, tol, max_iter).u
    converged = False
    iterations = max_iter
    Q = np.zeros((n_estratos, len(S_arr)))

    for it in range(max_iter):
        loc = score - u_bar[:, None] + (theta * log_H)[:, None]
        Q = q_hev(loc, theta)
        Q[:, ~con_oferta] = 0.0
        colocados = Q @ S_arr
        # Un estrato sin colocar a nadie no da información de dirección; se lo
        # deja quieto en vez de mandar `u` a −∞.
        paso = np.where(colocados > 0, theta * np.log(np.maximum(colocados, 1e-300) / H_arr), 0.0)
        u_new = u_bar + paso
        u_new -= u_new[0]
        delta = float(np.linalg.norm(u_new - u_bar))
        u_bar = u_new
        if delta < tol:
            converged = True
            iterations = it
            break

    loc = score - u_bar[:, None] + (theta * log_H)[:, None]
    Q = q_hev(loc, theta)
    Q[:, ~con_oferta] = 0.0
    p = e_max_hev(loc, theta)
    return LandUseResult(u=u_bar, p=p, Q=Q, converged=converged, iterations=iterations)


def solve_subasta(
    *,
    H: NDArray[np.int_],
    S: NDArray[np.int_],
    y: NDArray[np.float64],
    T: NDArray[np.float64],
    alpha: NDArray[np.float64],
    rho: NDArray[np.float64],
    lambda_h: NDArray[np.float64],
    mu: float = 1.0,
    tol: float = 1e-8,
    max_iter: int = 10000,
    ancho_celda_km: float = 1.0,
) -> LandUseResult:
    """Resuelve el equilibrio con el modelo de subasta que corresponda a los `λ`.

    Recibe `mu`, la precisión del ruido de la UTILIDAD (el `μ_h` de Martínez,
    común a los estratos). La subasta ve la precisión en dinero,
    `β_h = λ_h·μ`, ec. (4.3).

    **El despacho lo deciden los datos, no un campo de configuración.** Hubo un
    campo `solver` y se eliminó porque ofrecía elegir un método que decía
    corregir el artefacto de λ y no lo hacía (AU-07); reponerlo sería volver a
    poner al usuario a elegir entre un modelo válido y uno inválido:

    * `λ_h` todos iguales ⇒ las pujas son homoscedásticas y la forma cerrada de
      la ec. (4.26) es **exacta**. Se usa esa: es más rápida y no mete error de
      cuadratura en la línea base.
    * `λ_h` distintos ⇒ el ruido de la puja tiene escala `1/β_h = 1/(λ_h·μ)`, distinta
      por estrato, y la forma cerrada deja de ser válida. Se usa HEV.

    Así nunca se puede correr el modelo equivocado para la configuración dada.

    **El despacho es continuo, y no lo era.** Hasta el 2026-09-01 la rama
    cerrada recibía el parámetro de configuración crudo y la rama HEV
    `θ = 1/(μ·λ)`, o sea que cada una lo interpretaba en un espacio distinto: la
    cerrada como precisión en dinero (β), el HEV como precisión en útiles (μ).
    Con λ = 1 coinciden y no se notaba,
    pero con λ uniforme ≠ 1 hacer los λ infinitesimalmente heterogéneos movía la
    asignación de golpe —medido: 4,7 puntos con λ = 2, 8,9 con λ = 0,5—, que es
    el síntoma de estar resolviendo dos modelos distintos a cada lado del `if`.
    Ahora las dos ramas convierten igual, `β_h = λ_h·μ`, y el salto es cero;
    lo fija `test_el_despacho_no_salta_al_romper_la_uniformidad_de_lambda`.
    Desde sep-2026 las dos devuelven además el mismo precio, el esperado
    `p*_i` de (4.27) (ver `LandUseResult.p`).
    """
    H_arr = np.asarray(H, dtype=float)
    S_arr = np.asarray(S, dtype=float).reshape(-1)
    score = y[:, None] + _f_div_lambda(T, S_arr, alpha, rho, lambda_h, ancho_celda_km)
    lam = np.asarray(lambda_h, dtype=float)
    # `mu` es la precisión del ruido en ÚTILES (el μ_h de Martínez, común a los
    # estratos). La precisión en DINERO —la que ve la subasta, porque la puja
    # está en dinero— es `β_h = λ_h·μ`, ec. (4.3). La rama HEV recibe su
    # inverso, la escala de Train `θ_h = 1/β_h`. Las dos ramas tienen que hacer
    # la misma conversión o el despacho salta.
    if float(np.ptp(lam)) <= 0.0:
        return _solve_fixed_point(score, H_arr, S_arr, mu * float(lam[0]), tol, max_iter)
    return _solve_hev(score, H_arr, S_arr, 1.0 / (mu * lam), tol, max_iter)
