"""Oferta vial — Greenshields + BPR.

Portado de `titirilquen-repo/app.py:110-144`. Capacidad total por dirección =
`C_pista · N_pistas`, donde `C_pista` viene de Greenshields.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class CarSupplyResult:
    t_usuarios_min: NDArray[np.float64]
    flujos_veh_por_hora: NDArray[np.float64]
    capacidad_direccion: float
    alpha_bpr: float
    beta_bpr: float
    v_libre_kmh: float


def _factor_ancho(ancho_m: float) -> float:
    if ancho_m >= 3.5:
        return 1.0
    if 3.0 < ancho_m < 3.5:
        return 0.9
    return 0.75


def demora_auto_tramo(
    *,
    ubicacion_centro_km: float,
    demanda: NDArray[np.float64],
    v_max_kmh: float,
    ancho_pista_m: float,
    largo_vehiculo_m: float,
    gap_m: float,
    L_ciudad_km: float,
    num_pistas: int,
    alpha_bpr: float,
    beta_bpr: float,
) -> CarSupplyResult:
    f_a = _factor_ancho(ancho_pista_m)
    v_l = v_max_kmh * f_a
    densidad_emb = 1000 / (largo_vehiculo_m + gap_m)
    cap_pista = (densidad_emb * v_l) / 4
    num_pistas = max(1, num_pistas)
    capacidad_direccion = cap_pista * num_pistas

    N = len(demanda)
    idx_centro = int((ubicacion_centro_km / L_ciudad_km) * N)
    idx_centro = max(0, min(idx_centro, N - 1))

    t0 = ((L_ciudad_km / N) / v_l) * 60
    t_usuarios = np.zeros(N)
    flujos = np.zeros(N)
    demanda_aj = demanda.copy()
    demanda_aj[idx_centro] = 0

    if idx_centro > 0:
        d_izq = demanda_aj[:idx_centro]
        flujo_izq = np.cumsum(d_izq)
        flujos[:idx_centro] = flujo_izq
        with np.errstate(divide="ignore", invalid="ignore"):
            t_local = t0 * (1 + alpha_bpr * ((flujo_izq / capacidad_direccion) ** beta_bpr))
        t_usuarios[:idx_centro] = np.cumsum(t_local[::-1])[::-1] - (t_local / 2)

    if idx_centro < N - 1:
        d_der = demanda_aj[idx_centro + 1 :]
        flujo_der = np.cumsum(d_der[::-1])[::-1]
        flujos[idx_centro + 1 :] = flujo_der
        with np.errstate(divide="ignore", invalid="ignore"):
            t_local = t0 * (1 + alpha_bpr * ((flujo_der / capacidad_direccion) ** beta_bpr))
        t_usuarios[idx_centro + 1 :] = np.cumsum(t_local) - (t_local / 2)

    t_usuarios[idx_centro] = 0
    flujos[idx_centro] = 0

    return CarSupplyResult(
        t_usuarios_min=t_usuarios,
        flujos_veh_por_hora=flujos,
        capacidad_direccion=capacidad_direccion,
        alpha_bpr=alpha_bpr,
        beta_bpr=beta_bpr,
        v_libre_kmh=v_l,
    )
