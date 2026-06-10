"""Estimación de emisiones CO₂ por tramo.

Portado de `titirilquen-repo/app.py:806-876`. Documenta un módulo que el
Overleaf no cubre (ver D-06).

Fórmulas:
  - Auto:  FE(v) = 2467.4 · v^(-0.699)   [g/km], v clampeado a [1, 120]
  - Metro: factor · tren-km/h            [kg/tren·km — ver D-29]
           con tren-km/h = f_op · largo_línea · 2 (ida y vuelta: el servicio
           es un ciclo; el retorno "vacío" es costo real de la frecuencia).
  - Bici / Caminata: 0 (implícito)

El metro emite por TREN circulando, no por pasajero (D-29): con la frecuencia
endógena, esto exhibe las economías de escala del transporte público — más
demanda ⇒ más frecuencia ⇒ más tren-km, pero emisiones por pasajero a la baja;
y con poca demanda el servicio mínimo emite igual (costo fijo). La versión
anterior (kg/pax·km lineal) hacía que cada pasajero nuevo "emitiera", ocultando
exactamente ese efecto.
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
    frecuencia_metro: float,
    estaciones_km: NDArray[np.float64],
    capacidad_auto: float,
    alpha_bpr: float,
    beta_bpr: float,
    v_libre_kmh: float,
    largo_ciudad_km: float,
    n_celdas: int,
    factor_emision_metro_tren_km: float,
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

    # Metro por TREN-km (D-29): emisión fija por tren circulando, independiente
    # de la carga. tren-km/h = f_op · largo de la línea · 2 (ida y vuelta).
    # El perfil espacial se reparte uniforme sobre las celdas que cubre la línea.
    emisiones_metro_g = np.zeros(n_celdas)
    metro_kg = 0.0
    if len(estaciones_km) >= 2 and frecuencia_metro > 0:
        span_km = float(estaciones_km.max() - estaciones_km.min())
        tren_km_h = frecuencia_metro * span_km * 2.0
        metro_kg = factor_emision_metro_tren_km * tren_km_h
        idx_start = int((float(estaciones_km.min()) / largo_ciudad_km) * n_celdas)
        idx_end = int((float(estaciones_km.max()) / largo_ciudad_km) * n_celdas)
        idx_start = max(0, min(idx_start, n_celdas - 1))
        idx_end = max(idx_start + 1, min(idx_end, n_celdas))
        emisiones_metro_g[idx_start:idx_end] = (metro_kg * 1000) / (idx_end - idx_start)

    perfil_kg = (emisiones_auto_g + emisiones_metro_g) / 1000

    return EmissionsResult(
        total_kg_hora=auto_kg + metro_kg,
        auto_kg_hora=auto_kg,
        metro_kg_hora=metro_kg,
        perfil_espacial_kg=perfil_kg,
        velocidad_auto_kmh=v_local,
    )
