"""Figuras del informe de rho, desde `salida/*.json`.

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


def carga(nombre: str) -> dict:
    return json.loads((SALIDA / f"{nombre}.json").read_text(encoding="utf-8"))


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


def guarda(fig, nombre: str) -> None:
    fig.savefig(SALIDA / nombre, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {nombre}")


# --------------------------------------------------------------------------
def fig1_nivel() -> None:
    """El nivel de rho: inerte con lambda uniforme, activo con lambda ~ 1/y."""
    d = carga("e1-nivel")
    fig, ax = plt.subplots(1, 3, figsize=(11.4, 3.3))

    for k, (reg, titulo) in enumerate(
        (("R0", "λ uniforme (calibración vigente)"), ("R1", "λ ∝ 1/y (propuesta)"))
    ):
        f = d[reg]
        rho = [x["rho"] for x in f]
        for h in range(3):
            ax[k].plot(
                rho, [x["d"][h] for x in f], "o-", color=COL[h], ms=3.4, lw=1.6, label=EST[h]
            )
        ax[k].set_xscale("symlog", linthresh=1e-3)
        ax[k].set_xlabel("ρ (igual para los tres estratos)")
        ax[k].set_ylabel("distancia media al CBD (km)")
        ax[k].set_title(titulo)
        ax[k].set_ylim(0, 9)
    ax[0].legend(loc="center left")

    for reg, est, nom in (("R0", "--", "λ uniforme"), ("R1", "-", "λ ∝ 1/y")):
        f = d[reg]
        ax[2].plot(
            [x["rho"] for x in f],
            [x["pend_p"] for x in f],
            est,
            marker="o",
            ms=3.4,
            lw=1.6,
            color=TINTA if reg == "R1" else GRIS,
            label=nom,
        )
    ax[2].axhline(0, color=ALTO, lw=1.1)
    ax[2].set_xscale("symlog", linthresh=1e-3)
    ax[2].set_xlabel("ρ")
    ax[2].set_ylabel("pendiente de precio ($/km)")
    ax[2].set_title("El precio sí reacciona al nivel")
    ax[2].legend()
    fig.suptitle(
        "FIG. 01 · El nivel de ρ mueve los precios; la localización sólo si λ es heterogéneo",
        y=1.04,
        fontsize=11,
    )
    guarda(fig, "fig1-nivel.png")


# --------------------------------------------------------------------------
def fig2_brecha() -> None:
    """La brecha de elasticidades y la frontera de vuelco."""
    d = carga("e2-brecha")
    br = d["brechas"]
    rhos = d["rhos"]
    M = np.full((len(rhos), len(br)), np.nan)
    for f in d["filas"]:
        M[rhos.index(f["rho0"]), br.index(f["brecha"])] = f["d"][0]

    fig, ax = plt.subplots(1, 2, figsize=(11.0, 3.6))
    im = ax[0].imshow(M, aspect="auto", origin="lower", cmap="RdYlBu_r", vmin=0, vmax=8)
    ax[0].set_xticks(range(len(br)), [f"{x:+.2f}" for x in br], rotation=45, fontsize=7)
    ax[0].set_yticks(range(len(rhos)), [f"{x:g}" for x in rhos], fontsize=7)
    ax[0].set_xlabel("brecha de elasticidades  e_espacio − e_VST")
    ax[0].set_ylabel("ρ₀")
    ax[0].set_title("d del estrato alto (km)")
    ax[0].grid(False)
    fig.colorbar(im, ax=ax[0], label="km al CBD")
    # Contorno del vuelco: donde el alto deja de ser el mas central.
    ok = np.full_like(M, np.nan)
    for f in d["filas"]:
        ok[rhos.index(f["rho0"]), br.index(f["brecha"])] = 1.0 if f["orden_ok"] else 0.0
    ax[0].contour(ok, levels=[0.5], colors="k", linewidths=1.6)

    for i, r0 in enumerate(rhos):
        ax[1].plot(br, M[i], "o-", ms=3.2, lw=1.5, label=f"ρ₀ = {r0:g}")
    ax[1].set_xlabel("brecha  e_espacio − e_VST")
    ax[1].set_ylabel("d del estrato alto (km)")
    ax[1].set_title("El vuelco llega antes con ρ₀ mayor")
    ax[1].legend(fontsize=7.5)
    fig.suptitle(
        "FIG. 02 · Dónde vuelca la ciudad: la condición de Muth/Wheaton en este modelo",
        y=1.04,
        fontsize=11,
    )
    guarda(fig, "fig2-brecha.png")


# --------------------------------------------------------------------------
def fig3_redundancia() -> None:
    """Cuanto del efecto de rho reproduce alpha."""
    d = carga("e3-redundancia")["filas"]
    formas = [f["forma"] for f in d]
    frac = [100.0 * (1.0 - f["frac_no_imitada"]) for f in d]
    fig, ax = plt.subplots(1, 2, figsize=(10.4, 3.2))
    cols = [ALTO if f["forma"] == "bimodal" else MEDIO for f in d]
    ax[0].barh(formas, frac, color=cols, height=0.62)
    ax[0].set_xlim(0, 100)
    ax[0].set_xlabel("% del efecto de ρ que α reproduce")
    ax[0].set_title("ρ como α disfrazado")
    for i, v in enumerate(frac):
        ax[0].text(min(v + 1.5, 96), i, f"{v:.1f} %", va="center", fontsize=8, color=TINTA)

    ax[1].scatter([f["r2"] for f in d], frac, s=44, color=cols, zorder=3)
    for f, v in zip(d, frac, strict=True):
        ax[1].annotate(
            f["forma"], (f["r2"], v), fontsize=7.5, xytext=(4, -3), textcoords="offset points"
        )
    ax[1].set_xlabel("R² del ajuste dens ≈ a − b·T")
    ax[1].set_ylabel("% reproducido por α")
    ax[1].set_title("La redundancia es la colinealidad")
    fig.suptitle(
        "FIG. 03 · Cuánto de lo que hace ρ es propio, por geometría de la ciudad",
        y=1.05,
        fontsize=11,
    )
    guarda(fig, "fig3-redundancia.png")


# --------------------------------------------------------------------------
def fig4_donde() -> None:
    """Donde cae el efecto de rho en el espacio."""
    d = carga("e4-donde")
    base_fr = d["base"]["fronteras"]
    casos = d["casos"]
    claves = [k for k in ("-0.5", "0.5", "1.0", "1.5") if k in casos]
    fig, ax = plt.subplots(1, len(claves), figsize=(3.0 * len(claves), 3.1), sharey=True)
    if len(claves) == 1:
        ax = [ax]
    for k, cl in enumerate(claves):
        c = casos[cl]
        v = np.asarray(c["por_celda"])
        n = len(v)
        km = (np.arange(n) - n // 2) * (20.0 / n)
        ax[k].fill_between(km, v, color=MEDIO, alpha=0.75, lw=0)
        for f in base_fr:
            for s in (-1, 1):
                ax[k].axvline(s * f, color=GRIS, ls=":", lw=1.0)
        for f in c["fronteras"]:
            for s in (-1, 1):
                ax[k].axvline(s * f, color=ALTO, ls="--", lw=1.1)
        ax[k].set_title(f"brecha {float(cl):+.1f}\n{c['movidos_total']:,.0f} hogares")
        ax[k].set_xlabel("km desde el CBD")
        ax[k].set_xlim(-10, 10)
    ax[0].set_ylabel("hogares reubicados por celda")
    fig.suptitle(
        "FIG. 04 · El efecto se concentra en las fronteras entre estratos "
        "(punteado gris: base · rojo: desplazada)",
        y=1.06,
        fontsize=11,
    )
    guarda(fig, "fig4-donde.png")


# --------------------------------------------------------------------------
def fig5_precios() -> None:
    """El nivel de rho contra el gradiente de precios."""
    d = carga("e5-precios")
    f = d["filas"]
    rho = [x["rho0"] for x in f]
    fig, ax = plt.subplots(1, 2, figsize=(10.2, 3.2))
    ax[0].plot(rho, [x["pend_p"] for x in f], "-", lw=1.9, color=TINTA)
    ax[0].axhline(0, color=ALTO, lw=1.1)
    ax[0].axvline(d["vigente"]["rho0"], color=MEDIO, ls="--", lw=1.2)
    ax[0].annotate(
        "ρ vigente",
        (d["vigente"]["rho0"], 0),
        xytext=(6, 12),
        textcoords="offset points",
        fontsize=8,
        color=MEDIO,
    )
    ax[0].set_xlabel("ρ₀")
    ax[0].set_ylabel("pendiente de precio ($/km)")
    ax[0].set_title("Invariante al nivel de p; el cruce por cero es el techo de ρ₀")

    for h in range(3):
        ax[1].plot(rho, [x["d"][h] for x in f], "-", lw=1.7, color=COL[h], label=EST[h])
    ax[1].set_xlabel("ρ₀")
    ax[1].set_ylabel("distancia media (km)")
    ax[1].set_title("Y mientras tanto, la localización casi no se mueve")
    ax[1].legend()
    fig.suptitle(
        "FIG. 05 · El nivel de ρ se calibra contra el precio, no contra el mapa",
        y=1.05,
        fontsize=11,
    )
    guarda(fig, "fig5-precios.png")


# --------------------------------------------------------------------------
def fig6_robustez() -> None:
    """La brecha critica bajo variaciones."""
    d = carga("e7-robustez")
    br = d["brechas"]
    filas = d["variaciones"]
    fig, ax = plt.subplots(1, 2, figsize=(10.6, 3.4))
    for f in filas:
        y = [p["d"][0] for p in f["puntos"]]
        ax[0].plot(br, y, "o-", ms=3.0, lw=1.3, label=f"{f['eje']}: {f['caso']}", alpha=0.85)
    ax[0].set_xlabel("brecha  e_espacio − e_VST")
    ax[0].set_ylabel("d del estrato alto (km)")
    ax[0].set_title("Bajo variaciones de β, σ, shares y forma")
    ax[0].legend(fontsize=6.4, ncol=2)

    for f in d["grilla"]:
        ax[1].plot(
            br, [p["d"][0] for p in f["puntos"]], "o-", ms=3.4, lw=1.6, label=f"L = {f['L']}"
        )
    ax[1].set_xlabel("brecha  e_espacio − e_VST")
    ax[1].set_ylabel("d del estrato alto (km)")
    ax[1].set_title("Invariancia de grilla (D-26)")
    ax[1].legend()
    fig.suptitle("FIG. 06 · Robustez del vuelco", y=1.05, fontsize=11)
    guarda(fig, "fig6-robustez.png")


def main() -> None:
    for fn in (fig1_nivel, fig2_brecha, fig3_redundancia, fig4_donde, fig5_precios, fig6_robustez):
        fn()
    print(f"\n  Figuras en {SALIDA}")


if __name__ == "__main__":
    main()
