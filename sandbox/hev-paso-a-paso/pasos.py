"""Resuelve el caso mínimo paso a paso, imprimiendo cada uno.

    uv run python pasos.py

Deja todo lo que calcula en `salida/traza.json`, que es lo que consumen
`figuras.py` y el informe.
"""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path

import numpy as np

from caso import ESTRATOS, PARCELAS, Caso, caso_base
from subasta import (
    colocados,
    equilibrio,
    exceso,
    localizacion,
    q_hev,
    q_logit,
    resuelve_balanceo,
    resuelve_brent,
)

SALIDA = Path(__file__).parent / "salida"
OUT: dict = {}


def titulo(n: int, txt: str) -> None:
    print(f"\n{'=' * 74}\n  PASO {n} · {txt}\n{'=' * 74}")


def tabla(filas: list[list[str]], cab: list[str]) -> None:
    anchos = [max(len(str(f[k])) for f in [cab, *filas]) for k in range(len(cab))]
    print("  " + "  ".join(str(c).rjust(a) for c, a in zip(cab, anchos, strict=True)))
    print("  " + "  ".join("-" * a for a in anchos))
    for f in filas:
        print("  " + "  ".join(str(v).rjust(a) for v, a in zip(f, anchos, strict=True)))


# --------------------------------------------------------------------------- #
def paso_1_enunciado(caso) -> None:
    titulo(1, "El enunciado")
    print("  Dos estratos pujan por cinco parcelas. Nadie elige: la parcela se la")
    print("  lleva quien mas puja, y las pujas llevan ruido.\n")
    tabla(
        [
            ["S_i (viviendas)", *[f"{v:g}" for v in caso.S]],
            ["T_i (min al CBD)", *[f"{v:g}" for v in caso.T]],
        ],
        ["parcela", *PARCELAS],
    )
    print()
    tabla(
        [
            [
                e,
                f"{caso.H[h]:g}",
                f"{caso.y[h]:g}",
                f"{caso.alpha[h]:g}",
                f"{caso.rho[h]:g}",
                f"{caso.lambda_h[h]:g}",
                f"{caso.theta()[h]:.4f}",
            ]
            for h, e in enumerate(ESTRATOS)
        ],
        ["estrato", "H_h", "y_h", "alpha", "rho", "lambda", "theta"],
    )
    print(f"\n  Oferta total {caso.S.sum():g} = demanda total {caso.H.sum():g}. Tiene que ser")
    print("  asi: sumando las condiciones de equilibrio sobre h, y como las columnas")
    print("  de Q suman 1, queda Sum(S) = Sum(H). Si no se cumple, no hay solucion.\n")

    sc = caso.score()
    tabla(
        [[e, *[f"{v:+.4f}" for v in sc[h]]] for h, e in enumerate(ESTRATOS)],
        ["puja w_hi", *PARCELAS],
    )
    print("\n  El alto puja mas fuerte cerca del CBD y su puja cae mas rapido con la")
    print("  distancia: el gradiente de Alonso esta en los DATOS, no en la solucion.")
    print(f"  Pendiente por parcela:  Alto {np.diff(sc[0]).mean():+.4f}", end="")
    print(f"   Bajo {np.diff(sc[1]).mean():+.4f}")
    OUT["caso"] = {
        "H": caso.H.tolist(),
        "S": caso.S.tolist(),
        "y": caso.y.tolist(),
        "T": caso.T.tolist(),
        "alpha": caso.alpha.tolist(),
        "rho": caso.rho.tolist(),
        "lambda": caso.lambda_h.tolist(),
        "theta": caso.theta().tolist(),
        "score": sc.tolist(),
    }


# --------------------------------------------------------------------------- #
def paso_2_incognitas(caso) -> None:
    titulo(2, "Cuantas incognitas hay de verdad")
    print("  El problema parece tener dos incognitas, u_Alto y u_Bajo. Tiene una.\n")
    print("  (a) La utilidad esta determinada salvo una constante aditiva. Sumarle 5")
    print("      a las dos no cambia ninguna Q, porque solo entran por diferencias:")
    u0 = np.array([0.0, 0.7])
    q0 = q_hev(localizacion(caso, u0), caso.theta())
    q1 = q_hev(localizacion(caso, u0 + 5.0), caso.theta())
    print(f"      max |Q(u) - Q(u+5)| = {np.abs(q0 - q1).max():.2e}")
    print("      Por eso el nucleo normaliza con `u_new -= u_new[0]`. Queda 1 grado")
    print("      de libertad: delta = u_Bajo - u_Alto.\n")
    print("  (b) De las dos ecuaciones de equilibrio, solo una es independiente.")
    print("      La suma de los colocados es SIEMPRE la oferta total, valga lo que")
    print("      valga u, asi que la segunda ecuacion no dice nada nuevo:")
    filas = []
    for d in (-4.0, -1.0, 0.0, 1.0, 4.0):
        c = colocados(caso, np.array([0.0, d]))
        filas.append([f"{d:+.1f}", f"{c[0]:.6f}", f"{c[1]:.6f}", f"{c.sum():.10f}"])
    tabla(filas, ["delta", "coloca Alto", "coloca Bajo", "suma"])
    print(f"\n      La ultima columna es {caso.S.sum():g} exacto en todos los casos.")
    print("      Conclusion: UNA ecuacion escalar, UNA incognita.")
    OUT["invariancia"] = float(np.abs(q0 - q1).max())
    OUT["redundancia"] = filas


# --------------------------------------------------------------------------- #
def paso_3_funcion(caso) -> None:
    titulo(3, "La funcion de exceso")
    print("  g(delta) = (hogares que coloca el Alto) - H_Alto.  Su raiz es el")
    print("  equilibrio. Se tabula en todo el rango para ver que hay una sola:\n")
    ds = np.linspace(-6, 6, 25)
    gs = [exceso(caso, float(d)) for d in ds]
    filas = [[f"{d:+.2f}", f"{g:+.4f}"] for d, g in zip(ds[::3], gs[::3], strict=False)]
    tabla(filas, ["delta", "g(delta)"])
    creciente = all(b > a for a, b in pairwise(gs))
    print(f"\n  Monotona creciente en todo el rango: {creciente}")
    print("  Subir u_Bajo baja la puja del bajo, asi que el alto gana mas. Al ser")
    print("  monotona, la raiz es unica y cualquier metodo que la busque llega a la")
    print("  misma. No hay equilibrios multiples que discutir.")
    d_fino = np.linspace(-8, 8, 601)
    # Segunda pasada fina alrededor de la raiz: el balanceo salta casi todo en
    # el primer paso y las iteradas restantes solo se distinguen con este zoom.
    d_zoom = np.linspace(-0.80, -0.60, 201)
    OUT["curva_exceso"] = {
        "delta": d_fino.tolist(),
        "g": [exceso(caso, float(d)) for d in d_fino],
        "monotona": bool(creciente),
        "zoom_delta": d_zoom.tolist(),
        "zoom_g": [exceso(caso, float(d)) for d in d_zoom],
    }


# --------------------------------------------------------------------------- #
def paso_4_balanceo(caso):
    titulo(4, "El algoritmo del nucleo, iteracion por iteracion")
    print("  u_h <- u_h + theta_h * ln(colocados_h / H_h)\n")
    tr = resuelve_balanceo(caso)
    filas = []
    for k in range(min(len(tr.delta), 12)):
        col = colocados(caso, np.array([0.0, tr.delta[k]]))
        filas.append(
            [
                str(k),
                f"{tr.delta[k]:+.8f}",
                f"{col[0]:.4f}",
                f"{tr.exceso[k]:+.2e}",
                f"{tr.paso[k]:+.2e}" if k < len(tr.paso) else "",
            ]
        )
    tabla(filas, ["it", "delta", "coloca Alto", "exceso", "paso"])
    if len(tr.delta) > 12:
        print(f"  ... {len(tr.delta) - 12} iteraciones mas")
    print(f"\n  Convergio: {tr.convergio} en {tr.iteraciones} iteraciones.")
    print(f"  delta* = {tr.delta[-1]:.12f}   exceso final = {tr.exceso[-1]:+.2e}")
    OUT["balanceo"] = {
        "delta": tr.delta,
        "exceso": tr.exceso,
        "paso": tr.paso,
        "convergio": tr.convergio,
        "iteraciones": tr.iteraciones,
    }
    return tr


# --------------------------------------------------------------------------- #
def paso_5_brent(caso, tr) -> float:
    titulo(5, "Verificacion 1: un algoritmo sin nada en comun")
    print("  Biseccion pura sobre g. No usa el gradiente, ni el logaritmo del paso,")
    print("  ni la estructura del modelo: solo que g cambia de signo.\n")
    d_bis, n = resuelve_brent(caso)
    d_bal = tr.delta[-1]
    tabla(
        [
            ["balanceo (nucleo)", f"{d_bal:.14f}", str(tr.iteraciones)],
            ["biseccion", f"{d_bis:.14f}", str(n)],
        ],
        ["metodo", "delta*", "iteraciones"],
    )
    print(f"\n  Diferencia: {abs(d_bal - d_bis):.2e}")
    print("  Dos algoritmos independientes, el mismo numero. El punto fijo del")
    print("  balanceo ES la raiz de la ecuacion de equilibrio, no un artefacto suyo.")
    OUT["biseccion"] = {"delta": d_bis, "iteraciones": n, "dif": abs(d_bal - d_bis)}
    return d_bis


# --------------------------------------------------------------------------- #
def paso_6_nucleo(caso, d) -> None:
    titulo(6, "Verificacion 2: contra el nucleo de produccion")
    try:
        from titirilquen_core.land_use.equilibrium import solve_subasta
    except ImportError:
        print("  titirilquen_core no esta instalado; se omite. Correr con `uv run`.")
        OUT["nucleo"] = None
        return
    r = solve_subasta(
        H=caso.H,
        S=caso.S,
        y=caso.y,
        T=caso.T,
        alpha=caso.alpha,
        rho=caso.rho,
        lambda_h=caso.lambda_h,
        beta=caso.beta,
    )
    Q_demo, _, _ = equilibrio(caso, d)
    d_nucleo = float(r.u[1] - r.u[0])
    print(f"  delta* demo   = {d:.12f}")
    print(f"  delta* nucleo = {d_nucleo:.12f}")
    print(f"  diferencia    = {abs(d - d_nucleo):.2e}")
    print(f"\n  max |Q_demo - Q_nucleo| = {np.abs(Q_demo - r.Q).max():.2e}")
    print("\n  El demo reimplementa la matematica desde cero y no importa nada del")
    print("  nucleo, asi que esto mide que las dos implementaciones coinciden.")
    OUT["nucleo"] = {
        "delta": d_nucleo,
        "dif_delta": abs(d - d_nucleo),
        "dif_Q": float(np.abs(Q_demo - r.Q).max()),
        "Q": r.Q.tolist(),
    }


# --------------------------------------------------------------------------- #
def paso_7_montecarlo(caso, d, reps: int = 100_000, semilla: int = 42) -> None:
    titulo(7, "Verificacion 3: la subasta simulada de verdad")
    print(f"  {reps:,} repeticiones. En cada una, cada uno de los H_h hogares de cada")
    print("  estrato saca su propio ruido Gumbel y puja; gana la parcela el hogar")
    print("  con la puja mas alta. Se cuenta con que frecuencia gana cada estrato.\n")
    rng = np.random.default_rng(semilla)
    u = np.array([0.0, d])
    sc = caso.score() - u[:, None]
    th = caso.theta()
    H = caso.H.astype(int)
    freq = np.zeros((2, len(caso.S)))
    for i in range(len(caso.S)):
        maximos = np.empty((2, reps))
        for h in range(2):
            # `H_h` pujas independientes por repeticion; nos quedamos con la mayor.
            # Se trocea para no pedir 100.000 x 60 floats de una.
            top = np.empty(reps)
            paso = 25_000
            for a in range(0, reps, paso):
                b = min(a + paso, reps)
                g = rng.gumbel(loc=sc[h, i], scale=th[h], size=(b - a, H[h]))
                top[a:b] = g.max(axis=1)
            maximos[h] = top
        gana = maximos.argmax(axis=0)
        for h in range(2):
            freq[h, i] = (gana == h).mean()

    Q, _, _ = equilibrio(caso, d)
    tabla(
        [
            ["Q cuadratura  Alto", *[f"{v:.4f}" for v in Q[0]]],
            ["frecuencia MC Alto", *[f"{v:.4f}" for v in freq[0]]],
            ["diferencia", *[f"{v:+.4f}" for v in (freq[0] - Q[0])]],
        ],
        ["", *PARCELAS],
    )
    err = float(np.abs(freq - Q).max())
    print(f"\n  Error maximo: {err:.4f}   (esperado ~1/sqrt(n) = {1 / np.sqrt(reps):.4f})")
    print("\n  Esto verifica ADEMAS el corrimiento theta*ln(H): la simulacion saca")
    print("  las H_h pujas una por una y nunca usa esa formula.")
    OUT["montecarlo"] = {"reps": reps, "freq": freq.tolist(), "err": err}


# --------------------------------------------------------------------------- #
def paso_8_precios(caso, d) -> None:
    titulo(8, "Los precios y la asignacion de equilibrio")
    Q, col, p = equilibrio(caso, d)
    tabla(
        [
            ["Q Alto", *[f"{v:.4f}" for v in Q[0]]],
            ["Q Bajo", *[f"{v:.4f}" for v in Q[1]]],
            ["hogares Alto", *[f"{v:.2f}" for v in Q[0] * caso.S]],
            ["hogares Bajo", *[f"{v:.2f}" for v in Q[1] * caso.S]],
            ["precio p_i", *[f"{v:+.4f}" for v in p]],
        ],
        ["", *PARCELAS],
    )
    print(f"\n  Coloca Alto {col[0]:.6f} de {caso.H[0]:g}   Bajo {col[1]:.6f} de {caso.H[1]:g}")
    print(f"  Gradiente de precio P1->P5: {p[-1] - p[0]:+.4f}")
    print("  Negativo = el suelo vale mas cerca del CBD, que es Alonso.")
    OUT["equilibrio"] = {
        "Q": Q.tolist(),
        "colocados": col.tolist(),
        "precio": p.tolist(),
        "grad": float(p[-1] - p[0]),
    }


# --------------------------------------------------------------------------- #
def _km_medios(caso, Q) -> float:
    """Distancia media al CBD del estrato alto, ponderada por hogares."""
    km = np.arange(1, 6, dtype=float)
    return float((Q[0] * caso.S @ km) / (Q[0] @ caso.S))


def paso_9_lambda() -> None:
    titulo(9, "Por que lambda no significaba nada, y ahora si")
    print("  El experimento correcto no es «mover lambda y ver si algo cambia»:")
    print("  bajo la forma cerrada tambien cambia, porque lambda entra por")
    print("  score = y + f/lambda. Lo que hay que mostrar es que bajo la forma")
    print("  cerrada ese efecto es INDISTINGUIBLE de re-escalar alpha y rho.\n")

    #: Caso A: lambda heterogeneo, preferencias originales. Se elige un
    #: contraste fuerte (4x) para que el efecto se vea; con 0,8/1,25 existe
    #: igual pero queda en 0,002 y no se distingue de un detalle.
    #:
    #: OJO con el orden: la utilidad marginal del ingreso es DECRECIENTE en el
    #: ingreso, asi que lambda_alto < lambda_bajo. Al reves se invierte el valor
    #: del tiempo (VoT = alpha/lambda), que en los datos es mayor para el rico.
    A = caso_base((0.5, 2.0))
    #: Caso B: lambda uniforme, preferencias YA divididas por lambda. Por
    #: construccion tiene el mismo `score` que A, pero theta uniforme.
    B = Caso(
        H=A.H,
        S=A.S,
        y=A.y,
        T=A.T,
        alpha=A.alpha / A.lambda_h,
        rho=A.rho / A.lambda_h,
        lambda_h=np.array([1.0, 1.0]),
    )
    dif_score = float(np.abs(A.score() - B.score()).max())
    print(f"  (a) Los dos casos tienen la MISMA puja deterministica: max diff = {dif_score:.2e}")
    tabla(
        [
            [
                "A: lambda hetero",
                f"{A.lambda_h[0]:g} / {A.lambda_h[1]:g}",
                *[f"{v:g}" for v in A.alpha],
            ],
            [
                "B: lambda uniforme",
                f"{B.lambda_h[0]:g} / {B.lambda_h[1]:g}",
                *[f"{v:g}" for v in B.alpha],
            ],
        ],
        ["caso", "lambda A/B", "alpha Alto", "alpha Bajo"],
    )
    print("\n      La forma cerrada ve UNICAMENTE el score (se lee en")
    print("      `_solve_fixed_point`: recibe score, H, S y un beta escalar).")
    print("      Entonces para ella A y B son literalmente el mismo modelo, y")
    print("      cualquier lambda se puede canjear por preferencias. Eso es D-08:")
    print("      lambda no esta identificado.\n")

    print("  (b) El HEV, en cambio, ve tambien theta = 1/(beta*lambda):")
    dA, _ = resuelve_brent(A)
    dB, _ = resuelve_brent(B)
    QA, _, pA = equilibrio(A, dA)
    QB, _, pB = equilibrio(B, dB)
    tabla(
        [
            [
                "A (HEV)",
                f"{A.theta()[0]:.4f} / {A.theta()[1]:.4f}",
                f"{dA:+.6f}",
                f"{_km_medios(A, QA):.4f}",
                f"{pA[-1] - pA[0]:+.4f}",
            ],
            [
                "B (cerrado)",
                f"{B.theta()[0]:.4f} / {B.theta()[1]:.4f}",
                f"{dB:+.6f}",
                f"{_km_medios(B, QB):.4f}",
                f"{pB[-1] - pB[0]:+.4f}",
            ],
        ],
        ["caso", "theta A/B", "delta*", "km medios Alto", "grad p"],
    )
    dif_Q = float(np.abs(QA - QB).max())
    print(f"\n      max |Q_A - Q_B| = {dif_Q:.4f}")
    print("      Mismo score, distinta asignacion. Esa diferencia es enteramente")
    print("      atribuible a lambda, porque es lo unico que quedo distinto entre")
    print("      los dos casos. RECIEN AHI lambda significa algo.")
    print("\n      (Los delta* no son comparables entre las dos filas: u esta medida")
    print("      en las unidades de theta, que es justo lo que cambia. Lo comparable")
    print("      es la asignacion, que es observable.)\n")

    print("  (c) Un barrido, para ver la magnitud del efecto:")
    filas, res = [], {}
    for lam in [(1.0, 1.0), (0.8, 1.25), (0.5, 2.0), (0.4, 2.5)]:
        c = caso_base(lam)
        d, _ = resuelve_brent(c)
        Q, _, p = equilibrio(c, d)
        unif = abs(lam[0] - lam[1]) < 1e-12
        filas.append(
            [
                f"{lam[0]:g} / {lam[1]:g}",
                "cerrado" if unif else "HEV",
                f"{d:+.6f}",
                f"{_km_medios(c, Q):.4f}",
                f"{p[-1] - p[0]:+.4f}",
            ]
        )
        res[f"{lam[0]}/{lam[1]}"] = {
            "delta": d,
            "Q": Q.tolist(),
            "d_alto": _km_medios(c, Q),
            "grad_p": float(p[-1] - p[0]),
        }
    tabla(filas, ["lambda A/B", "modelo", "delta*", "km medios Alto", "grad p"])
    print("\n      Ojo con leer esta tabla como «el efecto de lambda»: cada fila")
    print("      cambia el score Y el theta a la vez. Lo unico que aisla lambda es")
    print("      la comparacion A vs B de arriba, donde el score quedo fijo.")
    OUT["lambda"] = {
        "barrido": res,
        "dif_score_AB": dif_score,
        "dif_Q_AB": dif_Q,
        "A": {
            "theta": A.theta().tolist(),
            "delta": dA,
            "Q": QA.tolist(),
            "km": _km_medios(A, QA),
            "grad_p": float(pA[-1] - pA[0]),
            "alpha": A.alpha.tolist(),
            "lambda": A.lambda_h.tolist(),
            "score": A.score().tolist(),
        },
        "B": {
            "theta": B.theta().tolist(),
            "delta": dB,
            "Q": QB.tolist(),
            "km": _km_medios(B, QB),
            "grad_p": float(pB[-1] - pB[0]),
            "alpha": B.alpha.tolist(),
            "lambda": B.lambda_h.tolist(),
            "score": B.score().tolist(),
        },
    }


# --------------------------------------------------------------------------- #
def paso_10_reduccion(caso) -> None:
    titulo(10, "El control de que el HEV no rompio el caso conocido")
    print("  Con los theta iguales, el HEV tiene que dar el logit cerrado exacto.\n")
    d, _ = resuelve_brent(caso)
    loc = localizacion(caso, np.array([0.0, d]))
    a, b = q_hev(loc, caso.theta()), q_logit(loc, caso.theta())
    tabla(
        [
            ["HEV (cuadratura)", *[f"{v:.10f}" for v in a[0]]],
            ["logit cerrado", *[f"{v:.10f}" for v in b[0]]],
            ["diferencia", *[f"{v:+.1e}" for v in (a[0] - b[0])]],
        ],
        ["Q del Alto", *PARCELAS],
    )
    print(f"\n  Error maximo: {np.abs(a - b).max():.2e}")
    OUT["reduccion"] = float(np.abs(a - b).max())


# --------------------------------------------------------------------------- #
def main() -> None:
    caso = caso_base()
    print("\n  LA SUBASTA HETEROSCEDASTICA EN EL CASO MAS SIMPLE")
    print("  dos estratos, cinco parcelas, una ecuacion, una incognita")
    paso_1_enunciado(caso)
    paso_2_incognitas(caso)
    paso_3_funcion(caso)
    tr = paso_4_balanceo(caso)
    d = paso_5_brent(caso, tr)
    paso_6_nucleo(caso, d)
    paso_7_montecarlo(caso, d)
    paso_8_precios(caso, d)
    paso_10_reduccion(caso)
    paso_9_lambda()

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "traza.json").write_text(json.dumps(OUT, indent=1), encoding="utf-8")
    print(f"\n\n  Traza guardada en {SALIDA / 'traza.json'}\n")


if __name__ == "__main__":
    main()
