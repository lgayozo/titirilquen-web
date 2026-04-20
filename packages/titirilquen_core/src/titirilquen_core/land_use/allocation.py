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
            raise RuntimeError(
                f"Asignación estancada con S_rest={S_rest.sum()} y H_rest={H_rest.tolist()}"
            )

    return parcelas
