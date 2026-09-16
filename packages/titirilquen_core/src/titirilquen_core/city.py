"""Ciudad lineal — abstracción 1D con CBD al centro.

Es el montaje de Anas (1990) que Martínez (2018, §3.1) presenta como el límite
discreto de la ciudad monocéntrica de Alonso: localizaciones discretas a
incrementos de distancia del CBD. Dos cosas que en esa teoría son endógenas
—el borde `L` y el perfil de densidad— acá son insumos (ver cap. 1 del libro).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CiudadLineal:
    """Ciudad unidimensional discretizada en `n_celdas` parcelas uniformes.

    El CBD es la celda central, `cbd_index = n_celdas // 2`, y la distancia de
    una celda al centro se mide POR ÍNDICE en todo el núcleo:
    `|i − cbd_index| · ancho_celda_km`. Con `n_celdas` impar eso coincide con la
    distancia entre centroides y el centroide del CBD cae exactamente en L/2;
    por eso `n_celdas` tiene que ser impar, y se exige acá y en `CityConfig`.

    Hasta sep-2026 la clase exponía además `centroides_km` y
    `distancia_al_cbd_km`, una segunda convención (por posición continua) que
    nadie llamaba y que sólo coincidía con la del núcleo con `n` impar (D-45).
    """

    n_celdas: int
    largo_total_km: float

    def __post_init__(self) -> None:
        if self.n_celdas < 3 or self.n_celdas % 2 == 0:
            raise ValueError(f"n_celdas debe ser impar y ≥ 3; obtuve {self.n_celdas}")
        if self.largo_total_km <= 0:
            raise ValueError(f"largo_total_km debe ser positivo; obtuve {self.largo_total_km}")

    @property
    def ancho_celda_km(self) -> float:
        return self.largo_total_km / self.n_celdas

    @property
    def cbd_index(self) -> int:
        return self.n_celdas // 2

    @property
    def cbd_km(self) -> float:
        return self.largo_total_km / 2.0
