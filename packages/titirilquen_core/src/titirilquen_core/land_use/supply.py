"""Generación de la oferta de suelo S[i] — capacidades por parcela.

Portado de `titirilquen-repo/Ciudad2.py:213-247`.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


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
