"""La subasta heteroscedástica — Train (2009) §4.5, Bhat (1995).

El logit cerrado supone varianza idéntica de las pujas entre estratos. Eso deja
de valer en cuanto los `λ_h` difieren, porque al despejar el precio el término
aleatorio queda dividido por `λ_h` (Martínez, ec. 4.3). Estos tests fijan las
tres propiedades que hacen que valga la pena tener el modelo:

1. **Reduce** al logit cerrado cuando los λ son uniformes — si no, el modelo
   nuevo estaría cambiando la línea base por la puerta de atrás.
2. **Conserva** los hogares por estrato, que es la ec. (5.1) de Martínez y la
   condición que el punto fijo resuelve.
3. **Identifica** λ: bajo la forma cerrada mover λ es EXACTAMENTE re-escalar
   (α, ρ) —max|ΔQ| = 0, ver `test_lambda_equivale_exactamente_a_reescalar…`— y
   bajo HEV deja de serlo. Es la razón de ser del cambio.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.special import logsumexp

from titirilquen_core.land_use.equilibrium import solve_logit, solve_subasta
from titirilquen_core.land_use.hev import e_max_hev, q_hev

L, CBD, LARGO_KM = 121, 60, 20.0
DX = LARGO_KM / L
#: Euler-Mascheroni. El máximo esperado de Gumbel supera a su parámetro de
#: localización en exactamente γ/β (Martínez, ec. 4.27).
GAMMA = 0.5772156649015329


def _escenario() -> dict:
    H = np.array([12000, 12000, 12000])
    idx = np.arange(L)
    w = np.exp(-0.5 * ((idx - CBD) / 30.0) ** 2)
    w[CBD] = 0.0
    S = np.floor(w / w.sum() * H.sum()).astype(int)
    S[0] += int(H.sum() - S.sum())
    d_km = np.abs(idx - CBD).astype(float) * DX
    return {
        "H": H,
        "S": S,
        "y": np.array([3.5e6, 1.5e6, 0.5e6]),
        "T": np.tile(d_km / 30.0 * 60.0, (3, 1)),
        "alpha": np.array([6.5, 6.0, 5.5]),
        "rho": np.full(3, 0.0025),
        "beta": 1.0,
        "tol": 1e-8,
        "max_iter": 3000,
        "ancho_celda_km": DX,
    }


# --- el kernel de cuadratura ------------------------------------------------


@pytest.mark.parametrize("beta", [0.3, 1.0, 3.0])
def test_q_hev_reproduce_la_forma_cerrada_con_theta_comun(beta: float) -> None:
    """Con una sola escala, la integral de Bhat da la ec. (4.26) de Martínez.

    Es la validación del kernel numérico: si esto falla, la cuadratura está mal
    y cualquier resultado heteroscedástico es ruido.
    """
    rng = np.random.default_rng(7)
    H = np.array([33300.0, 20000.0, 46700.0])
    w_det = rng.normal(0.0, 2.0, size=(3, 41))
    theta = np.full(3, 1.0 / beta)

    obtenido = q_hev(w_det + (theta * np.log(H))[:, None], theta)
    lg = np.log(H)[:, None] + beta * w_det
    esperado = np.exp(lg - logsumexp(lg, axis=0)[None, :])

    assert np.max(np.abs(obtenido - esperado)) < 1e-12


@pytest.mark.parametrize("beta", [0.5, 1.0, 2.0])
def test_e_max_hev_supera_a_la_localizacion_en_gamma_sobre_beta(beta: float) -> None:
    """`E[máx] = p_i + γ/β` con escala común — ec. (4.27) de Martínez.

    Valida a la vez el nivel y que la diferencia sea una CONSTANTE (desviación
    nula entre parcelas): es lo que permite afirmar que el precio del HEV y el
    de la rama cerrada difieren sólo en el cero arbitrario.
    """
    rng = np.random.default_rng(11)
    H = np.array([33300.0, 33300.0, 33300.0])
    w_det = rng.normal(0.0, 2.0, size=(3, 41))
    theta = np.full(3, 1.0 / beta)

    p_hev = e_max_hev(w_det + (theta * np.log(H))[:, None], theta)
    p_cerrado = logsumexp(np.log(H)[:, None] + beta * w_det, axis=0) / beta
    brecha = p_hev - p_cerrado

    assert brecha.std() < 1e-9, "la brecha depende de la parcela: no es una constante"
    assert brecha.mean() == pytest.approx(GAMMA / beta, abs=1e-6)


# --- el solver --------------------------------------------------------------


@pytest.mark.parametrize("lam", [0.5, 1.0, 2.0])
def test_hev_reduce_al_logit_cuando_lambda_es_uniforme(lam: float) -> None:
    """Con λ uniforme el despacho tiene que ir a la forma cerrada, EXACTA.

    No «parecido»: idéntico. Si no lo fuera, activar el modelo nuevo movería en
    silencio la calibración y la línea base de todo el simulador.
    """
    esc = _escenario()
    lams = np.full(3, lam)
    assert (
        np.max(np.abs(solve_subasta(lambda_h=lams, **esc).Q - solve_logit(lambda_h=lams, **esc).Q))
        == 0.0
    )


@pytest.mark.parametrize("lams", [(0.8, 1.0, 1.25), (0.5, 1.0, 2.0)])
def test_el_hev_conserva_los_hogares_por_estrato(lams: tuple[float, ...]) -> None:
    """`Σ_i S_i·Q_hi = H_h` — la ec. (5.1) de Martínez, «todo hogar se localiza».

    Es la condición que el punto fijo resuelve, así que verificarla es verificar
    que el balanceo llegó de verdad y no se quedó en un punto cualquiera.
    """
    esc = _escenario()
    r = solve_subasta(lambda_h=np.array(lams), **esc)
    assert r.converged, f"el punto fijo no convergió en {r.iterations} iteraciones"
    colocados = r.Q @ np.asarray(esc["S"], dtype=float)
    assert np.allclose(colocados / esc["H"], 1.0, atol=1e-6)


@pytest.mark.parametrize("lam", [0.6, 1.6])
def test_bajo_hev_lambda_deja_de_ser_reescalar_alpha_y_rho(lam: float) -> None:
    """LA razón de ser del modelo: λ queda identificado.

    Bajo la forma cerrada las dos vías dan `max|ΔQ| = 0` exacto (D-08), porque la
    puja es `y + f/λ` y `f` es lineal en α y ρ. Bajo HEV λ mueve ADEMÁS la escala
    del ruido, que la re-escala de preferencias no toca, así que las dos vías
    dejan de coincidir. Sin esta propiedad, implementar HEV no compraría nada.
    """
    esc = _escenario()
    via_lambda = solve_subasta(lambda_h=np.array([lam, 1.0, 1.0]), **esc)

    reescalado = dict(esc)
    reescalado["alpha"] = np.array([esc["alpha"][0] / lam, esc["alpha"][1], esc["alpha"][2]])
    reescalado["rho"] = np.array([esc["rho"][0] / lam, esc["rho"][1], esc["rho"][2]])
    via_preferencias = solve_subasta(lambda_h=np.ones(3), **reescalado)

    assert np.max(np.abs(via_lambda.Q - via_preferencias.Q)) > 1e-3
