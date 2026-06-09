"""Generación de la oferta de suelo S[i] — capacidades por parcela.

Portado de `titirilquen-repo/Ciudad2.py:213-247`, extendido con varias **formas
de ciudad** (no solo la Normal) para estudiar cómo cambia el equilibrio de
asignación de suelo según la geometría (ver D-13).
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import NDArray

FormaOferta = Literal[
    "normal", "uniforme", "exponencial", "meseta", "bimodal", "valle"
]
"""Forma del perfil de oferta de vivienda S(d) a lo largo del corredor:

- `normal`: campana gaussiana centrada en el CBD (monocéntrica compacta).
- `uniforme`: densidad plana (suburbio homogéneo).
- `exponencial`: S ∝ e^{−d/σ} (von Thünen; decae desde el CBD).
- `meseta`: núcleo de densidad plana de radio σ con borde neto (ciudad compacta
  con frontera; distinta de la normal, que tiene colas gaussianas).
- `bimodal`: dos picos a ±sep del CBD (ciudad policéntrica con subcentros).
- `valle`: densidad que **crece con la distancia** (poco espacio en el centro,
  mucho en la periferia) — triángulo invertido / ciudad desconcentrada.

Nota: en una ciudad **lineal** un anillo a radio r colapsa en dos puntos a ±r,
es decir, coincide con `bimodal`; por eso no se incluye una forma "anular"
separada (ver D-13).
"""


def _discretizar(w: NDArray[np.float64], N: int, CBD: int) -> NDArray[np.int_]:
    """Discretiza un perfil de pesos `w` a un vector entero S con Σ S = N,
    excluyendo el CBD, vía el método del mayor residuo (campana suave, sin el
    "dentado" del muestreo)."""
    w = np.asarray(w, dtype=float).copy()
    w[CBD] = 0.0  # no se construyen viviendas sobre el centro de negocios
    total = w.sum()
    if total <= 0:
        # Degenerado: reparte uniforme fuera del CBD.
        w[:] = 1.0
        w[CBD] = 0.0
        total = w.sum()

    I = len(w)
    target = w / total * N
    S = np.floor(target).astype(int)
    resto = int(N - S.sum())

    frac = target - np.floor(target)
    frac[CBD] = -1.0  # nunca al CBD
    orden = np.argsort(-frac)
    for k in range(max(0, resto)):
        S[orden[k % I]] += 1
    return S


def generar_oferta(
    *,
    forma: FormaOferta,
    I: int,
    N: int,
    CBD: int,
    sigma_frac: float = 0.5,
    forma_param: float = 0.5,
) -> NDArray[np.int_]:
    """Genera la oferta S según `forma`, determinista, con Σ S = N y CBD vacío.

    :param sigma_frac: ancho/dispersión como fracción de la semi-ciudad
        (σ = frac · min(CBD, I−1−CBD)). Controla la dispersión de la campana, la
        pendiente de la exponencial (e-folding) y el ancho del anillo/picos.
    :param forma_param: 2º parámetro, fracción de la semi-ciudad: radio del
        anillo (`anular`) o separación de los picos (`bimodal`). Ignorado en las
        demás formas.
    """
    semi = max(1.0, float(min(CBD, I - 1 - CBD)))
    sigma = max(sigma_frac * semi, 1e-6)
    idx = np.arange(I, dtype=float)
    d = np.abs(idx - CBD)

    if forma == "normal":
        w = np.exp(-0.5 * (d / sigma) ** 2)
    elif forma == "uniforme":
        w = np.ones(I, dtype=float)
    elif forma == "exponencial":
        w = np.exp(-d / sigma)
    elif forma == "meseta":
        # Núcleo de densidad plana con borde neto: super-gaussiana de orden alto
        # (flat-top). w≈1 para d≪σ y cae abruptamente cerca de d=σ.
        w = np.exp(-((d / sigma) ** 8))
    elif forma == "bimodal":
        # Los picos usan un ancho más angosto que el σ global, si no se solapan
        # y la estructura bimodal queda indistinguible de una campana.
        sigma_pico = sigma * 0.5
        sep = forma_param * semi
        w = np.exp(-0.5 * ((idx - (CBD - sep)) / sigma_pico) ** 2) + np.exp(
            -0.5 * ((idx - (CBD + sep)) / sigma_pico) ** 2
        )
    elif forma == "valle":
        # Densidad creciente con la distancia (V / triángulo invertido): poco
        # espacio en el centro, mucho en la periferia.
        w = d.astype(float)
    else:  # pragma: no cover - validado por Pydantic aguas arriba
        raise ValueError(f"forma de oferta desconocida: {forma!r}")

    return _discretizar(w, N, CBD)


def generar_oferta_normal(
    I: int,
    N: int,
    CBD: int,
    stdv: float | None = None,
    rng: np.random.Generator | None = None,
) -> NDArray[np.int_]:
    """Genera un vector de capacidades S que suma exactamente N.

    Distribución normal discreta centrada en el CBD, excluyendo al CBD
    (no se construyen viviendas sobre el centro de negocios). El muestreo
    refleja en los bordes para mantener la simetría.

    :param I: cantidad de parcelas.
    :param N: cantidad total de hogares a distribuir (Σ S = N).
    :param CBD: índice de la parcela del CBD (se excluye).
    :param stdv: desviación estándar; por defecto `min(CBD, I-1-CBD) / 2`.
    :param rng: generador de aleatoriedad (para reproducibilidad).
    """
    if rng is None:
        rng = np.random.default_rng()

    if stdv is None:
        stdv = min(CBD, I - 1 - CBD) / 2

    S = np.zeros(I, dtype=int)
    samples = rng.normal(loc=CBD, scale=stdv, size=N)

    for s in samples:
        i = int(np.round(s))

        if i >= CBD:
            i += 1
        if i < 0:
            i = -i
        if i >= I:
            i = 2 * (I - 1) - i

        # segunda guarda por si el reflejo también sale del rango
        i = max(0, min(i, I - 1))
        S[i] += 1

    return S


def generar_oferta_normal_det(
    I: int,
    N: int,
    CBD: int,
    stdv: float | None = None,
) -> NDArray[np.int_]:
    """Versión determinista de :func:`generar_oferta_normal`.

    En vez de muestrear N hogares (histograma ruidoso), discretiza la densidad
    Normal(CBD, stdv) directamente: S[i] ∝ pdf(i), excluyendo el CBD, y redondea
    al entero garantizando Σ S = N (método del mayor residuo). El resultado es
    una campana suave (sin el "dentado" parcela‑a‑parcela del muestreo).
    """
    if stdv is None:
        stdv = min(CBD, I - 1 - CBD) / 2
    stdv = max(float(stdv), 1e-6)

    idx = np.arange(I, dtype=float)
    w = np.exp(-0.5 * ((idx - CBD) / stdv) ** 2)
    w[CBD] = 0.0  # no se construyen viviendas sobre el centro de negocios
    total = w.sum()
    if total <= 0:
        # Degenerado (p. ej. CBD único): reparte uniforme fuera del CBD.
        w[:] = 1.0
        w[CBD] = 0.0
        total = w.sum()

    target = w / total * N
    S = np.floor(target).astype(int)
    resto = int(N - S.sum())

    # Reparte las `resto` unidades faltantes a las parcelas con mayor fracción.
    frac = target - np.floor(target)
    frac[CBD] = -1.0  # nunca al CBD
    orden = np.argsort(-frac)
    for k in range(max(0, resto)):
        S[orden[k % I]] += 1

    return S
