"""Figuras de la fase 0, desde `salida/persona.json`. No calcula nada.

uv run python figuras.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SALIDA = Path(__file__).parent / "salida"
D = json.loads((SALIDA / "persona.json").read_text(encoding="utf-8"))
F = D["filas"]

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


def fig1_trayectoria(sigma=10.0, mu=3.0, d=0.5):
    """Una persona: lo que experimentó, lo que percibe y lo que eligió."""
    r = fila(sigma, mu, d)
    e = r["ejemplo"]
    dias = np.arange(1, D["dias"] + 1)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    exp = np.array(e["experimentado_auto"])
    elige = np.array(e["elige_auto"])
    ax.scatter(
        dias[elige],
        exp[elige],
        s=14,
        color=AUTO,
        alpha=0.6,
        label="tiempo experimentado (días en auto)",
    )
    ax.plot(dias, e["percibido_auto"], color=AUTO, lw=2, label="tiempo percibido del auto (IBL)")
    ax.axhline(D["t_auto_eq"], color=AUTO, ls=":", lw=1.2, label="auto verdadero (equilibrio)")
    ax.axhline(D["t_metro_eq"], color=METRO, ls="--", lw=1.4, label="metro")
    ax.set_xlabel("día")
    ax.set_ylabel("minutos")
    ax.set_title(
        f"La persona con la peor primera experiencia en auto  (σ = {sigma:.0f} min, μ = {mu:.0f}, d = {d})"
    )
    for t in dias[~elige]:
        ax.axvspan(t - 0.5, t + 0.5, color=METRO, alpha=0.08, lw=0)
    ax.legend(loc="upper right", fontsize=8)
    limpia(ax)
    guarda(fig, "fig1-trayectoria.png")


def fig2_share_por_dia(d=0.5):
    """Cuántos van en auto cada día, contra lo que el logit verdadero dice."""
    sigmas = sorted({f["sigma"] for f in F})
    mus = sorted({f["mu"] for f in F})
    fig, axs = plt.subplots(1, len(mus), figsize=(10.5, 3.4), sharey=True)
    for ax, mu in zip(axs, mus, strict=True):
        for k, sigma in enumerate(sigmas):
            r = fila(sigma, mu, d)
            ax.plot(
                r["share_auto_por_dia"],
                color=AUTO,
                lw=1.2 + 0.6 * k,
                alpha=0.5 + 0.2 * k,
                label=f"σ = {sigma:.0f} min",
            )
        ax.axhline(
            r["p_auto_verdadera"],
            color=TINTA,
            ls=":",
            lw=1.2,
            label="P(auto) con tiempos verdaderos",
        )
        ax.set_title(f"μ = {mu:.0f}")
        ax.set_xlabel("día")
        ax.set_ylim(0, 1)
        limpia(ax)
    axs[0].set_ylabel("fracción que elige auto")
    axs[-1].legend(loc="lower right", fontsize=8)
    fig.suptitle(f"Share del auto día a día  (d = {d})", fontweight="bold")
    guarda(fig, "fig2-share.png")


def fig3_hot_stove(d=0.5):
    """Izquierda: quién abandonó el auto. Derecha: mala suerte temprana vs buena."""
    sigmas = sorted({f["sigma"] for f in F})
    mus = sorted({f["mu"] for f in F})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.6))
    for k, mu in enumerate(mus):
        a1.plot(
            sigmas,
            [100 * fila(s, mu, d)["abandono"] for s in sigmas],
            "o-",
            lw=1.2 + 0.6 * k,
            color=TINTA,
            alpha=0.4 + 0.3 * k,
            label=f"μ = {mu:.0f}",
        )
    a1.set_title("Abandono: ni un día en auto en los últimos 20")
    a1.set_xlabel("σ del error del auto (min)")
    a1.set_ylabel("% de las personas")
    a1.set_ylim(0, None)
    a1.legend(loc="upper left", fontsize=8)
    limpia(a1)

    from matplotlib.patches import Patch

    ancho = 0.8 / (2 * len(mus))
    xs = np.arange(len(sigmas))
    for k, mu in enumerate(mus):
        mala = [fila(s, mu, d)["share_fin_mala_suerte"] for s in sigmas]
        buena = [fila(s, mu, d)["share_fin_buena_suerte"] for s in sigmas]
        x0 = xs + (2 * k) * ancho
        a2.bar(x0, buena, ancho, color=METRO, alpha=0.4 + 0.3 * k)
        a2.bar(x0 + ancho, mala, ancho, color=AUTO, alpha=0.4 + 0.3 * k)
        for i in range(len(sigmas)):
            a2.text(
                x0[i] + ancho / 2,
                max(mala[i], buena[i]) + 0.01,
                f"μ={mu:.0f}",
                ha="center",
                fontsize=7,
                color=GRIS,
            )
    a2.legend(
        handles=[
            Patch(color=METRO, label="primera experiencia en el decil mejor"),
            Patch(color=AUTO, label="primera experiencia en el decil peor"),
        ],
        loc="upper right",
        fontsize=8,
    )
    a2.set_xticks(xs + ancho * (2 * len(mus) - 1) / 2)
    a2.set_xticklabels([f"σ = {s:.0f}" for s in sigmas])
    a2.set_ylabel("share del auto, últimos 20 días")
    a2.set_ylim(0, 1)
    a2.set_title("Mala suerte temprana vs buena suerte")
    limpia(a2)
    fig.suptitle(f"Hot stove effect  (d = {d})", fontweight="bold")
    guarda(fig, "fig3-hot-stove.png")


if __name__ == "__main__":
    print("Figuras en salida/:")
    fig1_trayectoria()
    fig2_share_por_dia()
    fig3_hot_stove()
