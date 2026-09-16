"""El caso mínimo: dos estratos, cinco parcelas.

Los números están elegidos para que se puedan leer, no para ser realistas. Todo
en unidades de utilidad directamente, sin pesos ni millones: con ingresos de
verdad las pujas difieren en 10⁶ y no se puede ver nada en un gráfico.

**La restricción estructural.** El equilibrio pide que cada estrato coloque
exactamente sus hogares, `Σ_i S_i·Q_{h/i} = H_h`. Sumando sobre `h`, y como las
columnas de `Q` suman 1, queda `Σ_i S_i = Σ_h H_h`. O sea que la oferta total
tiene que igualar a la demanda total, o el sistema no tiene solución. No es una
elección del caso de juguete: es una condición sobre los datos que el modelo
impone siempre.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

#: Nombres de los dos estratos, en el orden de todos los arrays.
ESTRATOS = ("Alto", "Bajo")
#: Etiquetas de las cinco parcelas, ordenadas por distancia al CBD.
PARCELAS = ("P1", "P2", "P3", "P4", "P5")


@dataclass(frozen=True)
class Caso:
    """Los datos del problema. Nada de esto se resuelve: es el enunciado."""

    #: Hogares de cada estrato que hay que localizar. `(2,)`
    H: NDArray[np.float64]
    #: Viviendas disponibles en cada parcela. `(5,)`
    S: NDArray[np.float64]
    #: Ingreso de cada estrato. `(2,)`
    y: NDArray[np.float64]
    #: Tiempo de viaje al CBD desde cada parcela, en minutos. `(5,)`
    T: NDArray[np.float64]
    #: Desutilidad marginal del tiempo de viaje, por estrato. `(2,)`
    alpha: NDArray[np.float64]
    #: Desutilidad marginal de la densidad, por estrato. `(2,)`
    rho: NDArray[np.float64]
    #: Utilidad marginal del ingreso, por estrato. `(2,)`
    lambda_h: NDArray[np.float64]
    #: Escala global del ruido de las pujas.
    beta: float = 1.0

    def score(self) -> NDArray[np.float64]:
        """La puja determinística `w_hi = y_h + f_h(i)/λ_h`. `(2, 5)`

        Es la disposición a pagar antes del ruido y antes de descontar `ū`. La
        división por `λ` convierte utilidad en plata: `f` está en útiles y `λ`
        es útiles por peso.
        """
        f = -self.alpha[:, None] * self.T[None, :] - self.rho[:, None] * self.S[None, :]
        return self.y[:, None] + f / self.lambda_h[:, None]

    def theta(self) -> NDArray[np.float64]:
        """Escala del ruido de la puja de cada estrato, `θ_h = 1/(β·λ_h)`. `(2,)`

        Es el único lugar por donde λ entra al modelo de forma que la subasta
        pueda distinguirlo: mueve la DISPERSIÓN, no solo el nivel. Con los λ
        iguales los θ son iguales y el HEV colapsa al logit cerrado.
        """
        return 1.0 / (self.beta * self.lambda_h)

    def comprueba(self) -> None:
        """La restricción estructural, verificada explícitamente."""
        if not np.isclose(self.S.sum(), self.H.sum()):
            raise ValueError(
                f"oferta total {self.S.sum()} != demanda total {self.H.sum()}: "
                "el sistema de equilibrio no tiene solucion"
            )


def caso_base(lambda_h: tuple[float, float] = (1.0, 1.0)) -> Caso:
    """El caso de juguete. `lambda_h` es lo único que se varía entre corridas.

    Las parcelas están a 1, 2, 3, 4 y 5 km del CBD, a 10 min/km. El estrato alto
    valora el doble el tiempo de viaje y cuatro veces más la baja densidad, así
    que su puja cae mucho más rápido con la distancia: el gradiente de Alonso
    está metido en los datos, no impuesto en la solución.
    """
    caso = Caso(
        H=np.array([40.0, 60.0]),
        S=np.array([10.0, 20.0, 30.0, 20.0, 20.0]),
        y=np.array([3.0, 1.0]),
        T=np.array([10.0, 20.0, 30.0, 40.0, 50.0]),
        alpha=np.array([0.060, 0.030]),
        rho=np.array([0.020, 0.005]),
        lambda_h=np.array(list(lambda_h)),
    )
    caso.comprueba()
    return caso
