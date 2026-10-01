"""Genera las figuras del informe a partir de `salida/traza.json`.

    uv run python figuras.py

No calcula nada: todo lo que dibuja lo produjo `pasos.py`. Así las figuras no
pueden desincronizarse de los números del texto.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SALIDA = Path(__file__).parent / "salida"
D = json.loads((SALIDA / "traza.json").read_text(encoding="utf-8"))

ALTO, BAJO = "#b4532a", "#2f6690"
TINTA, GRIS, REGLA = "#1a1a1a", "#6b6b6b", "#d8d4cc"
PARCELAS = ["P1", "P2", "P3", "P4", "P5"]

plt.rcParams.update(
    {
        "figure.dpi": 160,
        "savefig.dpi": 160,
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": REGLA,
        "axes.labelcolor": TINTA,
        "axes.titlesize": 10.5,
        "axes.titleweight": "semibold",
        "axes.grid": True,
        "grid.color": "#ebe8e2",
        "grid.linewidth": 0.8,
        "xtick.color": GRIS,
        "ytick.color": GRIS,
        "legend.frameon": False,
        "figure.facecolor": "white",
    }
)


def limpia(ax) -> None:
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def guarda(fig, nombre: str) -> None:
    fig.tight_layout()
    fig.savefig(SALIDA / nombre, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ", nombre)


# --------------------------------------------------------------------------- #
def fig1_exceso() -> None:
    """La función de exceso, su raíz, y el algoritmo caminando hacia ella."""
    c = D["curva_exceso"]
    bal = D["balanceo"]
    raiz = D["biseccion"]["delta"]

    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.axhline(0, color=TINTA, lw=1.1, zorder=1)
    ax.plot(c["delta"], c["g"], color=ALTO, lw=2.2, zorder=3, label="g(δ) = coloca Alto − H_Alto")

    # El camino del balanceo: de cada iterada a la siguiente.
    ds, gs = bal["delta"], bal["exceso"]
    ax.plot(ds, gs, "o", color=TINTA, ms=5.5, zorder=5, label="iteradas del balanceo")
    for k in range(len(ds) - 1):
        ax.annotate(
            "",
            xy=(ds[k + 1], gs[k + 1]),
            xytext=(ds[k], gs[k]),
            arrowprops={"arrowstyle": "->", "color": TINTA, "lw": 1.2, "alpha": 0.65},
            zorder=4,
        )
    ax.annotate("  arranca en it 0", (ds[0], gs[0]), fontsize=8.5, color=TINTA, va="center")

    ax.plot([raiz], [0], "o", ms=11, mfc="none", mec=BAJO, mew=2.2, zorder=6)
    ax.annotate(
        f"δ* = {raiz:.6f}",
        (raiz, 0),
        xytext=(raiz - 4.2, -16),
        fontsize=9,
        color=BAJO,
        fontweight="semibold",
        arrowprops={"arrowstyle": "-", "color": BAJO, "lw": 1},
    )

    ax.set_xlabel("δ = ū_Bajo − ū_Alto   (la única incógnita)")
    ax.set_ylabel("exceso de hogares del estrato alto")
    ax.set_title("La subasta entera es encontrar la raíz de esta curva")
    ax.set_xlim(-8, 8)
    ax.legend(loc="lower right")
    limpia(ax)

    # El primer paso se come casi toda la distancia; el resto solo se ve acá.
    ins = ax.inset_axes([0.085, 0.60, 0.30, 0.34])
    ins.axhline(0, color=TINTA, lw=1)
    ins.plot(c["zoom_delta"], c["zoom_g"], color=ALTO, lw=1.8)
    ins.plot(ds[1:], gs[1:], "o", color=TINTA, ms=4.5)
    for k in (1, 2):
        ins.annotate(f" it {k}", (ds[k], gs[k]), fontsize=7.5, color=TINTA, va="center")
    ins.set_xlim(-0.78, -0.66)
    ins.set_ylim(-0.12, 0.85)
    ins.tick_params(labelsize=7)
    ins.set_title("zoom: it 1 y it 2 (de it 3 ya no se distinguen)", fontsize=8, pad=3)
    for lado in ("top", "right"):
        ins.spines[lado].set_visible(False)
    ax.indicate_inset_zoom(ins, edgecolor=GRIS, alpha=0.5)
    guarda(fig, "fig1-exceso.png")


# --------------------------------------------------------------------------- #
def fig2_convergencia() -> None:
    """Cuán rápido converge cada método."""
    bal = D["balanceo"]
    err = [abs(v) for v in bal["exceso"]]
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.semilogy(
        range(len(err)), err, "o-", color=ALTO, lw=2, ms=5, label="balanceo (el del núcleo)"
    )

    # La bisección parte con un intervalo de 60 y lo parte al medio cada vez.
    n_bis = D["biseccion"]["iteraciones"]
    ax.semilogy(
        range(n_bis + 1),
        [60 * 0.5**k for k in range(n_bis + 1)],
        "--",
        color=BAJO,
        lw=1.6,
        label=f"bisección: ancho del intervalo ({n_bis} iteraciones)",
    )
    ax.set_xlabel("iteración")
    ax.set_ylabel("|exceso|   /   ancho")
    ax.set_title("El balanceo usa la estructura del modelo; la bisección no")
    ax.set_xlim(-1, max(len(err), 20) + 1)
    ax.legend(loc="upper right")
    limpia(ax)
    guarda(fig, "fig2-convergencia.png")


# --------------------------------------------------------------------------- #
def fig3_pujas() -> None:
    """Las pujas descontando ū, y la probabilidad de ganar que resulta."""
    sc = np.array(D["caso"]["score"])
    d = D["biseccion"]["delta"]
    Q = np.array(D["equilibrio"]["Q"])
    x = np.arange(5)

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.4, 5.4), sharex=True)
    a1.plot(x, sc[0], "o-", color=ALTO, lw=2, ms=6, label="Alto")
    a1.plot(x, sc[1] - d, "o-", color=BAJO, lw=2, ms=6, label="Bajo")
    a1.set_ylabel("puja  w − ū")
    a1.set_title("Arriba: la puja de cada estrato en equilibrio. Abajo: quién gana")
    a1.legend()
    limpia(a1)

    an = 0.38
    a2.bar(x - an / 2, Q[0], an, color=ALTO, label="Alto")
    a2.bar(x + an / 2, Q[1], an, color=BAJO, label="Bajo")
    a2.axhline(0.5, color=GRIS, lw=1, ls=":")
    a2.set_ylabel("probabilidad de ganar")
    a2.set_xticks(x)
    a2.set_xticklabels([f"{p}\n{t:g} min" for p, t in zip(PARCELAS, D["caso"]["T"], strict=True)])
    a2.set_ylim(0, 1)
    limpia(a2)
    guarda(fig, "fig3-pujas.png")


# --------------------------------------------------------------------------- #
def fig4_asignacion() -> None:
    """Hogares localizados y precio del suelo."""
    Q = np.array(D["equilibrio"]["Q"])
    S = np.array(D["caso"]["S"])
    p = np.array(D["equilibrio"]["precio"])
    x = np.arange(5)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.7))
    a1.bar(x, Q[0] * S, 0.62, color=ALTO, label="Alto")
    a1.bar(x, Q[1] * S, 0.62, bottom=Q[0] * S, color=BAJO, label="Bajo")
    for i in range(5):
        a1.text(i, S[i] + 0.7, f"{S[i]:g}", ha="center", fontsize=8, color=GRIS)
    a1.set_xticks(x)
    a1.set_xticklabels(PARCELAS)
    a1.set_ylabel("hogares localizados")
    a1.set_title("Toda la oferta ocupada, cada estrato completo")
    a1.legend(loc="upper left")
    limpia(a1)

    a2.plot(x, p, "o-", color=TINTA, lw=2.2, ms=6)
    a2.fill_between(x, p.min() - 0.15, p, color=TINTA, alpha=0.06)
    a2.set_xticks(x)
    a2.set_xticklabels(PARCELAS)
    a2.set_ylabel("precio del suelo  p_i")
    a2.set_ylim(p.min() - 0.15, p.max() + 0.15)
    a2.set_title(f"Gradiente {D['equilibrio']['grad']:+.3f}: cae con la distancia")
    limpia(a2)
    guarda(fig, "fig4-asignacion.png")


# --------------------------------------------------------------------------- #
def fig5_montecarlo() -> None:
    """La cuadratura contra la subasta simulada hogar por hogar."""
    mc = D["montecarlo"]
    Q = np.array(D["equilibrio"]["Q"])
    F = np.array(mc["freq"])
    x = np.arange(5)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.6), gridspec_kw={"width_ratios": [1.5, 1]})
    an = 0.38
    a1.bar(x - an / 2, Q[0], an, color=ALTO, label="cuadratura")
    a1.bar(x + an / 2, F[0], an, color="none", edgecolor=TINTA, lw=1.6, label="Monte Carlo")
    a1.set_xticks(x)
    a1.set_xticklabels(PARCELAS)
    a1.set_ylabel("P(gana el Alto)")
    a1.set_title(f"{mc['reps']:,} subastas simuladas".replace(",", "."))
    a1.legend()
    limpia(a1)

    dif = (F - Q).ravel()
    a2.axhline(0, color=TINTA, lw=1)
    env = 1 / np.sqrt(mc["reps"])
    a2.axhspan(-env, env, color=BAJO, alpha=0.12)
    a2.plot(range(len(dif)), dif, "o", color=ALTO, ms=5)
    a2.set_ylabel("MC − cuadratura")
    a2.set_xticks([])
    a2.set_ylim(-3 * env, 3 * env)
    a2.set_title(f"Banda ±1/√n = ±{env:.4f}")
    limpia(a2)
    guarda(fig, "fig5-montecarlo.png")


# --------------------------------------------------------------------------- #
def fig6_lambda() -> None:
    """Mismo score, distinta asignación: la identificación de λ."""
    L = D["lambda"]
    A, B = L["A"], L["B"]
    QA, QB = np.array(A["Q"]), np.array(B["Q"])
    x = np.arange(5)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.9))
    scA, scB = np.array(A["score"]), np.array(B["score"])
    lam_a = f"{A['lambda'][0]:g} / {A['lambda'][1]:g}"
    a1.plot(x, scA[0], "-", color=ALTO, lw=5, alpha=0.32, label=f"A: λ = {lam_a}")
    a1.plot(x, scB[0], "--", color=TINTA, lw=1.5, label="B: λ = 1 / 1, α y ρ divididos por λ")
    a1.set_xticks(x)
    a1.set_xticklabels(PARCELAS)
    a1.set_ylabel("puja determinística del Alto")
    dif = L["dif_score_AB"]
    a1.set_title(
        "Las dos pujas son el mismo número\n"
        f"(diferencia máxima: {'0 exacto' if dif == 0 else f'{dif:.1e}'})"
    )
    a1.legend(loc="upper right", fontsize=8)
    limpia(a1)

    an = 0.38
    a2.bar(
        x - an / 2,
        QA[0],
        an,
        color=ALTO,
        label=f"A (HEV), θ = {A['theta'][0]:g} / {A['theta'][1]:g}",
    )
    a2.bar(
        x + an / 2, QB[0], an, color="none", edgecolor=TINTA, lw=1.6, label="B (cerrado), θ = 1 / 1"
    )
    a2.set_xticks(x)
    a2.set_xticklabels(PARCELAS)
    a2.set_ylabel("P(gana el Alto)")
    a2.set_ylim(0, max(QA[0].max(), QB[0].max()) * 1.42)
    a2.set_title(f"Pero la asignación difiere en {L['dif_Q_AB']:.4f}\nEso, y solo eso, es λ")
    a2.legend(loc="upper left", fontsize=8)
    limpia(a2)
    guarda(fig, "fig6-lambda.png")


if __name__ == "__main__":
    print("Figuras en salida/:")
    fig1_exceso()
    fig2_convergencia()
    fig3_pujas()
    fig4_asignacion()
    fig5_montecarlo()
    fig6_lambda()
