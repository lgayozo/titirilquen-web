"""Asignación de hogares a parcelas basada en la matriz `Q`.

Portado de `titirilquen-repo/Ciudad2.py:483-529`. Mantiene el algoritmo de
barrido por rondas de izquierda a derecha.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def asignar_hogares_simple(
    *,
    Q: NDArray[np.float64],
    S: NDArray[np.int_],
    H: NDArray[np.int_],
    rng: np.random.Generator | None = None,
) -> list[list[int]]:
    """Asigna hogares (numerados 1..n_strata) a parcelas respetando Q, S y H.

    Algoritmo: barrido circular de parcelas; en cada parcela con espacio, sortea
    un estrato según la columna `Q[:, i]` (filtrada por disponibilidad H_rest[h]>0).

    :returns: `parcelas`, lista de listas. parcelas[i] = lista de estratos que
        viven en la parcela i. Los estratos se indexan 1-based (1=alto, 2=medio, 3=bajo).
    """
    if rng is None:
        rng = np.random.default_rng()

    n_strata, n_parcelas = Q.shape
    S_rest = np.asarray(S, dtype=int).copy()
    H_rest = np.asarray(H, dtype=int).copy()

    if int(S_rest.sum()) != int(H_rest.sum()):
        raise ValueError(
            f"Capacidad total ({int(S_rest.sum())}) ≠ demanda total ({int(H_rest.sum())})"
        )

    parcelas: list[list[int]] = [[] for _ in range(n_parcelas)]

    while S_rest.sum() > 0:
        progress = False
        for i in range(n_parcelas):
            if S_rest[i] == 0:
                continue

            pesos = Q[:, i].copy()
            pesos[H_rest == 0] = 0.0
            masa = pesos.sum()
            if masa == 0:
                # No se puede completar esta parcela — continuar con las demás
                continue

            probs = pesos / masa
            h = int(rng.choice(n_strata, p=probs))
            parcelas[i].append(h + 1)
            H_rest[h] -= 1
            S_rest[i] -= 1
            progress = True

        if not progress:
            # Q degeneró a 0/1 (underflow numérico): con scores extremos —p.ej.
            # gridlock del acoplado (D-24), donde T llega a miles de minutos y
            # las diferencias α_h·T superan el rango de exp()— hay parcelas cuya
            # única masa está en estratos con cuota agotada. Las cuotas mandan
            # (Σ S = Σ H): el sobrante se reparte como "desborde" — los hogares
            # restantes llenan los espacios restantes en orden aleatorio. Es la
            # lectura física correcta: si el mercado dice "aquí solo viviría el
            # estrato 1" pero el estrato 1 ya no existe, alguien ocupa igual el
            # espacio disponible (la alternativa, fallar, mataba la corrida).
            sobrantes = np.repeat(np.arange(1, n_strata + 1), H_rest)
            rng.shuffle(sobrantes)
            k = 0
            for i in range(n_parcelas):
                while S_rest[i] > 0:
                    parcelas[i].append(int(sobrantes[k]))
                    k += 1
                    S_rest[i] -= 1
            H_rest[:] = 0
            break

    return parcelas
