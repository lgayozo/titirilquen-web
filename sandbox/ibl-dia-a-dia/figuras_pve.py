"""Figuras del efecto de variabilidad del pago, desde `salida/pve.json` y
`salida/poblacion.json`. No calcula nada.

uv run python figuras_pve.py
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np

from figuras import AUTO, GRIS, METRO, SALIDA, TINTA, guarda, limpia

P = json.loads((SALIDA / "pve.json").read_text(encoding="utf-8"))
POB = json.loads((SALIDA / "poblacion.json").read_text(encoding="utf-8"))
COLOR_MU = {1.0: GRIS, 3.0: METRO, 10.0: AUTO}
TITULOS = {
    "ambos": "Ruido en los dos modos\n(efecto de variabilidad)",
    "solo_mejor": "Ruido sólo en el mejor (auto)\n(+ hot stove en contra)",
    "solo_peor": "Ruido sólo en el peor (metro)\n(+ hot stove a favor)",
}


def fila(cond, sigma, mu, d):
    return next(
        f
        for f in P["filas"]
        if f["condicion"] == cond and f["sigma"] == sigma and f["mu"] == mu and f["d"] == d
    )


def fig7_pve(d=0.5):
    """Una persona: cuota del mejor contra σ, por condición de ruido y μ."""
    sigmas = sorted({f["sigma"] for f in P["filas"]})
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.6), sharey=True)
    for ax, cond in zip(axs, TITULOS, strict=True):
        for mu, color in COLOR_MU.items():
            y = [fila(cond, s, mu, d)["cuota_mejor_ultimos"] for s in sigmas]
            ax.plot(sigmas, y, "-o", color=color, ms=3.5, lw=1.6, label=f"μ = {mu:g}")
        ax.axhline(0.5, color=TINTA, lw=0.8, ls=":")
        ax.set_title(TITULOS[cond])
        ax.set_xlabel("σ del ruido de experiencia (min)")
        ax.set_ylim(0, 1.02)
        limpia(ax)
    axs[0].set_ylabel("cuota del mejor modo (últimos 20 días)")
    axs[0].legend(loc="lower left")
    guarda(fig, "fig7-pve.png")


def fig8_pve_dias(mu=10.0, sigma=40.0):
    """Una persona: el efecto por día, según el decaimiento d."""
    fig, ax = plt.subplots(figsize=(8, 3.4))
    dias = np.arange(1, P["dias"] + 1)
    for d, estilo in ((0.0, "-"), (0.5, "--"), (1.0, ":")):
        y = np.array(fila("ambos", sigma, mu, d)["cuota_mejor_por_dia"])
        # "valid": sin relleno con ceros en los bordes (que inventaba caídas).
        suave = np.convolve(y, np.ones(5) / 5, mode="valid")
        ax.plot(dias[2:-2], suave, estilo, color=AUTO, lw=1.6, label=f"d = {d:g}")
    p0 = fila("ambos", 0.0, mu, 0.5)["p_mejor_verdadera"]
    ax.axhline(p0, color=GRIS, lw=0.9, ls="-", label=f"P verdadera ({p0:.2f})")
    ax.axhline(0.5, color=TINTA, lw=0.8, ls=":")
    ax.set_xlabel("día")
    ax.set_ylabel("cuota del mejor (media móvil 5 días)")
    ax.set_ylim(0.45, 1.0)
    ax.set_title(f"μ = {mu:g}, σ = {sigma:g} min en los dos modos")
    ax.legend(loc="lower right")
    limpia(ax)
    guarda(fig, "fig8-pve-dias.png")


def fig9_pve_poblacion(d=0.5):
    """Población: cuota del modo verdaderamente mejor entre auto y metro, por banda de ventaja."""
    filas = [f for f in POB["filas"] if f["d"] == d and "cuota_mejor_auto_metro" in f]
    sigmas = sorted({f["sigma"] for f in filas})
    bandas = filas[0]["cuota_mejor_auto_metro"]["bandas"]
    fig, axs = plt.subplots(1, len(bandas), figsize=(10, 3.4), sharey=True)
    for j, (ax, banda) in enumerate(zip(axs, bandas, strict=True)):
        for mu, color in COLOR_MU.items():
            y = [
                next(f for f in filas if f["sigma"] == s and f["mu"] == mu)[
                    "cuota_mejor_auto_metro"
                ]["bandas"][j]["cuota"]
                for s in sigmas
            ]
            ax.plot(sigmas, y, "-o", color=color, ms=3.5, lw=1.6, label=f"μ = {mu:g}")
        ax.axhline(0.5, color=TINTA, lw=0.8, ls=":")
        hasta = "∞" if banda["hasta"] is None else f"{banda['hasta']:g}"
        ax.set_title(
            f"ventaja {banda['desde']:g}–{hasta} útiles\n(n = {banda['n']:,})".replace(",", ".")
        )
        ax.set_xlabel("σ (min)")
        ax.set_ylim(0.4, 1.02)
        limpia(ax)
    axs[0].set_ylabel("cuota del mejor entre auto y metro")
    axs[-1].legend(loc="lower right")  # el único panel con espacio abajo
    guarda(fig, "fig9-pve-poblacion.png")


if __name__ == "__main__":
    fig7_pve()
    fig8_pve_dias()
    fig9_pve_poblacion()
