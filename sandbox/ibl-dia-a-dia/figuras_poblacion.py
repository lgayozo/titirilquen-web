"""Figuras de la fase 1, desde `salida/poblacion.json`. No calcula nada.

uv run python figuras_poblacion.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

SALIDA = Path(__file__).parent / "salida"
D = json.loads((SALIDA / "poblacion.json").read_text(encoding="utf-8"))
F = D["filas"]
EQ = D["split_equilibrio"]

AUTO, METRO, TINTA, GRIS, REGLA = "#b4532a", "#2f6690", "#1a1a1a", "#6b6b6b", "#d8d4cc"
plt.rcParams.update(
    {
        "figure.dpi": 160,
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": REGLA,
        "axes.titlesize": 10.5,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.color": "#ebe8e2",
        "legend.frameon": False,
        "figure.facecolor": "white",
    }
)


def fila(sigma, mu, d):
    return next(f for f in F if f["sigma"] == sigma and f["mu"] == mu and f["d"] == d)


def limpia(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def guarda(fig, nombre):
    fig.tight_layout()
    fig.savefig(SALIDA / nombre, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  ", nombre)


def fig4_split(sigma=10.0, d=0.5):
    """Partición modal día a día contra el equilibrio MSA, por escala del logit."""
    mus = sorted({f["mu"] for f in F})
    fig, axs = plt.subplots(1, len(mus), figsize=(10.5, 3.4), sharey=True)
    for ax, mu in zip(axs, mus, strict=True):
        s = np.array(fila(sigma, mu, d)["split_por_dia"])
        s0 = np.array(fila(0.0, mu, d)["split_por_dia"])
        ax.plot(s0[:, 0], color=AUTO, lw=1.2, alpha=0.35)
        ax.plot(s0[:, 1], color=METRO, lw=1.2, alpha=0.35)
        ax.plot(s[:, 0], color=AUTO, lw=1.8, label="auto")
        ax.plot(s[:, 1], color=METRO, lw=1.8, label="metro")
        ax.axhline(EQ[0], color=AUTO, ls=":", lw=1.2)
        ax.axhline(EQ[1], color=METRO, ls=":", lw=1.2)
        ax.set_title(f"μ = {mu:.0f}")
        ax.set_xlabel("día")
        ax.set_ylim(0, 1)
        limpia(ax)
    axs[0].set_ylabel("fracción de los que eligen")
    axs[-1].plot([], [], color=GRIS, ls=":", label="equilibrio MSA (día 0)")
    axs[-1].plot([], [], color=GRIS, lw=1.2, alpha=0.5, label="σ = 0 (referencia de cada μ)")
    axs[-1].legend(loc="upper right", fontsize=8)
    fig.suptitle(f"Partición modal día a día  (σ = {sigma:.0f} min, d = {d})", fontweight="bold")
    guarda(fig, "fig4-split.png")


def fig5_abandono(d=0.5):
    """Abandono del auto y del metro contra σ, por μ."""
    sigmas = sorted({f["sigma"] for f in F})
    mus = sorted({f["mu"] for f in F})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.4), sharey=True)
    for ax, nombre, color in ((a1, "auto", AUTO), (a2, "metro", METRO)):
        for k, mu in enumerate(mus):
            ax.plot(
                sigmas,
                [100 * fila(s, mu, d)[f"abandono_{nombre}"] for s in sigmas],
                "o-",
                color=color,
                lw=1.2 + 0.6 * k,
                alpha=0.4 + 0.3 * k,
                label=f"μ = {mu:.0f}",
            )
        ax.set_title(f"Abandono del {nombre}: ni un día en los últimos {D['ultimos']}")
        ax.set_xlabel("σ del error (min)")
        ax.legend(loc="upper left", fontsize=8)
        limpia(ax)
    a1.set_ylabel("% de quienes pueden usarlo")
    a1.set_ylim(0, None)
    fig.suptitle(f"Hot stove en la población  (d = {d})", fontweight="bold")
    guarda(fig, "fig5-abandono.png")


def fig6_suerte_y_congestion(d=0.5):
    """Izquierda: mala vs buena suerte temprana en el auto. Derecha: el tiempo real del auto."""
    sigmas = sorted({f["sigma"] for f in F if f["sigma"] > 0})
    mus = sorted({f["mu"] for f in F})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.6))
    ancho = 0.8 / (2 * len(mus))
    xs = np.arange(len(sigmas))
    for k, mu in enumerate(mus):
        mala = [fila(s, mu, d)["share_fin_mala_suerte_auto"] for s in sigmas]
        buena = [fila(s, mu, d)["share_fin_buena_suerte_auto"] for s in sigmas]
        x0 = xs + 2 * k * ancho
        a1.bar(x0, buena, ancho, color=METRO, alpha=0.4 + 0.3 * k)
        a1.bar(x0 + ancho, mala, ancho, color=AUTO, alpha=0.4 + 0.3 * k)
        for i in range(len(sigmas)):
            a1.text(
                x0[i] + ancho / 2,
                max(mala[i], buena[i]) + 0.01,
                f"μ={mu:.0f}",
                ha="center",
                fontsize=7,
                color=GRIS,
            )
    a1.legend(
        handles=[
            Patch(color=METRO, label="primer ε en el decil mejor"),
            Patch(color=AUTO, label="primer ε en el decil peor"),
        ],
        loc="upper right",
        fontsize=8,
    )
    a1.set_xticks(xs + ancho * (2 * len(mus) - 1) / 2)
    a1.set_xticklabels([f"σ = {s:.0f}" for s in sigmas])
    a1.set_ylabel(f"share del auto, últimos {D['ultimos']} días")
    a1.set_ylim(0, 1)
    a1.set_title("Mala suerte temprana vs buena, en el auto")
    limpia(a1)

    for k, mu in enumerate(mus):
        r = fila(10.0, mu, d)
        a2.plot(
            r["t_auto_medio_por_dia"],
            color=AUTO,
            lw=1.2 + 0.6 * k,
            alpha=0.4 + 0.3 * k,
            label=f"μ = {mu:.0f}",
        )
    a2.set_title("Tiempo real del auto, promedio de quienes lo usan  (σ = 10)")
    a2.set_xlabel("día")
    a2.set_ylabel("minutos")
    a2.legend(loc="upper right", fontsize=8)
    limpia(a2)
    fig.suptitle(f"(d = {d})", fontweight="bold")
    guarda(fig, "fig6-suerte-congestion.png")


if __name__ == "__main__":
    print("Figuras en salida/:")
    fig4_split()
    fig5_abandono()
    fig6_suerte_y_congestion()
