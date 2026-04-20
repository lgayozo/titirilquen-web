"""Ciudad lineal — abstracción 1D con CBD al centro.

Reemplazo directo de la clase `CiudadLineal` de `app.py:68-73` con validación
de dominio y helpers. No incluye modelo de uso de suelo (queda en v2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CiudadLineal:
    """Ciudad unidimensional discretizada en `n_celdas` parcelas uniformes.

    El CBD se ubica en la celda central: `cbd_index = n_celdas // 2`.
    La posición kilométrica de la celda `i` es `(i + 0.5) · ancho_celda`.
    """

    n_celdas: int
    largo_total_km: float

    @property
    def ancho_celda_km(self) -> float:
        return self.largo_total_km / self.n_celdas

    @property
    def cbd_index(self) -> int:
        return self.n_celdas // 2

    @property
    def cbd_km(self) -> float:
        return self.largo_total_km / 2.0

    def centroides_km(self) -> np.ndarray:
        """Posición (km) del centroide de cada celda."""
        return (np.arange(self.n_celdas) + 0.5) * self.ancho_celda_km

    def distancia_al_cbd_km(self) -> np.ndarray:
        """Distancia absoluta (km) desde el centroide de cada celda al CBD."""
        return np.abs(self.centroides_km() - self.cbd_km)
