"""Orquestador del uso de suelo — clase `LandUseCity`.

Reemplazo de la clase `Ciudad` de `titirilquen-repo/Ciudad2.py`, con API
explícita y separada de los helpers de transporte.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.land_use.allocation import asignar_hogares_simple
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.equilibrium import (
    LandUseResult,
    solve_heteroscedastic,
    solve_logit,
)

_SOLVERS = {
    "heteroscedastic": solve_heteroscedastic,
    "logit": solve_logit,
}
from titirilquen_core.land_use.supply import generar_oferta


V_REF_KMH = 30.0
"""Velocidad de referencia del baseline "sin transporte": el T por defecto es
el tiempo a flujo libre a esta velocidad. Misma convención que el arranque del
loop acoplado (ver D-23/D-26)."""


def _default_T(
    n_parcelas: int, cbd_index: int, n_strata: int, ancho_celda_km: float
) -> NDArray[np.float64]:
    """T[h, i] = tiempo a flujo libre al CBD, en **minutos** (d_km/v_ref·60),
    igual para todos los estratos (la variación por estrato se captura vía α_h).

    En minutos y no en índices de celda (D-26): con índices, refinar la grilla
    "agrandaba" la ciudad que ve el bid-rent y el equilibrio dependía de la
    resolución; en unidades físicas T(x) es invariante a la discretización."""
    dist_km = np.abs(np.arange(n_parcelas) - cbd_index).astype(float) * ancho_celda_km
    t_min = dist_km / V_REF_KMH * 60.0
    return np.tile(t_min, (n_strata, 1))


@dataclass
class LandUseCity:
    """Ciudad lineal con uso de suelo resuelto.

    Uso típico:
        city = LandUseCity.build(L=201, CBD=100, cfg=LandUseConfig(...))
        # o con una T proveniente de transporte:
        city.update(T=T_from_transport)
    """

    L: int
    cbd_index: int
    cfg: LandUseConfig
    # Ancho físico de cada celda. Default ≈ ciudad de 20 km en 201 celdas (la
    # referencia del frontend); los callers deben pasar largo_km/L real.
    ancho_celda_km: float = 0.1
    S: NDArray[np.int_] = field(default_factory=lambda: np.zeros(0, dtype=int))
    result: LandUseResult | None = None
    parcelas: list[list[int]] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        *,
        L: int,
        CBD: int,
        cfg: LandUseConfig,
        ancho_celda_km: float = 0.01,
        S: NDArray[np.int_] | None = None,
        T: NDArray[np.float64] | None = None,
        rng: np.random.Generator | None = None,
    ) -> "LandUseCity":
        """Construye la ciudad, genera oferta si no se entrega, y resuelve equilibrio."""
        if rng is None:
            rng = np.random.default_rng()
        N_total = int(sum(cfg.H_por_estrato))
        if S is None:
            S = generar_oferta(
                forma=cfg.forma,
                I=L,
                N=N_total,
                CBD=CBD,
                sigma_frac=cfg.oferta_sigma_frac,
                forma_param=cfg.forma_param,
            )
        if int(sum(S)) != N_total:
            raise ValueError(f"Σ S ({int(sum(S))}) ≠ Σ H ({N_total})")

        city = cls(L=L, cbd_index=CBD, cfg=cfg, ancho_celda_km=ancho_celda_km, S=S)
        city.update(T=T, rng=rng)
        return city

    def update(
        self,
        *,
        T: NDArray[np.float64] | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        """Recalcula el equilibrio. Si `T` no se entrega, usa la distancia al CBD."""
        if rng is None:
            rng = np.random.default_rng()

        H = np.asarray(self.cfg.H_por_estrato, dtype=int)
        n_strata = len(H)
        y = np.asarray([s.y for s in self.cfg.estratos], dtype=float)
        alpha = np.asarray([s.alpha for s in self.cfg.estratos], dtype=float)
        rho = np.asarray([s.rho for s in self.cfg.estratos], dtype=float)
        lambda_h = np.asarray([s.lambda_ for s in self.cfg.estratos], dtype=float)

        if T is None:
            T = _default_T(self.L, self.cbd_index, n_strata, self.ancho_celda_km)
        if T.shape != (n_strata, self.L):
            raise ValueError(f"T shape {T.shape} != ({n_strata}, {self.L})")

        solver = _SOLVERS[self.cfg.solver]
        self.result = solver(
            H=H,
            S=self.S,
            y=y,
            T=T,
            alpha=alpha,
            rho=rho,
            lambda_h=lambda_h,
            beta=self.cfg.beta,
            tol=self.cfg.tol,
            max_iter=self.cfg.max_iter,
            ancho_celda_km=self.ancho_celda_km,
        )
        self.parcelas = asignar_hogares_simple(Q=self.result.Q, S=self.S, H=H, rng=rng)

    def densidad_por_celda(self) -> NDArray[np.float64]:
        """Densidad de población por celda (hab/km) como **consecuencia de la oferta
        `S`**:

            dens(i) = S_i / Δx

        donde `S_i` son los hogares que la ciudad ofrece en la celda `i`
        (`supply.generar_oferta`) y `Δx = ancho_celda_km`. La **forma** la da el
        perfil de oferta (`forma`); ya NO es un gradiente de Clark geométrico
        impuesto e independiente del equilibrio. Es **invariante a la grilla** (`S`
        escala con `Δx`, así que `S/Δx` no depende de la resolución) e
        **independiente del estrato** (la composición `Q` solo reparte esa
        población entre estratos, no fija su nivel). Las celdas sin oferta (el CBD,
        `S=0`) quedan en 0.

        Es la **misma envolvente** que usa la asignación de hogares
        (`asignar_hogares_simple` reparte `S·Q`), el feed a transporte y las
        figuras del frontend: una sola definición de "cuántos viven en la celda i"."""
        dens = np.asarray(self.S, dtype=float) / self.ancho_celda_km
        dens[np.asarray(self.S) <= 0] = 0.0  # sin vivienda (CBD)
        return dens

    def hogares_por_parcela_estrato(self) -> NDArray[np.int_]:
        """Matriz (n_strata, L) con el conteo efectivo asignado por celda."""
        n_strata = len(self.cfg.H_por_estrato)
        conteos = np.zeros((n_strata, self.L), dtype=int)
        for i, parcela in enumerate(self.parcelas):
            for h in parcela:
                conteos[h - 1, i] += 1
        return conteos
