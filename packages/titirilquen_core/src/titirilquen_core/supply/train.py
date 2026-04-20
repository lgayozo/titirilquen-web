"""Oferta de transporte público (trenes) — sistema cíclico.

Portado de `titirilquen-repo/app.py:184-253`. Frecuencia endógena según tramo
crítico; tiempo de espera base `30/f_op` con penalización BPR-like si la
estación se satura.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

# Parámetros de congestión en andén — fijos en el código original.
# Ver app.py:237-238 del repo original.
_ALFA_CONGESTION = 0.5
_BETA_CONGESTION = 4.0


@dataclass(frozen=True)
class TrainSupplyResult:
    t_acceso_min: NDArray[np.float64]
    t_espera_min: NDArray[np.float64]
    t_viaje_min: NDArray[np.float64]
    t_total_min: NDArray[np.float64]
    frecuencia_operativa: float
    carga_por_tramo: NDArray[np.float64]
    estaciones_km: NDArray[np.float64]


def oferta_tren(
    *,
    demanda: NDArray[np.float64],
    L_ciudad_km: float,
    x_centro_km: float,
    v_tren_kmh: float,
    capacidad_tren: int,
    num_estaciones: int,
    v_caminata_kmh: float,
    tasa_carga: float,
    frec_min: float,
    frec_max: float,
) -> TrainSupplyResult:
    N = len(demanda)
    dx = L_ciudad_km / N
    x_parcelas = np.arange(N) * dx + (dx / 2)

    dist_entre_est = L_ciudad_km / num_estaciones
    estaciones = np.unique(
        np.concatenate(
            [
                np.arange(x_centro_km, L_ciudad_km + 0.01, dist_entre_est),
                np.arange(x_centro_km, -0.01, -dist_entre_est),
            ]
        )
    )
    estaciones = np.sort(estaciones[(estaciones >= 0) & (estaciones <= L_ciudad_km)])
    num_s = len(estaciones)

    pax_suben = np.zeros(num_s)
    dist_acceso = np.zeros(N)
    loc_estacion_acceso = np.zeros(N)
    idx_estacion_usuario = np.zeros(N, dtype=int)

    idx_cbd_parcela = int((x_centro_km / L_ciudad_km) * N)
    for i in range(N):
        dists = np.abs(estaciones - x_parcelas[i])
        idx_est = int(np.argmin(dists))
        dist_acceso[i] = dists[idx_est]
        loc_estacion_acceso[i] = estaciones[idx_est]
        idx_estacion_usuario[i] = idx_est
        if i != idx_cbd_parcela:
            pax_suben[idx_est] += demanda[i]

    idx_centro_est = int(np.argmin(np.abs(estaciones - x_centro_km)))

    if num_s >= 2:
        carga_por_tramo = np.zeros(num_s - 1)
    else:
        carga_por_tramo = np.zeros(0)
    carga_al_salir_estacion = np.zeros(num_s)

    acum = 0.0
    for i in range(idx_centro_est):
        acum += pax_suben[i]
        if i < len(carga_por_tramo):
            carga_por_tramo[i] = acum
            carga_al_salir_estacion[i] = acum

    acum = 0.0
    for i in range(num_s - 1, idx_centro_est, -1):
        acum += pax_suben[i]
        if i - 1 >= 0:
            carga_por_tramo[i - 1] = acum
            carga_al_salir_estacion[i] = acum

    carga_maxima = float(np.max(carga_por_tramo)) if len(carga_por_tramo) > 0 else 0.0
    f_teorica = carga_maxima / capacidad_tren if capacidad_tren > 0 else 0.0
    f_op = float(np.clip(f_teorica, frec_min, frec_max))

    capacidad_maxima_sistema = frec_max * capacidad_tren
    t_espera_base = (1 / (2 * f_op)) * 60 if f_op > 0 else 0.0

    t_espera_por_estacion = np.zeros(num_s)
    for i in range(num_s):
        if i == idx_centro_est:
            t_espera_por_estacion[i] = 0.0
            continue
        carga_local = carga_al_salir_estacion[i]
        ratio = carga_local / capacidad_maxima_sistema if capacidad_maxima_sistema > 0 else 0.0
        factor = 1.0 if ratio <= 1 else _ALFA_CONGESTION * (ratio**_BETA_CONGESTION)
        t_espera_por_estacion[i] = t_espera_base * factor

    t_acceso_min = (dist_acceso / v_caminata_kmh) * 60
    t_espera_min = t_espera_por_estacion[idx_estacion_usuario]
    t_viaje_min = (np.abs(loc_estacion_acceso - x_centro_km) / v_tren_kmh) * 60
    t_total = t_acceso_min + t_espera_min + t_viaje_min

    # `tasa_carga` actualmente sin uso en la fórmula original, se preserva como
    # parámetro reservado para futura inclusión de tiempo de dwell.
    _ = tasa_carga

    return TrainSupplyResult(
        t_acceso_min=t_acceso_min,
        t_espera_min=t_espera_min,
        t_viaje_min=t_viaje_min,
        t_total_min=t_total,
        frecuencia_operativa=f_op,
        carga_por_tramo=carga_por_tramo,
        estaciones_km=estaciones,
    )
