"""Figuras de E1 y E2, desde `salida/experimentos.json`. No calcula nada.

uv run python figuras_experimentos.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SALIDA = Path(__file__).parent / "salida"
D = json.loads((SALIDA / "experimentos.json").read_text(encoding="utf-8"))
CASOS = {c["nombre"]: c for c in D["casos"]}
BINS = np.array(D["bins"])
DIAS = np.arange(1, D["dias"] + 1)

AUTO, METRO, TINTA, GRIS, REGLA = "#b4532a", "#2f6690", "#1a1a1a", "#6b6b6b", "#d8d4cc"
COLOR_CASO = {"C1": "#8a8a8a", "C2": AUTO, "C3": METRO}
COLOR_K = {1: "#e3a587", 2: "#d0794f", 3: AUTO, 5: "#7d3519", 10: TINTA}
HORIZONTES = {
    "corto": "Corto plazo (días 1–10)",
    "medio": "Mediano (11–50)",
    "largo": "Largo (51–250)",
}
plt.rcParams.update(
    {
        "figure.dpi": 160,
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": REGLA,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.color": "#ebe8e2",
        "legend.frameon": False,
        "figure.facecolor": "white",
    }
)


def limpia(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def horizontes(ax):
    for x in (10.5, 50.5):
        ax.axvline(x, color=REGLA, lw=0.8)


def guarda(fig, nombre):
    fig.tight_layout()
    fig.savefig(SALIDA / nombre, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def e1(caso, d, k=None, r=None):
    for f in D["e1"]:
        if f["caso"] == caso and f["d"] == d:
            if k is None and f.get("control"):
                return f
            if k is not None and f["k"] == k and f["r"] == r:
                return f
    raise KeyError((caso, d, k, r))


def e2(caso, d, cond, sigma):
    return next(
        f
        for f in D["e2"]
        if f["caso"] == caso and f["d"] == d and f["condicion"] == cond and f["sigma"] == sigma
    )


def fig_e1_trayectorias(caso="C2", d=0.5):
    """Cuota esperada del modo mejor por día, tras k shocks de r·A minutos."""
    c = CASOS[caso]
    ctrl = np.array(e1(caso, d)["s_por_dia"])
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.5), sharey=True)
    for ax, k in zip(axs, (1, 5), strict=True):
        ax.plot(DIAS, ctrl, color=GRIS, lw=1.4, ls="--", label="sin shock (control)")
        for r, alfa in ((1.0, 0.35), (2.0, 0.6), (4.0, 0.85), (6.0, 1.0)):
            y = ctrl + np.array(e1(caso, d, k, r)["brecha_por_dia"])
            ax.plot(
                DIAS,
                y,
                color=AUTO,
                alpha=alfa,
                lw=1.5,
                label=f"Δ = {r:g}·A = {r * c['ventaja_min']:.0f} min",
            )
        ax.axhline(0.5, color=TINTA, lw=0.7, ls=":")
        horizontes(ax)
        ax.set_title(f"k = {k} experiencia{'s' if k > 1 else ''} mala{'s' if k > 1 else ''}")
        ax.set_xlabel("día t (días)")
        ax.set_ylim(0, 1)
        limpia(ax)
    axs[0].set_ylabel(f"s̄(t): prob. de elegir {c['mejor'].lower()} (0–1)")
    axs[1].legend(loc="lower right", fontsize=8)
    guarda(fig, "e1-trayectorias.png")


def fig_e1_critico(caso="C2"):
    """P del mejor justo después del k-ésimo shock: fórmula (9) contra simulación."""
    c = CASOS[caso]
    rs = sorted({f["r"] for f in D["e1"] if not f.get("control")})
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.5), sharey=True)
    for ax, d in zip(axs, (0.0, 0.5, 1.28), strict=True):
        for k, color in COLOR_K.items():
            rr = np.linspace(0, max(rs), 200)
            w = c["w_k"][str(d)][str(k)]
            ax.plot(rr, 1 / (1 + np.exp(-c["dv"] * (1 - w * rr))), color=color, lw=1.3)
            ax.plot(
                rs,
                [e1(caso, d, k, r)["p_post_sim"] for r in rs],
                "o",
                color=color,
                ms=3.5,
                label=f"k = {k}",
            )
        ax.axhline(0.5, color=TINTA, lw=0.7, ls=":")
        ax.axhline(c["p_verdadera"], color=GRIS, lw=0.7, ls="--")
        ax.set_title(f"d = {d:g}")
        ax.set_xlabel("tamaño del shock Δ/A (adim.)")
        limpia(ax)
    axs[0].set_ylabel("P del mejor tras el k-ésimo shock (0–1)")
    axs[2].legend(loc="upper right", fontsize=8)
    guarda(fig, "e1-critico.png")


def fig_e1_horizontes(caso="C2", d=0.5):
    """Efecto sobre S (tratamiento − control) por horizonte."""
    rs = sorted({f["r"] for f in D["e1"] if not f.get("control")})
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.4), sharey=True)
    for ax, (w, titulo) in zip(axs, HORIZONTES.items(), strict=True):
        for k, color in COLOR_K.items():
            y = [100 * e1(caso, d, k, r)["efecto"][w] for r in rs]
            ax.plot(rs, y, "-o", color=color, ms=3, lw=1.4, label=f"k = {k}")
        ax.axhline(0, color=TINTA, lw=0.7)
        ax.set_title(titulo)
        ax.set_xlabel("tamaño del shock Δ/A (adim.)")
        limpia(ax)
    axs[0].set_ylabel("efecto E en la cuota del mejor (pp)")
    axs[2].legend(loc="lower left", fontsize=8)
    guarda(fig, "e1-horizontes.png")


def fig_e1_distribuciones(caso="C2", d=0.5, k=3):
    """Distribución de P̄_n entre réplicas: control contra dos shocks."""
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.2), sharey=True)
    series = (
        ("sin shock", e1(caso, d), GRIS),
        (f"k = {k}, Δ = 2·A", e1(caso, d, k, 2.0), "#d0794f"),
        (f"k = {k}, Δ = 6·A", e1(caso, d, k, 6.0), TINTA),
    )
    for ax, (w, titulo) in zip(axs, HORIZONTES.items(), strict=True):
        for nombre, f, color in series:
            h = np.array(f["ventanas"][w]["histograma"], dtype=float)
            ax.stairs(h / h.sum(), BINS, color=color, lw=1.6, label=nombre)
        ax.axvline(0.5, color=TINTA, lw=0.7, ls=":")
        ax.set_title(titulo)
        ax.set_xlabel("P̄ₙ: prob. media de la réplica (0–1)")
        limpia(ax)
    axs[0].set_ylabel("fracción de réplicas (0–1)")
    axs[0].legend(loc="upper left", fontsize=8)
    guarda(fig, "e1-distribuciones.png")


def fig_e2_phi(d=0.5):
    """Φ (fracción de la ventaja que sobrevive) contra σ·|β|, largo plazo."""
    sigmas = sorted({f["sigma"] for f in D["e2"]})
    titulos = {
        "ambos": "Ruido en los dos modos",
        "solo_mejor": "Ruido sólo en el mejor",
        "solo_peor": "Ruido sólo en el peor",
    }
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.5), sharey=True)
    for ax, (cond, titulo) in zip(axs, titulos.items(), strict=True):
        for caso, c in CASOS.items():
            x = [s * abs(c["beta"]) for s in sigmas]
            y = [e2(caso, d, cond, s)["phi"]["largo"] for s in sigmas]
            ax.plot(x, y, "-o", color=COLOR_CASO[caso], ms=3.5, lw=1.5, label=caso)
        ax.axhline(1, color=GRIS, lw=0.7, ls="--")
        ax.axhline(0, color=TINTA, lw=0.7, ls=":")
        ax.set_title(titulo)
        ax.set_xlabel("σ·|β| (útiles)")
        limpia(ax)
    axs[0].set_ylabel("Φ, largo plazo (adim.)")
    axs[0].legend(loc="lower left", fontsize=8)
    guarda(fig, "e2-phi.png")


def fig_e2_descomposicion(caso="C2", d=0.5):
    """S − P verdadera = dispersión (efecto de variabilidad) + sesgo (hot stove)."""
    sigmas = [s for s in sorted({f["sigma"] for f in D["e2"]}) if s > 0]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.4), sharey=True)
    for ax, cond in zip(axs, ("ambos", "solo_mejor", "solo_peor"), strict=True):
        x = np.arange(len(sigmas))
        dec = [e2(caso, d, cond, s)["descomposicion"]["largo"] for s in sigmas]
        pve = np.array([100 * q["pve"] for q in dec])
        ses = np.array([100 * q["sesgo"] for q in dec])
        ax.bar(x - 0.18, pve, 0.36, color=METRO, label="dispersión (variabilidad)")
        ax.bar(x + 0.18, ses, 0.36, color=AUTO, label="sesgo (hot stove)")
        ax.plot(x, pve + ses, "k_", ms=14, mew=2, label="total S − P verdadera")
        ax.axhline(0, color=TINTA, lw=0.7)
        ax.set_xticks(x, [f"{s:g}" for s in sigmas])
        ax.set_xlabel("σ (min)")
        ax.set_title(
            {
                "ambos": "Ruido en los dos modos",
                "solo_mejor": "Ruido sólo en el mejor",
                "solo_peor": "Ruido sólo en el peor",
            }[cond]
        )
        limpia(ax)
    axs[0].set_ylabel("contribución a S − P*, largo plazo (pp)")
    axs[0].legend(loc="lower left", fontsize=8)
    guarda(fig, "e2-descomposicion.png")


def fig_e2_distribuciones(caso="C2", d=0.5, cond="ambos"):
    """Distribución de P̄_n de largo plazo según σ."""
    fig, ax = plt.subplots(figsize=(6.5, 3.3))
    for s, alfa in ((0.0, 1.0), (20.0, 0.45), (40.0, 0.7), (80.0, 1.0)):
        h = np.array(e2(caso, d, cond, s)["ventanas"]["largo"]["histograma"], dtype=float)
        color = GRIS if s == 0 else METRO
        ax.stairs(h / h.sum(), BINS, color=color, alpha=alfa, lw=1.6, label=f"σ = {s:g} min")
    ax.axvline(0.5, color=TINTA, lw=0.7, ls=":")
    ax.set_xlabel("P̄ₙ: prob. media de la réplica, días 51–250 (0–1)")
    ax.set_ylabel("fracción de réplicas (0–1)")
    ax.legend(loc="upper left", fontsize=8)
    limpia(ax)
    guarda(fig, "e2-distribuciones.png")


def fig_e2_decaimiento(caso="C2", cond="ambos"):
    """Φ por horizonte y decaimiento d."""
    sigmas = sorted({f["sigma"] for f in D["e2"]})
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.3), sharey=True)
    for ax, (w, titulo) in zip(axs, HORIZONTES.items(), strict=True):
        for d, estilo in ((0.0, ":"), (0.5, "-"), (1.28, "--")):
            y = [e2(caso, d, cond, s)["phi"][w] for s in sigmas]
            ax.plot(sigmas, y, estilo, marker="o", color=METRO, ms=3, lw=1.5, label=f"d = {d:g}")
        ax.axhline(1, color=GRIS, lw=0.7, ls="--")
        ax.axhline(0, color=TINTA, lw=0.7, ls=":")
        ax.set_title(titulo)
        ax.set_xlabel("σ (min)")
        limpia(ax)
    axs[0].set_ylabel("Φ (adim.)")
    axs[0].legend(loc="lower left", fontsize=8)
    guarda(fig, "e2-decaimiento.png")


if __name__ == "__main__":
    fig_e1_trayectorias()
    fig_e1_critico()
    fig_e1_horizontes()
    fig_e1_distribuciones()
    fig_e2_phi()
    fig_e2_descomposicion()
    fig_e2_distribuciones()
    fig_e2_decaimiento()
    print(f"  figuras en {SALIDA}")
