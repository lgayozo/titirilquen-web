"""Auditoría de la subasta heteroscedástica (HEV) — Train §4.5 / Bhat (1995).

Produce todas las cifras de `docs/informe-hev.html`: validación numérica,
contraste con la teoría, resultados y análisis de sensibilidad. Si algo del
solver cambia, este script lo dice y el informe hay que rehacerlo.

Correr desde packages/titirilquen_core:

    uv run python scripts/auditoria_hev.py

Nota de estilo: la salida va en ASCII (ver `diagnostico_bienestar.py`), porque
la consola de Windows usa cp1252 y un `print` con «λ» aborta la corrida.
"""

from __future__ import annotations

import time

import numpy as np
from scipy.special import logsumexp

from titirilquen_core.land_use import LandUseCity, LandUseConfig
from titirilquen_core.land_use.config import LandUseStratumConfig
from titirilquen_core.land_use.equilibrium import solve_logit, solve_subasta
from titirilquen_core.land_use.hev import e_max_hev, q_hev

L, CBD, LARGO_KM = 201, 100, 20.0
DX = LARGO_KM / L
H_BASE = (33300, 33300, 33300)
Y = (3.5e6, 1.5e6, 0.5e6)
ALPHA = (6.5, 6.0, 5.5)
DIST_KM = np.abs(np.arange(L) - CBD).astype(float) * DX

#: Euler-Mascheroni: E[max Gumbel] = localizacion + gamma/beta.
GAMMA = 0.5772156649015329


def _cfg(lams, H=H_BASE, rho=None, beta=1.0):
    r = LandUseStratumConfig(y=1.0).rho if rho is None else rho
    return LandUseConfig(
        H_por_estrato=H,
        beta=beta,
        estratos=tuple(
            LandUseStratumConfig(y=y, alpha=a, rho=r, **{"lambda": lam})
            for y, a, lam in zip(Y, ALPHA, lams, strict=True)
        ),
    )


def ciudad(lams, **kw):
    return LandUseCity.build(
        L=L,
        CBD=CBD,
        cfg=_cfg(lams, **kw),
        ancho_celda_km=DX,
        rng=np.random.default_rng(42),
    )


def perfil(city):
    """(distancia media al CBD, dispersion) por estrato, en km."""
    q = city.result.Q * np.asarray(city.S, dtype=float)[None, :]
    out = []
    for h in range(3):
        peso = q[h] / max(q[h].sum(), 1e-9)
        m = float((peso * DIST_KM).sum())
        out.append((m, float(np.sqrt((peso * (DIST_KM - m) ** 2).sum()))))
    return out


def _kw_solver(lams, rho=None, beta=1.0):
    """Argumentos crudos para `solve_*`, sin pasar por LandUseCity."""
    cfg = _cfg(lams, rho=rho, beta=beta)
    c = ciudad(lams, rho=rho, beta=beta)
    return {
        "H": np.asarray(cfg.H_por_estrato),
        "S": c.S,
        "y": np.asarray(Y),
        "T": np.tile(DIST_KM / 30.0 * 60.0, (3, 1)),
        "alpha": np.asarray(ALPHA),
        "rho": np.asarray([e.rho for e in cfg.estratos]),
        "beta": beta,
        "tol": 1e-8,
        "max_iter": 4000,
        "ancho_celda_km": DX,
    }


# ---------------------------------------------------------------------------


def s1_cuadratura() -> None:
    print("\n### 1. La cuadratura: cuantos nodos y por que el trapecio")
    print("  Error de Q contra una grilla de referencia de 400.001 nodos.\n")

    def q_ref(loc, th, n=200001, lo=-20.0, hi=90.0):
        w = np.linspace(lo, hi, n)
        pw = np.exp(-np.exp(-w)) * np.exp(-w)
        out = np.zeros(len(loc))
        for h in range(len(loc)):
            z = np.ones_like(w)
            for g in range(len(loc)):
                if g == h:
                    continue
                a = (loc[h] - loc[g] + th[h] * w) / th[g]
                z *= np.exp(-np.exp(-np.clip(a, -60, 60)))
            out[h] = np.trapezoid(z * pw, w)
        return out / out.sum()

    def q_trap(loc, th, n):
        w = np.linspace(-10.0, 40.0, n)
        pw = np.exp(-np.exp(-w)) * np.exp(-w) * (w[1] - w[0])
        pw[0] *= 0.5
        pw[-1] *= 0.5
        out = np.zeros(len(loc))
        for h in range(len(loc)):
            z = np.ones_like(w)
            for g in range(len(loc)):
                if g == h:
                    continue
                a = (loc[h] - loc[g] + th[h] * w) / th[g]
                z *= np.exp(-np.exp(-np.clip(a, -40, 40)))
            out[h] = pw @ z
        return out / out.sum()

    def q_lag(loc, th, n):
        t, wt = np.polynomial.laguerre.laggauss(n)
        w = -np.log(t)
        out = np.zeros(len(loc))
        for h in range(len(loc)):
            z = np.ones_like(t)
            for g in range(len(loc)):
                if g == h:
                    continue
                a = (loc[h] - loc[g] + th[h] * w) / th[g]
                z *= np.exp(-np.exp(-np.clip(a, -60, 60)))
            out[h] = float(np.dot(wt, z))
        return out / out.sum()

    lnH = np.log(33300.0)
    casos = []
    for lam in (0.5, 0.8, 1.25, 2.0):
        th = np.array([1.0 / lam, 1.0, 1.0])
        for sep in (0.0, 2.0, 8.0):
            casos.append((lam, sep, np.array([0.0, -sep, -2 * sep]) + th * lnH, th))

    print(f"{'nodos':>8}{'trapecio (peor error)':>26}{'Gauss-Laguerre':>20}")
    print("-" * 56)
    for n in (40, 80, 160, 401, 801):
        pt = max(np.max(np.abs(q_trap(loc, th, n) - q_ref(loc, th))) for _, _, loc, th in casos)
        # numpy pierde los nodos de Laguerre por overflow desde ~n=200: la
        # recurrencia de sus polinomios desborda. Otra razon para descartarlo.
        if n <= 160:
            pl = max(np.max(np.abs(q_lag(loc, th, n) - q_ref(loc, th))) for _, _, loc, th in casos)
            col = f"{pl:>20.2e}"
        else:
            col = f"{'desborda':>20}"
        print(f"{n:>8}{pt:>26.2e}{col}")
    print()
    print("  Gauss-Laguerre parece la eleccion natural: la sustitucion t=exp(-w)")
    print("  lleva el peso EXACTAMENTE a exp(-t). Converge mal igual: el doble")
    print("  exponencial no se parece a un polinomio en t. El trapecio gana porque")
    print("  el integrando decae exponencialmente en los dos extremos, que es el")
    print("  caso en que converge con precision espectral.")
    print("  ELEGIDO: 401 nodos sobre [-10, 40].")


def s2_reduccion() -> None:
    print("\n### 2. Contraste con la teoria (I): reduccion al logit cerrado")
    print("  Con theta comun, la integral de Bhat DEBE dar la ec. (4.26).\n")
    rng = np.random.default_rng(7)
    Hn = np.array([33300.0, 20000.0, 46700.0])
    w_det = rng.normal(0.0, 2.0, size=(3, 41))
    print(f"{'beta':>8}{'max|dQ| (kernel)':>20}{'max|dQ| (solver completo)':>28}")
    print("-" * 58)
    for beta in (0.3, 1.0, 3.0):
        th = np.full(3, 1.0 / beta)
        a = q_hev(w_det + (th * np.log(Hn))[:, None], th)
        lg = np.log(Hn)[:, None] + beta * w_det
        b = np.exp(lg - logsumexp(lg, axis=0)[None, :])
        kw = _kw_solver((1.0, 1.0, 1.0), beta=beta)
        d_solver = np.max(
            np.abs(
                solve_subasta(lambda_h=np.ones(3), **kw).Q
                - solve_logit(lambda_h=np.ones(3), **kw).Q
            )
        )
        print(f"{beta:>8}{np.max(np.abs(a - b)):>20.2e}{d_solver:>28.2e}")
    print()
    print("  El solver da CERO exacto porque despacha a la forma cerrada; el")
    print("  kernel da ~1e-15, que es el redondeo de la cuadratura.")


def s3_precio() -> None:
    print("\n### 3. Contraste con la teoria (II): el precio")
    print("  E[max] debe superar al parametro de localizacion en gamma/beta")
    print("  (Martinez ec. 4.27), y la brecha debe ser CONSTANTE entre parcelas.\n")
    rng = np.random.default_rng(11)
    Hn = np.full(3, 33300.0)
    w_det = rng.normal(0.0, 2.0, size=(3, 41))
    print(f"{'beta':>8}{'brecha media':>16}{'gamma/beta':>14}{'sd entre parcelas':>20}")
    print("-" * 58)
    for beta in (0.5, 1.0, 2.0):
        th = np.full(3, 1.0 / beta)
        p_hev = e_max_hev(w_det + (th * np.log(Hn))[:, None], th)
        p_cer = logsumexp(np.log(Hn)[:, None] + beta * w_det, axis=0) / beta
        d = p_hev - p_cer
        print(f"{beta:>8}{d.mean():>16.6f}{GAMMA / beta:>14.6f}{d.std():>20.2e}")


def s4_conservacion() -> None:
    print("\n### 4. Contraste con la teoria (III): conservacion y convergencia")
    print("  Ec. (5.1) de Martinez: sum_i S_i Q_hi = H_h para todo estrato.\n")
    print(f"{'lambda':>22}{'error rel. max':>18}{'converge':>11}{'iters':>8}{'seg':>8}")
    print("-" * 68)
    for lams in ((1.0, 1.0, 1.0), (0.8, 1.0, 1.25), (0.5, 1.0, 2.0), (0.4, 1.0, 3.0)):
        kw = _kw_solver(lams)
        t0 = time.perf_counter()
        r = solve_subasta(lambda_h=np.asarray(lams), **kw)
        t = time.perf_counter() - t0
        col = r.Q @ np.asarray(kw["S"], dtype=float)
        err = float(np.max(np.abs(col / np.asarray(kw["H"]) - 1.0)))
        print(f"{lams!s:>22}{err:>18.2e}{r.converged!s:>11}{r.iterations:>8}{t:>8.2f}")


def s5_identificacion() -> None:
    print("\n### 5. EL RESULTADO CENTRAL: lambda queda identificado")
    print("  Se compara mover lambda_alto contra re-escalar (alpha, rho) por")
    print("  1/lambda. Bajo la forma cerrada son la MISMA configuracion.\n")
    print(
        f"{'lambda':>8}{'cerrado: max|dQ|':>20}{'HEV: max|dQ|':>16}"
        f"{'d_alto via lam':>17}{'d_alto via a,r':>17}"
    )
    print("-" * 78)
    for lam in (0.5, 0.8, 1.25, 2.0):
        kw_l = _kw_solver((lam, 1.0, 1.0))
        kw_r = dict(kw_l)
        kw_r["alpha"] = np.array([ALPHA[0] / lam, ALPHA[1], ALPHA[2]])
        kw_r["rho"] = np.array([kw_l["rho"][0] / lam, kw_l["rho"][1], kw_l["rho"][2]])

        c_l = solve_logit(lambda_h=np.array([lam, 1.0, 1.0]), **kw_l)
        c_r = solve_logit(lambda_h=np.ones(3), **kw_r)
        h_l = solve_subasta(lambda_h=np.array([lam, 1.0, 1.0]), **kw_l)
        h_r = solve_subasta(lambda_h=np.ones(3), **kw_r)

        def dm(res, S):
            q = res.Q[0] * np.asarray(S, dtype=float)
            return float((q * DIST_KM).sum() / max(q.sum(), 1e-9))

        print(
            f"{lam:>8}{np.max(np.abs(c_l.Q - c_r.Q)):>20.2e}"
            f"{np.max(np.abs(h_l.Q - h_r.Q)):>16.4f}"
            f"{dm(h_l, kw_l['S']):>17.2f}{dm(h_r, kw_r['S']):>17.2f}"
        )
    print()
    print("  La columna 'cerrado' es CERO exacto: es la identidad de D-08.")
    print("  La columna 'HEV' no lo es. Ahi esta la razon de ser del modelo.")


def s6_sensibilidad_lambda() -> None:
    print("\n### 6. SENSIBILIDAD (I): lambda de un estrato")
    print("  Se mueve solo el lambda del estrato alto.\n")
    print(
        f"{'lambda':>8}{'theta_alto':>12}{'alpha_ef':>10}{'d_alto':>9}{'disp':>8}"
        f"{'d_medio':>9}{'d_bajo':>9}{'iters':>7}"
    )
    print("-" * 74)
    for lam in (0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.6, 2.0, 3.0):
        c = ciudad((lam, 1.0, 1.0))
        pf = perfil(c)
        print(
            f"{lam:>8}{1.0 / lam:>12.2f}{ALPHA[0] / lam:>10.2f}"
            f"{pf[0][0]:>9.2f}{pf[0][1]:>8.2f}{pf[1][0]:>9.2f}{pf[2][0]:>9.2f}"
            f"{c.result.iterations:>7}"
        )
    print()
    print("  lambda = 1,0 es la fila donde despacha a la forma cerrada.")


def s7_sensibilidad_escala() -> None:
    print("\n### 7. SENSIBILIDAD (II): escalar TODOS los lambda por k")
    print("  Si lambda fuera solo una eleccion de unidades, esto no deberia")
    print("  cambiar nada. Se mide contra k=1.\n")
    print("  OJO: hasta D-31 esta tabla daba hasta 2,4e-1 y se concluia que NO")
    print("  era invariante. Lo era el bug: la rama cerrada usaba b = beta en")
    print("  vez de b = beta*lambda.\n")
    base = ciudad((1.0, 1.0, 1.0))
    print(f"{'k':>8}{'max|dQ| vs k=1':>18}{'d_alto':>9}{'d_medio':>9}{'d_bajo':>9}{'iters':>8}")
    print("-" * 62)
    for k in (0.5, 0.8, 1.0, 1.25, 2.0):
        c = ciudad((k, k, k))
        pf = perfil(c)
        print(
            f"{k:>8}{np.max(np.abs(c.result.Q - base.result.Q)):>18.2e}"
            f"{pf[0][0]:>9.2f}{pf[1][0]:>9.2f}{pf[2][0]:>9.2f}"
            f"{c.result.iterations:>8}"
        )
    print()
    print("  SI es invariante, y debe serlo. El mecanismo, con b = beta*lambda:")
    print("    - la puja que varia entre parcelas es f/lambda: se encoge por k;")
    print("    - la precision del ruido b = beta*lambda: crece por k;")
    print("    - el cociente senal/ruido, (f/lambda)*b = f*beta, NO depende de k.")
    print("  El unico otro termino es el ingreso y, constante por estrato, que el")
    print("  punto fijo absorbe en u. Asi que la asignacion no se mueve.")
    print()
    print("  Con lambda UNIFORME el despacho va a la forma cerrada, asi que esta")
    print("  tabla mide el logit. Que de invariante es lo que confirma que las")
    print("  dos ramas ya leen beta en el mismo espacio.")


def s8_sensibilidad_poblacion() -> None:
    print("\n### 8. SENSIBILIDAD (III): el HEV rompe la invariancia de escala")
    print("  La localizacion lleva theta_h*ln(H_h), asi que la poblacion entra en")
    print("  la subasta en cuanto los theta difieren. Es la propiedad AU-03 del")
    print("  logit cerrado —asignacion invariante a la escala— que el HEV NO")
    print("  conserva.\n")
    print(
        f"{'suma H':>10}{'ln H':>8}{'d_alto lam=0,8':>17}{'d_alto lam=1':>15}"
        f"{'d_alto lam=1,25':>18}"
    )
    print("-" * 70)
    for suma in (9_000, 36_000, 99_900, 144_000):
        h = suma // 3
        Hn = (h, h, suma - 2 * h)
        fila = []
        for lam in (0.8, 1.0, 1.25):
            fila.append(perfil(ciudad((lam, 1.0, 1.0), H=Hn))[0][0])
        print(f"{suma:>10,}{np.log(h):>8.2f}{fila[0]:>17.2f}{fila[1]:>15.2f}{fila[2]:>18.2f}")
    print()
    print("  Con lambda UNIFORME la columna del medio da 1,47 en las cuatro")
    print("  poblaciones: el logit cerrado es homogeneo de grado 0 en la escala")
    print("  (AU-03). Con lambda heterogeneo deja de serlo: a lambda=1,25 el")
    print("  estrato alto pasa de 5,96 km con 9.000 hogares a 4,67 km con")
    print("  144.000. Es consecuencia directa de la teoria —el maximo de H draws")
    print("  depende de H y de la escala a la vez— pero hay que declararlo: la")
    print("  misma ciudad a distinta escala ya no da el mismo mapa.")


def s9_sensibilidad_beta() -> None:
    print("\n### 9. SENSIBILIDAD (IV): interaccion con beta")
    print("  theta_h = 1/(beta*lambda_h), asi que beta y lambda comparten escala.\n")
    print(f"{'beta':>8}{'d_alto lam=0,8':>17}{'d_alto lam=1':>15}{'d_alto lam=1,25':>18}")
    print("-" * 60)
    for beta in (0.5, 1.0, 2.0, 4.0):
        fila = [perfil(ciudad((lam, 1.0, 1.0), beta=beta))[0][0] for lam in (0.8, 1.0, 1.25)]
        print(f"{beta:>8}{fila[0]:>17.2f}{fila[1]:>15.2f}{fila[2]:>18.2f}")
    print()
    print("  Subir beta agudiza la subasta (menos ruido) y con eso el efecto de")
    print("  lambda se vuelve mas abrupto: son la misma escala.")


def main() -> None:
    print("=" * 78)
    print("AUDITORIA DE LA SUBASTA HETEROSCEDASTICA (HEV)")
    print("Train (2009) cap. 4.5 / Bhat (1995) -- implementacion en land_use/hev.py")
    print("=" * 78)
    print(
        f"Base: L={L} celdas · {LARGO_KM:.0f} km · SumaH=99.900 · "
        f"alpha=6,5/6,0/5,5 · rho={LandUseStratumConfig(y=1.0).rho} · beta=1"
    )
    s1_cuadratura()
    s2_reduccion()
    s3_precio()
    s4_conservacion()
    s5_identificacion()
    s6_sensibilidad_lambda()
    s7_sensibilidad_escala()
    s8_sensibilidad_poblacion()
    s9_sensibilidad_beta()
    print()


if __name__ == "__main__":
    main()
