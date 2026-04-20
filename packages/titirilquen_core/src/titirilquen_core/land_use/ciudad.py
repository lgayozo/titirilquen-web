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
from titirilquen_core.land_use.equilibrium import LandUseResult, solve_frechet, solve_logit
from titirilquen_core.land_use.supply import generar_oferta_normal


def _default_T(n_parcelas: int, cbd_index: int, n_strata: int) -> NDArray[np.float64]:
    """T[h, i] = |i - cbd|, igual para todos los estratos (la variación por
    estrato se captura vía α_h)."""
    dist = np.abs(np.arange(n_parcelas) - cbd_index).astype(float)
    return np.tile(dist, (n_strata, 1))


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
    ancho_celda_km: float = 0.01
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
            S = generar_oferta_normal(L, N_total, CBD, rng=rng)
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
            T = _default_T(self.L, self.cbd_index, n_strata)
        if T.shape != (n_strata, self.L):
            raise ValueError(f"T shape {T.shape} != ({n_strata}, {self.L})")

        solver = solve_logit if self.cfg.solver == "logit" else solve_frechet
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
        )
        self.parcelas = asignar_hogares_simple(Q=self.result.Q, S=self.S, H=H, rng=rng)

    def hogares_por_parcela_estrato(self) -> NDArray[np.int_]:
        """Matriz (n_strata, L) con el conteo efectivo asignado por celda."""
        n_strata = len(self.cfg.H_por_estrato)
        conteos = np.zeros((n_strata, self.L), dtype=int)
        for i, parcela in enumerate(self.parcelas):
            for h in parcela:
                conteos[h - 1, i] += 1
        return conteos
