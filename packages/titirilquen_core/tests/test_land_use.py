from __future__ import annotations

import numpy as np
import pytest

from titirilquen_core.land_use import (
    LandUseCity,
    LandUseConfig,
    LandUseStratumConfig,
    generar_oferta_normal,
    solve_heteroscedastic,
    solve_logit,
)


def _toy_scenario(lam: np.ndarray):
    L, CBD = 81, 40
    idx = np.arange(L)
    S = np.maximum(
        1, np.round(np.exp(-0.5 * ((idx - CBD) / 20.0) ** 2) * 100)
    ).astype(int)
    S[CBD] = 0
    H = np.array([2000, 2000, 2000])
    S[0] += int(H.sum() - S.sum())
    T = np.tile(np.abs(idx - CBD).astype(float), (3, 1))
    return dict(
        H=H, S=S, y=np.array([120.0, 50.0, 10.0]), T=T,
        alpha=np.array([1.3, 1.2, 1.1]), rho=np.array([1.0, 1.0, 1.0]),
        lambda_h=lam, beta=1.0, tol=1e-9, max_iter=20000,
    )


def test_heteroscedastic_reduce_a_logit_con_lambda_1() -> None:
    """Con λ_h = 1 ∀h, el logit heteroscedástico coincide exactamente con el logit."""
    args = _toy_scenario(np.array([1.0, 1.0, 1.0]))
    rl = solve_logit(**args)
    rh = solve_heteroscedastic(**args)
    np.testing.assert_allclose(rl.u, rh.u, atol=1e-9)
    np.testing.assert_allclose(rl.Q, rh.Q, atol=1e-9)


def test_heteroscedastic_invariante_a_escala_comun_de_lambda() -> None:
    """Escalar TODOS los λ por un factor común no debe cambiar la asignación
    (propiedad de consistencia que el logit NO tiene)."""
    base = solve_heteroscedastic(**_toy_scenario(np.array([1.0, 1.0, 1.0]))).Q
    for k in (0.5, 2.0, 4.0):
        Qk = solve_heteroscedastic(**_toy_scenario(np.array([k, k, k]))).Q
        np.testing.assert_allclose(Qk, base, atol=1e-6)


def test_heteroscedastic_converge_con_lambda_heterogeneo() -> None:
    res = solve_heteroscedastic(**_toy_scenario(np.array([2.0, 1.0, 0.5])))
    assert res.converged
    col_sum = res.Q.sum(axis=0)
    expected = np.where(_toy_scenario(np.array([2.0, 1.0, 0.5]))["S"] > 0, 1.0, 0.0)
    np.testing.assert_allclose(col_sum, expected, atol=1e-6)


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


def test_q_conserva_hogares_por_estrato_con_H_desigual() -> None:
    """Σ_i S_i·Q[h,i] = H_h en el equilibrio (Suelo.tex ec. 3; ver D-25).

    Regresión: el Q devuelto omitía la ponderación H_h de la subasta, así que
    con H heterogéneo la composición no conservaba los hogares por estrato
    (p.ej. H=(1000,4000,5000) daba ≈(2287,3149,4565))."""
    args = _toy_scenario(np.array([1.0, 1.0, 1.0]))
    args["H"] = np.array([1000, 4000, 5000])
    # Recalzar oferta = demanda tras cambiar H.
    diff = int(args["H"].sum() - args["S"].sum())
    args["S"][0] += diff
    for solver in (solve_logit, solve_heteroscedastic):
        res = solver(**args)
        assert res.converged
        hogares = res.Q @ args["S"].astype(float)
        np.testing.assert_allclose(hogares, args["H"].astype(float), rtol=1e-6)


# ---------------------------------------------------------------------------
# D-26: invariancia a la resolución de la grilla (unidades físicas)
# ---------------------------------------------------------------------------

from titirilquen_core.coupled_metrics import _theil  # noqa: E402


def _cfg_default_fisica() -> LandUseConfig:
    """Defaults del paquete (α en utiles/min, ρ en utiles/(hog/km), y en $/mes)
    con la población de referencia del frontend."""
    return LandUseConfig(H_por_estrato=(1000, 4000, 5000))


def test_invariancia_a_la_resolucion_de_la_grilla() -> None:
    """Misma ciudad FÍSICA (20 km), distinta grilla ⇒ los indicadores deben
    converger (D-26). La grilla es una decisión numérica, no económica.

    Regresión: con T en índices de celda y ρ sobre hogares/celda, el Theil iba
    de 0.245 (L=101) a 0.658 (L=401) — refinar la grilla equivalía a estirar
    la ciudad."""
    LARGO_KM = 20.0
    theils: list[float] = []
    dists: list[np.ndarray] = []
    for L in (101, 201, 401):
        CBD = L // 2
        city = LandUseCity.build(
            L=L, CBD=CBD, cfg=_cfg_default_fisica(),
            ancho_celda_km=LARGO_KM / L, rng=np.random.default_rng(7),
        )
        assert city.result is not None and city.result.converged
        Q, S = city.result.Q, city.S.astype(float)
        theils.append(_theil(Q))
        dist_km = np.abs(np.arange(L) - CBD) * (LARGO_KM / L)
        NQ = Q * S[None, :]
        dists.append((NQ * dist_km).sum(1) / NQ.sum(1))

    t = np.array(theils)
    assert t.max() - t.min() < 0.02 * t.mean() + 0.01, f"Theil no invariante: {t}"
    d = np.stack(dists)
    assert np.all(np.abs(d - d.mean(axis=0)) < 0.35), f"dist medias no invariantes:\n{d}"


def test_sensibilidad_al_tamano_fisico() -> None:
    """Agrandar la ciudad FÍSICA (más km, misma grilla y población) SÍ debe
    aumentar el sorting: el gradiente α·T pesa más contra el ruido del logit.
    Es el efecto económico real, a diferencia del artefacto de grilla (D-26)."""
    L = 201
    theil_por_largo: dict[float, float] = {}
    for largo in (10.0, 40.0):
        city = LandUseCity.build(
            L=L, CBD=L // 2, cfg=_cfg_default_fisica(),
            ancho_celda_km=largo / L, rng=np.random.default_rng(7),
        )
        assert city.result is not None
        theil_por_largo[largo] = _theil(city.result.Q)
    assert theil_por_largo[40.0] > theil_por_largo[10.0] + 0.1, theil_por_largo


def test_densidad_por_celda_es_oferta_sobre_dx() -> None:
    """La densidad por celda es una CONSECUENCIA de la oferta: dens = S/Δx (ya no
    el gradiente de Clark). Sigue la forma y es 0 donde no hay oferta (el CBD)."""
    L, largo = 201, 20.0
    dx = largo / L
    city = LandUseCity.build(
        L=L, CBD=L // 2, cfg=_cfg_default_fisica(),
        ancho_celda_km=dx, rng=np.random.default_rng(7),
    )
    dens = city.densidad_por_celda()
    S = np.asarray(city.S, dtype=float)
    assert np.allclose(dens, S / dx)  # dens = S/Δx exacto
    assert dens[city.cbd_index] == 0.0  # CBD sin oferta → 0
    assert np.all((S <= 0) == (dens == 0.0))  # 0 sii S<=0


def test_densidad_y_equilibrio_conservan_hogares() -> None:
    """El equilibrio conserva hogares por estrato: Σ_i S_i·Q[h,i] = H_h (D-25), lo
    que hace que el feed S-based a transporte reparta ΣH exacto. Y como la densidad
    es S/Δx, Σ_i densidad·Δx = ΣS = ΣH — antes, con la densidad de Clark, ese total
    no cuadraba con ΣH (rompía la conservación del feed, audit #5)."""
    L, dx = 201, 20.0 / 201
    city = LandUseCity.build(
        L=L, CBD=L // 2, cfg=_cfg_default_fisica(),
        ancho_celda_km=dx, rng=np.random.default_rng(7),
    )
    assert city.result is not None
    H = np.asarray(_cfg_default_fisica().H_por_estrato, dtype=float)
    # Σ_i S_i·Q[h,i] = H_h (conservación por estrato del equilibrio).
    assert np.allclose(city.result.Q @ city.S.astype(float), H, rtol=1e-6)
    # Σ_i densidad·Δx = ΣH (el total que la densidad de Clark rompía).
    assert np.isclose((city.densidad_por_celda() * dx).sum(), H.sum())


def test_asignacion_no_se_estanca_con_Q_degenerado() -> None:
    """Regresión (gridlock D-24): con Q underfloweado a 0/1 y cuotas agotadas,
    la asignación debe completarse por desborde, no lanzar RuntimeError."""
    from titirilquen_core.land_use.allocation import asignar_hogares_simple

    L, n = 21, 3
    Q = np.zeros((n, L))
    Q[0, 5:16] = 1.0
    Q[2, :5] = 1.0
    Q[2, 16:] = 1.0
    S = np.full(L, 10)
    S[10] = 0
    H = np.array([20, 90, 90])
    parcelas = asignar_hogares_simple(Q=Q, S=S, H=H, rng=np.random.default_rng(1))
    conteo = np.zeros(n, dtype=int)
    for parc in parcelas:
        for h in parc:
            conteo[h - 1] += 1
    np.testing.assert_array_equal(conteo, H)          # cuotas exactas
    assert sum(len(p) for p in parcelas) == int(S.sum())  # capacidad exacta
