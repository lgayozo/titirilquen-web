"""Módulo de uso de suelo (Alonso-Muth-Mills monocéntrico).

Ciudad lineal con H estratos socioeconómicos compitiendo por L parcelas.
Cada estrato tiene ingreso `y_h`, sensibilidad al ingreso `λ_h`, penalización
de transporte `α_h` y penalización de densidad `ρ_h`.

La asignación se resuelve mediante un punto fijo logit sobre el vector de
utilidades promedio `u_bar`, del cual se derivan los precios y las
probabilidades de subasta `Q[h, i]`.

Referencia: Martínez F., *Microeconomic Modelling in Urban Science*, cap. 3–5.
Portado verbatim de `titirilquen-repo/Ciudad2.py`.
"""

from titirilquen_core.land_use.allocation import asignar_hogares_simple
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig
from titirilquen_core.land_use.equilibrium import LandUseResult, solve_frechet, solve_logit
from titirilquen_core.land_use.supply import generar_oferta_normal

__all__ = [
    "LandUseCity",
    "LandUseConfig",
    "LandUseResult",
    "LandUseStratumConfig",
    "asignar_hogares_simple",
    "generar_oferta_normal",
    "solve_frechet",
    "solve_logit",
]
