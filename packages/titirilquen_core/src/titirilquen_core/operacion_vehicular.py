"""Consumo de recursos de operar un auto, como lo pide la evaluación social.

Dos fuentes, las dos en `reference/`:

- **MESPIVU** (MDS–SECTRA 2013), sección 13.1.1: las funciones de consumo.
  Combustible en movimiento (ec. 13.1.1-4, tabla 13.1.1-3) y «otros costos de
  operación» —lubricantes, neumáticos, repuestos y mano de obra de
  mantenimiento— (ec. 13.1.1-7 a 13.1.1-11, tablas 13.1.1-8 a 13.1.1-11).
- **Precios Sociales** (MDSF), capítulo 4: los precios, que llegan en
  `SimulationConfig.precios_sociales` porque cambian cada año.

Sólo la columna «Autos, camionetas y todo terreno»: el modelo no tiene otro
vehículo motorizado privado.

**Lo que el modelo NO tiene y por eso queda fuera** (se declara, no se inventa):

- Detenciones y ralentí (los términos `h·cd` y `d·cr` de la ec. 13.1.1-4): la
  BPR da una velocidad media por tramo, no paradas.
- La corrección por gradiente (ec. 13.1.1-5).
- La rugosidad del pavimento. El manual no trae un IRI por defecto —lo saca de
  un catastro—, así que `precios_sociales.iri` vale 0 por omisión y el
  resultado es un PISO: sólo el término que no depende de la rugosidad.

Ojo con la tabla 13.1.1-3: el encabezado impreso dice «(ml/det)», pero el texto
y la ecuación la usan como consumo en movimiento por kilómetro. Acá va en ml/km.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.config import PreciosSociales

#: MESPIVU, tabla 13.1.1-3: velocidad crucero (km/h) → consumo en movimiento
#: (ml/km) de autos, camionetas y todo terreno.
CONSUMO_AUTO_VELOCIDAD_KMH = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0])
CONSUMO_AUTO_ML_KM = np.array([205.6, 110.2, 81.3, 68.9, 63.7, 62.4, 64.0, 67.5, 73.1, 80.1])


def consumo_combustible_auto_ml_km(
    velocidad_kmh: NDArray[np.float64] | float,
) -> NDArray[np.float64] | float:
    """Consumo de combustible en movimiento de un auto, en ml/km.

    Interpola linealmente la tabla 13.1.1-3 («para velocidades no incluidas en
    las tablas, se interpola»). Fuera del rango 10–100 km/h se queda con el
    extremo: la tabla no da con qué extrapolar.
    """
    return np.interp(velocidad_kmh, CONSUMO_AUTO_VELOCIDAD_KMH, CONSUMO_AUTO_ML_KM)


def otros_costos_operacion_auto_clp_km(precios: PreciosSociales) -> float:
    """Lubricantes, neumáticos, repuestos y mantención de un auto, en $/km.

    Ec. 13.1.1-7 del MESPIVU con los consumos de las ec. 13.1.1-8 a 13.1.1-11
    para vías pavimentadas (`α + β·IRI` o `α + β·IRIⁿ`), con los precios y la
    rugosidad de la configuración. Los consumos del manual son por 1.000 km.
    """
    iri = precios.iri
    lubricante_l = 1.109 + 0.005498 * iri
    neumaticos = 0.052 + 0.001241 * iri
    repuestos_pct = 0.173 + 0.00286 * iri**1.87  # % del vehículo nuevo
    mano_obra_h = 1.083 + 0.02539 * iri**1.74
    por_mil_km = (
        lubricante_l * precios.lubricante_auto_clp_l
        + neumaticos * precios.neumatico_auto_clp
        + repuestos_pct / 100 * precios.vehiculo_auto_clp
        + mano_obra_h * precios.mantencion_clp_h
    )
    return por_mil_km / 1000
