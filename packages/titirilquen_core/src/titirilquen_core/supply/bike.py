"""Oferta de bicicletas — BPR con ajuste por pendiente.

Portado de `titirilquen-repo/app.py:146-182`. Comportamiento idéntico al original;
cambios sólo en tipado y dataclass de salida.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class BikeSupplyResult:
    t_usuarios_min: NDArray[np.float64]
    flujos_bici_por_hora: NDArray[np.float64]


def _velocidad_con_pendiente(v_media: float, pendiente_pct: float) -> float:
    """Factor de velocidad según pendiente. Coeficiente `0.9992` (no `0.09992`
    como dice el Overleaf) — ver D-01.
    """
    if pendiente_pct > 0:
        factor = -0.0579 * pendiente_pct + 0.9992
    else:
        factor = -0.0455 * pendiente_pct + 1.0
    return max(min(v_media * factor, 45.0), 5.0)


def demora_bici_tramo(
    *,
    ubicacion_centro_km: float,
    capacidad: int,
    demanda: NDArray[np.float64],
    v_media: float,
    L_ciudad_km: float,
    alpha: float,
    beta: float,
    pendiente_porcentaje: float = 0.0,
) -> BikeSupplyResult:
    """Calcula demoras acumuladas y flujos por celda hacia el CBD."""
    N = len(demanda)
    idx_centro = int((ubicacion_centro_km / L_ciudad_km) * N)
    idx_centro = max(0, min(idx_centro, N - 1))
    dx = L_ciudad_km / N

    v_izq = _velocidad_con_pendiente(v_media, pendiente_porcentaje)
    v_der = _velocidad_con_pendiente(v_media, -pendiente_porcentaje)
    t0_izq = (dx / v_izq) * 60
    t0_der = (dx / v_der) * 60

    t_usuarios = np.zeros(N)
    flujos = np.zeros(N)
    demanda_aj = demanda.copy()
    demanda_aj[idx_centro] = 0

    if idx_centro > 0:
        d_izq = demanda_aj[:idx_centro]
        flujo_izq = np.cumsum(d_izq)
        flujos[:idx_centro] = flujo_izq
        t_local = t0_izq * (1 + alpha * ((flujo_izq / capacidad) ** beta))
        t_ac_izq = np.cumsum(t_local[::-1])[::-1]
        t_usuarios[:idx_centro] = t_ac_izq - (t_local / 2)

    if idx_centro < N - 1:
        d_der = demanda_aj[idx_centro + 1 :]
        flujo_der = np.cumsum(d_der[::-1])[::-1]
        flujos[idx_centro + 1 :] = flujo_der
        t_local = t0_der * (1 + alpha * ((flujo_der / capacidad) ** beta))
        t_ac_der = np.cumsum(t_local)
        t_usuarios[idx_centro + 1 :] = t_ac_der - (t_local / 2)

    t_usuarios[idx_centro] = 0
    flujos[idx_centro] = 0

    return BikeSupplyResult(t_usuarios_min=t_usuarios, flujos_bici_por_hora=flujos)
