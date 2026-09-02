"""Figuras del informe de impacto, desde `salida/impacto.json`.

    uv run python figuras.py

No calcula nada: todo lo produjo `impacto.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SALIDA = Path(__file__).parent / "salida"
D = json.loads((SALIDA / "impacto.json").read_text(encoding="utf-8"))
F = D["filas"]

ALTO, MEDIO, BAJO = "#b4532a", "#2f6690", "#2e6e4e"
COL = (ALTO, MEDIO, BAJO)
EST = ("Alto", "Medio", "Bajo")
TINTA, GRIS, REGLA = "#1a1a1a", "#6b6b6b", "#d8d4cc"

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


def limpia(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def guarda(fig, nombre):
    fig.tight_layout()
    fig.savefig(SALIDA / nombre, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ", nombre)


def km():
    return (np.arange(D["L"]) - D["CBD"]) * D["dx"]


# --------------------------------------------------------------------------- #
def fig1_impacto_vs_r():
    """Cuánto cambia el resultado según cuán heterogéneos sean los λ."""
    r = [f["r"] for f in F]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.5))

    a1.plot(r, [f["max_dQ"] for f in F], "o-", color=ALTO, lw=2, ms=5)
    a1.set_xlabel("razón de heterogeneidad  r   (λ = 1/r · 1 · r)")
    a1.set_ylabel("max |ΔQ|")
    a1.set_title("Diferencia máxima en una celda")
    a1.axhline(0, color=GRIS, lw=1)
    limpia(a1)

    tot = sum(F[0]["H"])
    a2.plot(r, [100 * f["movidos_total"] / tot for f in F], "o-", color=TINTA, lw=2, ms=5)
    a2.set_xlabel("razón de heterogeneidad  r")
    a2.set_ylabel("% de los hogares")
    a2.set_title("Hogares que cambian de celda")
    a2.set_ylim(0, None)
    limpia(a2)
    guarda(fig, "fig1-impacto.png")


# --------------------------------------------------------------------------- #
def fig2_donde(r="2.0"):
    """El resultado central: la diferencia no está repartida."""
    P = D["perfiles"][r]
    S = np.array(P["S"], dtype=float)
    Qa, Qb = np.array(P["Q_antes"]), np.array(P["Q_ahora"])
    x = km()

    fig, (a1, a2) = plt.subplots(
        2, 1, figsize=(7.6, 5.6), sharex=True, gridspec_kw={"height_ratios": [1, 1.15]}
    )

    a1.fill_between(x, 0, S, color=GRIS, alpha=0.18, lw=0)
    a1.set_ylabel("oferta S (viviendas)")
    a1.set_title("Dónde está la vivienda, y dónde el modelo se equivocaba")
    limpia(a1)

    for h in range(3):
        a2.plot(x, Qb[h] - Qa[h], color=COL[h], lw=1.8, label=EST[h])
    a2.axhline(0, color=TINTA, lw=1)
    a2.set_xlabel("distancia al CBD (km)")
    a2.set_ylabel("ΔQ   (HEV − forma cerrada)")
    a2.legend(loc="upper right", ncol=3)
    a2.set_xlim(-8, 8)
    limpia(a2)

    # Las FRONTERAS: donde se cruzan las composiciones. Ahi caen los picos, y es
    # el resultado del informe. Marcar la distancia media seria otra cosa y no
    # coincide: la media del Alto esta en 1,05 km y la frontera cerca de 2.
    def cruce(a, b):
        """Primer x > 0 donde la curva `a` deja de ir por encima de `b`."""
        dif = Qb[a] - Qb[b]
        for k in range(D["CBD"], D["L"] - 1):
            if dif[k] > 0 >= dif[k + 1]:
                t = dif[k] / (dif[k] - dif[k + 1])
                return x[k] + t * (x[k + 1] - x[k])
        return None

    for par, etiq in (
        ((0, 1), "frontera\nAlto / Medio"),
        ((1, 2), "frontera\nMedio / Bajo"),
    ):
        xf = cruce(*par)
        if xf is None:
            continue
        for sg in (-1, 1):
            a2.axvline(sg * xf, color=GRIS, ls=":", lw=1.1)
        a2.annotate(
            f"{etiq}\n{xf:.1f} km",
            xy=(xf, 0),
            xytext=(xf + 0.3, a2.get_ylim()[0] * 0.70),
            fontsize=8,
            color=GRIS,
            ha="left",
        )
    guarda(fig, "fig2-donde.png")


# --------------------------------------------------------------------------- #
def fig3_composicion(r="2.0"):
    """La composición por celda, con los dos modelos superpuestos."""
    P = D["perfiles"][r]
    Qa, Qb = np.array(P["Q_antes"]), np.array(P["Q_ahora"])
    x = km()
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    for h in range(3):
        ax.plot(x, Qa[h], color=COL[h], lw=2.6, alpha=0.30)
        ax.plot(x, Qb[h], color=COL[h], lw=1.5, ls="--")
    ax.plot([], [], color=TINTA, lw=2.6, alpha=0.30, label="antes (forma cerrada)")
    ax.plot([], [], color=TINTA, lw=1.5, ls="--", label="ahora (HEV)")
    ax.set_xlabel("distancia al CBD (km)")
    ax.set_ylabel("Q — probabilidad de ganar la celda")
    ax.set_title("Composición por celda: dónde se separan las dos curvas")
    ax.set_xlim(-8, 8)
    ax.legend(loc="upper right")
    limpia(ax)
    guarda(fig, "fig3-composicion.png")


# --------------------------------------------------------------------------- #
def fig4_agregados():
    """Los agregados casi no se mueven: hay que decirlo."""
    r = [f["r"] for f in F]
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    for h in range(3):
        ax.plot(r, [f["d_antes"][h] for f in F], "-", color=COL[h], lw=2.6, alpha=0.30)
        ax.plot(r, [f["d_ahora"][h] for f in F], "--", color=COL[h], lw=1.5)
        ax.annotate(
            EST[h],
            (r[-1], F[-1]["d_ahora"][h]),
            xytext=(6, -3),
            textcoords="offset points",
            color=COL[h],
            fontsize=9,
            fontweight="semibold",
        )
    ax.plot([], [], color=TINTA, lw=2.6, alpha=0.30, label="antes (forma cerrada)")
    ax.plot([], [], color=TINTA, lw=1.5, ls="--", label="ahora (HEV)")
    ax.set_xlabel("razón de heterogeneidad  r")
    ax.set_ylabel("distancia media al CBD (km)")
    ax.set_title("El agregado por estrato apenas se mueve — las curvas se pisan")
    ax.legend(loc="center right")
    limpia(ax)
    guarda(fig, "fig4-agregados.png")


if __name__ == "__main__":
    print("Figuras en salida/:")
    fig1_impacto_vs_r()
    fig2_donde()
    fig3_composicion()
    fig4_agregados()
