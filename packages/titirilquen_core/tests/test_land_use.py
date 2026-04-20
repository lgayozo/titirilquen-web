from __future__ import annotations

import numpy as np
import pytest

from titirilquen_core.land_use import (
    LandUseCity,
    LandUseConfig,
    LandUseStratumConfig,
    generar_oferta_normal,
    solve_logit,
    solve_frechet,
)


def test_oferta_normal_suma_exactamente_N() -> None:
    rng = np.random.default_rng(42)
    S = generar_oferta_normal(I=101, N=1000, CBD=50, rng=rng)
    assert int(S.sum()) == 1000
    assert len(S) == 101


def test_oferta_normal_respeta_cbd_vacio() -> None:
    rng = np.random.default_rng(42)
    S = generar_oferta_normal(I=101, N=1000, CBD=50, rng=rng)
    # Puede no ser exactamente 0 si la reflexión empuja; pero debería ser bajo
    assert S[50] == 0 or S[50] < S[49]


def test_solve_logit_converge_simple() -> None:
    L, CBD = 51, 25
    H = np.array([100, 100, 100])
    S = np.full(L, 6)
    S[CBD] = 0
    S[0] = S[0] + (H.sum() - S.sum())
    assert int(S.sum()) == int(H.sum())
    T = np.tile(np.abs(np.arange(L) - CBD).astype(float), (3, 1))
    res = solve_logit(
        H=H, S=S, y=np.array([100.0, 50.0, 10.0]), T=T,
        alpha=np.array([1.3, 1.2, 1.1]),
        rho=np.array([1.0, 1.0, 1.0]),
        lambda_h=np.array([1.0, 1.0, 1.0]),
        beta=1.0, tol=1e-6, max_iter=5000,
    )
    assert res.converged
    # Q columnas deben sumar 1 donde S>0; donde S=0, Q=0.
    col_sum = res.Q.sum(axis=0)
    expected = np.where(S > 0, 1.0, 0.0)
    np.testing.assert_allclose(col_sum, expected, atol=1e-6)


def test_land_use_city_build_asigna_todos_los_hogares() -> None:
    cfg = LandUseConfig(
        H_por_estrato=(300, 300, 300),
        estratos=(
            LandUseStratumConfig(y=100.0, alpha=1.3, rho=1.0),
            LandUseStratumConfig(y=50.0, alpha=1.2, rho=1.0),
            LandUseStratumConfig(y=10.0, alpha=1.1, rho=1.0),
        ),
        beta=1.0,
        max_iter=2000,
    )
    rng = np.random.default_rng(42)
    city = LandUseCity.build(L=51, CBD=25, cfg=cfg, rng=rng)
    asignados = sum(len(p) for p in city.parcelas)
    assert asignados == 900
    assert city.result is not None


def test_update_con_T_custom() -> None:
    cfg = LandUseConfig(H_por_estrato=(200, 200, 200), max_iter=2000)
    rng = np.random.default_rng(42)
    city = LandUseCity.build(L=51, CBD=25, cfg=cfg, rng=rng)
    # Nueva T: distancia cúbica (hace transporte más penalizante)
    T_custom = np.tile((np.abs(np.arange(51) - 25) ** 1.5).astype(float), (3, 1))
    city.update(T=T_custom, rng=rng)
    asignados = sum(len(p) for p in city.parcelas)
    assert asignados == 600


def test_frechet_tambien_converge() -> None:
    L, CBD = 31, 15
    H = np.array([100, 100, 100])
    S = np.full(L, 10)
    S[CBD] = 0
    S[0] += H.sum() - S.sum()
    T = np.tile(np.abs(np.arange(L) - CBD).astype(float), (3, 1))
    res = solve_frechet(
        H=H, S=S, y=np.array([100.0, 50.0, 10.0]), T=T,
        alpha=np.array([1.0, 1.0, 1.0]),
        rho=np.array([1.0, 1.0, 1.0]),
        lambda_h=np.array([1.0, 1.0, 1.0]),  # λ homogéneo para que converja
        beta=1.0, tol=1e-6, max_iter=2000,
    )
    assert res.converged


def test_alpha_mas_alto_atrae_cerca_del_cbd() -> None:
    """Un estrato con α más alto penaliza más el transporte y debería concentrarse
    más cerca del CBD que uno con α bajo."""
    cfg = LandUseConfig(
        H_por_estrato=(300, 300, 300),
        estratos=(
            LandUseStratumConfig(y=100.0, alpha=3.0, rho=1.0),  # alto α = no quiere viajar
            LandUseStratumConfig(y=50.0, alpha=1.0, rho=1.0),
            LandUseStratumConfig(y=10.0, alpha=0.5, rho=1.0),   # bajo α = indiferente
        ),
        beta=1.0,
        max_iter=2000,
    )
    rng = np.random.default_rng(42)
    city = LandUseCity.build(L=101, CBD=50, cfg=cfg, rng=rng)
    conteos = city.hogares_por_parcela_estrato()  # (3, 101)

    # Distancia media al CBD por estrato
    dist = np.abs(np.arange(101) - 50)
    dist_media = np.array([np.sum(conteos[h] * dist) / max(conteos[h].sum(), 1) for h in range(3)])
    # α=3.0 (h=0) debería estar estrictamente más cerca que α=0.5 (h=2)
    assert dist_media[0] < dist_media[2], f"dist_media={dist_media}"
