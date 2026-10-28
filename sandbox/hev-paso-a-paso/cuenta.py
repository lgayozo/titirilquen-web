"""Cuántas veces se resuelve el logit heteroscedástico en una corrida.

    uv run python cuenta.py

Existe porque la pregunta «¿en qué momento se resuelve el HEV?» tiene una
respuesta contraintuitiva: en ninguno en particular. El HEV es la operación más
interna, y se resuelve entera cada vez que se evalúa la función de exceso — o
sea, una vez por cada punto de la curva de la Fig. 01.

Se instrumenta `subasta.q_hev` con un contador en vez de estimarlo a mano.
"""

from __future__ import annotations

import numpy as np

import subasta
from caso import caso_base

CUENTA = {"llamadas": 0, "integrando": 0}
_ORIGINAL = subasta.q_hev


def _espia(loc, theta):
    CUENTA["llamadas"] += 1
    # Cada llamada evalua el integrando en `nodos` puntos, por estrato y parcela.
    CUENTA["integrando"] += loc.shape[0] * loc.shape[1] * subasta.N_NODOS
    return _ORIGINAL(loc, theta)


def mide(nombre: str, fn) -> tuple[str, int, int]:
    CUENTA["llamadas"] = CUENTA["integrando"] = 0
    fn()
    return nombre, CUENTA["llamadas"], CUENTA["integrando"]


def main() -> None:
    subasta.q_hev = _espia
    caso = caso_base()

    filas = [
        mide("una sola evaluacion de g(delta)", lambda: subasta.exceso(caso, 0.0)),
        mide("el balanceo entero (8 iteraciones)", lambda: subasta.resuelve_balanceo(caso)),
        mide("la biseccion (53 iteraciones)", lambda: subasta.resuelve_brent(caso)),
        mide(
            "la curva de la Fig. 01 (601 + 201 puntos)",
            lambda: [
                subasta.exceso(caso, float(d))
                for d in np.concatenate([np.linspace(-8, 8, 601), np.linspace(-0.80, -0.60, 201)])
            ],
        ),
    ]

    print("\n  DONDE SE RESUELVE EL LOGIT HETEROSCEDASTICO\n")
    print("  exceso(delta)            <- un punto de la curva")
    print("    +- colocados(u)")
    print("        +- q_hev(loc, th)  <- ACA. El HEV entero, una vez.")
    print("            +- _PESO @ z   <- la cuadratura, 401 nodos\n")
    an = max(len(f[0]) for f in filas)
    print(f"  {'':<{an}}  {'HEV resueltos':>14}  {'evals. del integrando':>22}")
    print(f"  {'-' * an}  {'-' * 14}  {'-' * 22}")
    for nombre, n, ev in filas:
        print(f"  {nombre:<{an}}  {n:>14,}  {ev:>22,}".replace(",", "."))
    print("\n  El HEV no se resuelve «en un momento»: es la operacion mas interna,")
    print("  y el equilibrio consiste en resolverlo una y otra vez hasta que la")
    print("  asignacion que devuelve coloque a todos los hogares.\n")


if __name__ == "__main__":
    main()
