"""Estimación de emisiones CO₂ por tramo.

Portado de `titirilquen-repo/app.py:806-876`. Documenta un módulo que el
Overleaf no cubre (ver D-06).

Fórmulas:
  - Auto:  FE(v) = 2467.4 · v^(-0.699)   [g/km], v clampeado a [1, 120]
  - Metro: factor_emision_metro · dist   [kg/pax·km, lineal]
  - Bici / Caminata: 0 (implícito)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


def factor_emision_auto(velocidad_kmh: NDArray[np.float64] | float) -> NDArray[np.float64] | float:
    v = np.clip(velocidad_kmh, 1.0, 120.0)
    return 2467.4 * (v**-0.699)


@dataclass(frozen=True)
class EmissionsResult:
    total_kg_hora: float
    auto_kg_hora: float
    metro_kg_hora: float
    perfil_espacial_kg: NDArray[np.float64]
    velocidad_auto_kmh: NDArray[np.float64]


def calcular_emisiones(
    *,
    flujos_auto: NDArray[np.float64],
    carga_metro_tramos: NDArray[np.float64],
    estaciones_km: NDArray[np.float64],
    capacidad_auto: float,
    alpha_bpr: float,
    beta_bpr: float,
    v_libre_kmh: float,
    largo_ciudad_km: float,
    n_celdas: int,
    factor_emision_metro: float,
) -> EmissionsResult:
    dx_km = largo_ciudad_km / n_celdas

    with np.errstate(divide="ignore", invalid="ignore"):
        grado_sat = flujos_auto / capacidad_auto
        factor_demora = 1 + alpha_bpr * (grado_sat**beta_bpr)
        v_local = v_libre_kmh / factor_demora
    v_local = np.nan_to_num(v_local, nan=v_libre_kmh)

    factores_g_km = factor_emision_auto(v_local)
    emisiones_auto_g = flujos_auto * dx_km * factores_g_km
    auto_kg = float(np.sum(emisiones_auto_g)) / 1000

    f_metro_g_pkm = factor_emision_metro * 1000
    emisiones_metro_g = np.zeros(n_celdas)
    for j in range(len(carga_metro_tramos)):
        start_km = estaciones_km[j]
        end_km = estaciones_km[j + 1]
        idx_start = int((start_km / largo_ciudad_km) * n_celdas)
        idx_end = int((end_km / largo_ciudad_km) * n_celdas)
        if idx_end > idx_start:
            val = carga_metro_tramos[j] * f_metro_g_pkm * dx_km
            emisiones_metro_g[idx_start:idx_end] = val
    metro_kg = float(np.sum(emisiones_metro_g)) / 1000

    perfil_kg = (emisiones_auto_g + emisiones_metro_g) / 1000

    return EmissionsResult(
        total_kg_hora=auto_kg + metro_kg,
        auto_kg_hora=auto_kg,
        metro_kg_hora=metro_kg,
        perfil_espacial_kg=perfil_kg,
        velocidad_auto_kmh=v_local,
    )
