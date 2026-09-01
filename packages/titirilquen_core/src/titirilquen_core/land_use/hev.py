"""Subasta **heteroscedástica** (HEV) — Train (2009) §4.5, siguiendo a Bhat (1995).

El logit cerrado de `equilibrium.py` supone que todas las pujas de una parcela
tienen la **misma varianza**. Eso deja de ser cierto en cuanto los `λ_h` difieren
entre estratos: por la ec. (4.3) de Martínez, al despejar el precio para obtener
la disposición a pagar el término aleatorio queda dividido por `λ_h`,

    q_hi = y_h + (f_h(z_i) − u_h)/λ_h + ε_hi/λ_h

o sea Gumbel con parámetro de forma `b_h = λ_h·μ_h`, **distinto por estrato**
(Martínez, p. 77: `ε'_hi = ε_hi/λ_h` es Gumbel(0, b_h) con `b_h = λ_h·μ_h`).
Aplicar la forma cerrada ahí no es una aproximación: es otro modelo, y equivale a
suponer `b_h = b` común, o sea `μ_h = b/λ_h` —que quien más valora el dinero
tiene proporcionalmente menos dispersión idiosincrática de utilidad—, un supuesto
sin fundamento conductual que nadie eligió.

**Cuál es el `beta` de la configuración.** Es `μ`, la precisión del ruido en
**útiles**, común a los estratos; la precisión en **dinero** es `b_h = β·λ_h` y
es la que ve la subasta, porque la puja está en dinero. `solve_subasta` hace esa
conversión en las dos ramas. Antes no: la rama cerrada recibía `β` crudo, lo que
equivalía a fijar `b = β` en vez de `b = β·λ`, y hacía que el despacho saltara al
volver los λ infinitesimalmente heterogéneos (4,7 puntos con λ = 2). Con `λ = 1`
las dos lecturas coinciden, que es por qué la línea base nunca lo notó.

El modelo correcto para varianzas distintas entre alternativas es el **HEV**
(heteroskedastic extreme value). La probabilidad de que la alternativa `h` gane
es, en la forma de Bhat:

    Q_h = ∫ [ Π_{g≠h} exp(−exp(−(loc_h − loc_g + θ_h·w) / θ_g)) ]
            · exp(−exp(−w)) · exp(−w) dw

que **no tiene forma cerrada** —el máximo de Gumbel de escalas distintas no es
Gumbel—, pero cuya integral es de una sola dimensión y se resuelve bien por
cuadratura (Train, §4.5).

**Traducción a la subasta de suelo.** Las «alternativas» son los ESTRATOS que
pujan por una parcela, no las parcelas:

* `loc_h = w_hi + θ_h·ln(H_h)` — la puja determinística más el desplazamiento por
  el número de postores. El máximo de `H_h` Gumbel i.i.d. de escala `θ_h` es
  Gumbel con la localización corrida en `θ_h·ln(H_h)`; con `θ` común eso
  reproduce exactamente el peso `H_h` de la ec. (4.26) de Martínez.
* `θ_h = 1/(β·λ_h)` — la escala del ruido de la puja. Con los `λ_h` todos iguales
  da `θ_h = 1/β` para todos y el HEV **coincide con la forma cerrada**, que es la
  propiedad de reducción que fija `test_hev_reduce_al_logit_cuando_lambda_es_uniforme`.

**Por qué importa.** Bajo la forma cerrada, mover `λ_h` es *exactamente* lo mismo
que re-escalar `(α_h, ρ_h)` por `1/λ_h` (D-08): λ no es un parámetro
identificado. Bajo HEV esa identidad se rompe, porque λ mueve además la escala
del ruido, que es observable en `Q`. Recién acá λ significa algo.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

#: Grilla de cuadratura sobre `w`, con el peso de la densidad de valor extremo.
#:
#: La regla del trapecio sobre una grilla uniforme es la herramienta correcta
#: acá: el integrando es suave y decae exponencialmente en los dos extremos, que
#: es justo el caso en que el trapecio converge con precisión espectral. Se
#: probó Gauss-Laguerre —la sustitución `t = e^{−w}` lleva el peso exactamente a
#: `e^{−t}`— y converge MAL: el doble exponencial no se parece a un polinomio en
#: `t` (error 2·10⁻⁴ con 160 nodos contra 10⁻¹³ del trapecio con 801).
#:
#: Rango y nodos medidos: con `[-10, 40]` el truncamiento aporta menos de 10⁻¹⁶,
#: y **401 nodos** alcanzan precisión de máquina (2·10⁻¹⁶) en todo el rango de λ
#: que la aplicación admite. Se probó con 801 y no compra nada: el error ya está
#: en el redondeo. Importa porque esto corre dentro del punto fijo y también en
#: Pyodide, así que cada nodo se paga cientos de veces.
_W_MIN, _W_MAX, _N_NODOS = -10.0, 40.0, 401
_W = np.linspace(_W_MIN, _W_MAX, _N_NODOS)
#: `exp(−exp(−w))·exp(−w)·dw` — la densidad por el ancho del trapecio, con los
#: extremos a medio peso.
_PESO = np.exp(-np.exp(-_W)) * np.exp(-_W) * (_W[1] - _W[0])
_PESO[0] *= 0.5
_PESO[-1] *= 0.5

#: Tope del argumento antes de exponenciar. `exp(-exp(-x))` satura a 0 por
#: debajo de −40 y a 1 por encima; recortar evita `overflow` sin cambiar nada.
_TOPE = 40.0


def q_hev(
    loc: NDArray[np.float64],
    theta: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Probabilidad de ganar la subasta, por estrato y parcela.

    :param loc: `(n_estratos, n_parcelas)` — localización de la puja de cada
        estrato en cada parcela, con el desplazamiento por `H_h` ya incluido.
    :param theta: `(n_estratos,)` — escala del ruido de cada estrato.
    :returns: `(n_estratos, n_parcelas)`, columnas que suman 1.

    Se vectoriza sobre parcelas y nodos a la vez; el único bucle es sobre los
    pares de estratos, que son 3×3.
    """
    n_estratos, n_parcelas = loc.shape
    acum = np.zeros((n_estratos, n_parcelas))
    for h in range(n_estratos):
        # `z[k, i]` = producto sobre g≠h evaluado en el nodo k y la parcela i.
        z = np.ones((_N_NODOS, n_parcelas))
        for g in range(n_estratos):
            if g == h:
                continue
            arg = (loc[h] - loc[g])[None, :] + theta[h] * _W[:, None]
            np.multiply(z, np.exp(-np.exp(-np.clip(arg / theta[g], -_TOPE, _TOPE))), out=z)
        acum[h] = _PESO @ z
    total = acum.sum(axis=0)
    # Una parcela sin oferta no participa de ninguna subasta; la deja en 0 el
    # caller. Acá sólo se evita dividir por cero.
    np.divide(acum, np.where(total > 0, total, 1.0), out=acum)
    return acum


def e_max_hev(
    loc: NDArray[np.float64],
    theta: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Valor esperado del máximo de las pujas — el precio de la parcela.

    Es la ec. (4.27) de Martínez («the maximum bid in the auction represents the
    transaction price») cuando el máximo ya no es Gumbel y no hay forma cerrada.
    Se integra la CDF del máximo, `F(w) = Π_g exp(−exp(−(w−loc_g)/θ_g))`.

    Ojo con el nivel: esto es el máximo ESPERADO, mientras la rama cerrada
    devuelve el parámetro de localización, que es el esperado menos `γ/β`. Los
    dos difieren en una constante, y el precio de este modelo está definido
    justamente salvo una constante (la 4ª condición de equilibrio de Alonso, que
    la fijaría, no está implementada). No afecta ningún gradiente.
    """
    n_estratos, n_parcelas = loc.shape
    # Grilla propia: el soporte del máximo depende de dónde caigan las pujas.
    esc = float(theta.max())
    w = np.linspace(float(loc.min()) - 14.0 * esc, float(loc.max()) + 34.0 * esc, 4001)

    cdf = np.ones((len(w), n_parcelas))
    for g in range(n_estratos):
        arg = (w[:, None] - loc[g][None, :]) / theta[g]
        np.multiply(cdf, np.exp(-np.exp(-np.clip(arg, -_TOPE, _TOPE))), out=cdf)

    # `E[X] = Σ w·dF` sobre puntos medios. La forma `∫(1−F) − ∫F` partida en
    # w=0 parece más directa pero mete un error de orden `dw` en el punto de
    # corte, que acá vale ~10⁻² — visible contra el γ/β que debe reproducir.
    w_medio = 0.5 * (w[:-1] + w[1:])
    return w_medio @ np.diff(cdf, axis=0)
