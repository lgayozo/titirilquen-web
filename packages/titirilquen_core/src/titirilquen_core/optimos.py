"""Dos referencias de óptimo, evaluadas SOBRE el equilibrio que ya se resolvió.

Son indicadores, no otro equilibrio: dicen cuánto se debería cobrar y con qué
frecuencia operar dada la demanda de esta corrida. Si se aplicaran, la demanda
respondería y los dos números se moverían; el óptimo de verdad es el punto fijo
de ese proceso, que acá no se resuelve.

**Peaje de Pigou.** En un tramo con demora BPR, `t(q) = t0·(1 + α·(q/C)^β)`,
cada auto que entra le agrega demora a los `q` que ya están. Ese costo, que el
conductor no paga, es el costo marginal externo:

    CMgE = q · dt/dq = t0 · α · β · (q/C)^β          [minutos por vehículo]

y el peaje que lo internaliza es ese tiempo al valor del tiempo de quienes lo
sufren. Es la diferencia entre el costo marginal social y el costo medio que
percibe el usuario; con él, el equilibrio de usuario coincide con el óptimo
social del tramo.

Sólo cuenta la demora. La bencina extra que la congestión le hace quemar a los
demás (`operacion_vehicular`) también es un costo externo y queda fuera, así
que el peaje sale algo corto.

**Frecuencia de Mohring.** Con espera media de medio intervalo, `1/(2f)`, la
suma de lo que gastan los usuarios esperando y lo que cuesta operar es

    C(f) = c · ℓ · f  +  Q · V_e / (2f)

con `c` el costo por tren-km, `ℓ` los tren-km de una vuelta, `Q` los pasajeros
de la hora y `V_e` el valor del tiempo de espera. Se minimiza en

    f* = sqrt( Q · V_e / (2 · c · ℓ) )

la regla de la raíz cuadrada de Mohring: la frecuencia óptima crece con
la raíz de la demanda, no en proporción. El modelo opera con otra regla —la
frecuencia que hace caber la carga del tramo crítico, `carga_max / K`—, así que
comparar las dos dice si el servicio queda corto o largo respecto del que
minimiza el costo total. No considera el tope de capacidad ni la congestión de
andén.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.constantes import FACTOR_CAPACIDAD_PRACTICA


def costo_marginal_externo_auto_min(
    flujos_veh_h: NDArray[np.float64],
    *,
    capacidad_direccion: float,
    v_libre_kmh: float,
    ancho_celda_km: float,
    alpha: float,
    beta: float,
) -> NDArray[np.float64]:
    """Minutos de demora que un auto más le impone a los demás, por tramo.

    `q · dt/dq` de la BPR del auto, sobre la misma capacidad práctica con que
    se calculan los tiempos (`FACTOR_CAPACIDAD_PRACTICA · C`, D6)."""
    capacidad = FACTOR_CAPACIDAD_PRACTICA * capacidad_direccion
    if capacidad <= 0 or v_libre_kmh <= 0:
        return np.zeros_like(np.asarray(flujos_veh_h, dtype=float))
    t0 = ancho_celda_km / v_libre_kmh * 60
    return t0 * alpha * beta * (np.asarray(flujos_veh_h, dtype=float) / capacidad) ** beta


def peaje_pigou_clp_km(
    cmge_min: NDArray[np.float64], *, vot_clp_hora: float, ancho_celda_km: float
) -> NDArray[np.float64]:
    """El costo marginal externo en pesos por kilómetro de cada tramo."""
    return cmge_min / 60 * vot_clp_hora / ancho_celda_km


def frecuencia_mohring_tph(
    *,
    pasajeros_hora: float,
    valor_espera_clp_hora: float,
    costo_tren_km_clp: float,
    tren_km_por_vuelta: float,
) -> float:
    """La frecuencia (trenes/hora) que minimiza espera + operación.

    0 si falta alguno de los términos: sin costo de operación la frecuencia
    óptima no está acotada, y sin pasajeros no hay a quién servir."""
    costo_por_tren = costo_tren_km_clp * tren_km_por_vuelta
    if pasajeros_hora <= 0 or valor_espera_clp_hora <= 0 or costo_por_tren <= 0:
        return 0.0
    return float(np.sqrt(pasajeros_hora * valor_espera_clp_hora / (2 * costo_por_tren)))
