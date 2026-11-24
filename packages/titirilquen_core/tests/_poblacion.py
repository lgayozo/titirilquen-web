"""La antigua «densidad plana», expresada como uso de suelo.

Hasta sep-2026 los tests poblaban la ciudad con `densidad_hab_km` ×
`share_estratos` (ruta `iter_msa`). Esa ruta desapareció: la población viene
siempre del suelo. `suelo_uniforme` es su equivalente exacto —oferta uniforme,
mezcla `π_h` en toda celda— para que los tests sigan describiendo una ciudad
plana cuando eso es lo que quieren.
"""

from __future__ import annotations

from titirilquen_core.land_use.config import LandUseConfig


def suelo_uniforme(
    total: int, shares: tuple[float, float, float] = (0.10, 0.40, 0.50)
) -> LandUseConfig:
    """`total` hogares repartidos `shares` sobre una oferta uniforme."""
    h = [round(total * s) for s in shares]
    h[1] += total - sum(h)  # el redondeo cierra en el estrato medio
    return LandUseConfig(H_por_estrato=(h[0], h[1], h[2]), forma="uniforme", max_iter=200)
