"""Fase 1: la población completa aprende día a día, con la congestión endógena.

    uv run python poblacion.py

**Qué se prueba.** Lo mismo que en fase 0 pero con la ciudad entera y el
feedback de la oferta: cada día todos eligen con sus tiempos percibidos, los
flujos cargan la red (`resolver_oferta`: BPR del auto, frecuencia del metro),
y cada persona experimenta el tiempo real de su modo en su celda más un `ε`
propio. Al día siguiente decide con el IBL sobre lo que vivió.

**Día 0 = el equilibrio MSA de la app.** `run_msa` con la configuración web
entrega la población (agentes con celda, estrato y auto), los tiempos de
equilibrio por celda y la partición modal. Esos tiempos son la «información
exógena de buena calidad» del documento: el prior de todos.

**Cómo entra la utilidad del núcleo sin reimplementarla.** La utilidad de un
modo es lineal en su tiempo de viaje: `V = … + b_tiempo_viaje · t`. Se llama
`calcular_utilidades` UNA vez por grupo (estrato, celda, tiene_auto) con los
tiempos del día 0 —`V_ref`— y la utilidad de cada persona cada día es
`V_ref + b_tiempo_viaje · (b_ni − t_ref)`, donde `b_ni` es su tiempo percibido.
Todo lo que cambia día a día vive en `b_ni`; la parte no lineal (ASC, costo,
penalizaciones, factibilidad) queda tal como la calcula el núcleo.

**Supuestos declarados.**
* `ε ~ N(0, σ)`, i.i.d. por persona y día, sobre el AUTO (tiempo total) y sobre
  el METRO (tiempo en vehículo, que es el que pesa `b_tiempo_viaje`; espera y
  acceso quedan en `V_ref`). Sin truncar en flujo libre (ver fase 0).
* Bici y caminata no tienen `ε` y su utilidad queda congelada en `V_ref`: sus
  penalizaciones por umbral no son lineales en el tiempo y no son el objeto del
  documento. Sus flujos sí cargan la red cada día.
* Teletrabajadores fuera: no eligen.
* La escala del logit `μ` multiplica las utilidades antes del softmax; `μ = 1`
  es el logit del núcleo.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import run_msa
from titirilquen_core.supply.oferta import resolver_oferta

from ibl import tiempo_percibido
from persona import _config_web

SALIDA = Path(__file__).parent / "salida"
MODOS = ("Auto", "Metro", "Bici", "Caminata")
DIAS = 100
ULTIMOS = 20
# σ = 0 es la referencia de cada μ: la misma dinámica sin ruido converge al
# equilibrio del logit con escala μ, y el hot stove es la diferencia con σ > 0.
SIGMAS = (0.0, 5.0, 10.0, 20.0)
MUS = (1.0, 3.0, 10.0)
DECAIMIENTOS = (0.0, 0.5, 1.0)


class Escenario:
    """La ciudad, la población y la referencia del día 0, listas para vectorizar."""

    def __init__(self) -> None:
        sim, lu = _config_web()
        trace = run_msa(sim, lu, localizacion="equilibrio")
        s = trace.iteraciones[-1]
        self.sim: SimulationConfig = sim
        self.ciudad = CiudadLineal(
            n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km
        )
        L = self.ciudad.n_celdas
        agentes = [a for a in trace.agentes if not a.teletrabaja]
        self.N = len(agentes)
        self.celda = np.array([a.celda_origen for a in agentes])
        self.estrato = np.array([a.estrato for a in agentes])
        self.tiene_auto = np.array([a.tiene_auto for a in agentes])
        # Referencia del día 0: tiempos del equilibrio por celda.
        self.t_auto_ref = np.asarray(s.t_auto, dtype=float)
        self.t_viaje_ref = np.asarray(s.t_tren_viaje, dtype=float)
        ref = [
            TiemposObservados(
                auto_total=float(s.t_auto[i]),
                bici_total=float(s.t_bici[i]),
                tren_acceso=float(s.t_tren_acceso[i]),
                tren_espera=float(s.t_tren_espera[i]),
                tren_viaje=float(s.t_tren_viaje[i]),
            )
            for i in range(L)
        ]
        # V_ref y factibilidad, una vez por grupo (estrato, celda, auto).
        cache: dict[tuple[int, int, bool], tuple[np.ndarray, np.ndarray]] = {}
        self.V_ref = np.zeros((self.N, 4))
        self.feas = np.zeros((self.N, 4), dtype=bool)
        for n in range(self.N):
            key = (int(self.estrato[n]), int(self.celda[n]), bool(self.tiene_auto[n]))
            if key not in cache:
                u = calcular_utilidades(
                    estrato=key[0],
                    celda_origen=key[1],
                    tiene_auto=key[2],
                    ciudad=self.ciudad,
                    config=sim.demand,
                    tiempos_observados=ref[key[1]],
                    modos_habilitados=sim.modos_habilitados,
                )
                cache[key] = (
                    np.array([u[m].valor for m in MODOS]),
                    np.array([u[m].feasible for m in MODOS]),
                )
            self.V_ref[n], self.feas[n] = cache[key]
        self.btv = np.array(
            [sim.demand.estratos[int(h)].betas.b_tiempo_viaje for h in self.estrato]
        )
        # La partición modal del equilibrio, sobre los que eligen.
        split = s.modal_split
        tot = sum(v for m, v in split.items() if m != "Teletrabajo")
        self.split_equilibrio = [split[m] / tot for m in MODOS]
        self.n_grupos = len(cache)


def _softmax_filas(V: np.ndarray, mu: float) -> np.ndarray:
    z = mu * (V - V.max(axis=1, keepdims=True))
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sortear(P: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    cum = P.cumsum(axis=1)
    u = rng.random(P.shape[0])[:, None]
    return np.minimum((u > cum).sum(axis=1), P.shape[1] - 1)


def _suerte(primera_eps: np.ndarray, ult_share: np.ndarray) -> tuple[float, float]:
    """Share final de quienes tuvieron la primera experiencia en el decil peor vs mejor."""
    ok = ~np.isnan(primera_eps)
    if ok.sum() < 20:
        return float("nan"), float("nan")
    q10, q90 = np.nanpercentile(primera_eps, [10, 90])
    mala = ult_share[ok & (primera_eps >= q90)]
    buena = ult_share[ok & (primera_eps <= q10)]
    return float(mala.mean()), float(buena.mean())


def simular(esc: Escenario, sigma: float, mu: float, d: float, rng: np.random.Generator) -> dict:
    N, L = esc.N, esc.ciudad.n_celdas
    x = np.zeros((N, DIAS + 1, 2))
    a = np.zeros((N, DIAS + 1, 2), dtype=bool)
    x[:, 0, 0] = esc.t_auto_ref[esc.celda]
    x[:, 0, 1] = esc.t_viaje_ref[esc.celda]
    a[:, 0, :] = True
    t_ref = x[:, 0, :].copy()

    modo_hist = np.zeros((N, DIAS), dtype=np.int8)
    primera_eps = np.full((N, 2), np.nan)  # el ε del primer día en auto / metro
    split_dia = np.zeros((DIAS, 4))
    t_auto_medio = np.zeros(DIAS)  # tiempo real del auto, promedio sobre quienes lo usaron
    t_metro_medio = np.zeros(DIAS)
    bienestar = np.zeros(DIAS)  # utilidad VERDADERA media del modo elegido

    for t in range(1, DIAS + 1):
        b = tiempo_percibido(x, a, t, d)
        V = esc.V_ref.copy()
        V[:, :2] += esc.btv[:, None] * (b - t_ref)
        V[~esc.feas] = -np.inf
        modo = _sortear(_softmax_filas(V, mu), rng)
        modo_hist[:, t - 1] = modo

        d_auto = np.bincount(esc.celda[modo == 0], minlength=L).astype(float)
        d_metro = np.bincount(esc.celda[modo == 1], minlength=L).astype(float)
        d_bici = np.bincount(esc.celda[modo == 2], minlength=L).astype(float)
        oferta = resolver_oferta(esc.sim, esc.ciudad, d_auto, d_bici, d_metro)
        t_auto_dia = np.asarray(oferta.auto.t_usuarios_min, dtype=float)
        t_viaje_dia = np.asarray(oferta.tren.t_viaje_min, dtype=float)

        eps = rng.normal(0.0, sigma, size=N)
        real = np.stack([t_auto_dia[esc.celda], t_viaje_dia[esc.celda]], axis=1)
        for k in (0, 1):
            usa = modo == k
            x[usa, t, k] = np.maximum(real[usa, k] + eps[usa], 0.0)
            a[usa, t, k] = True
            nuevo = usa & np.isnan(primera_eps[:, k])
            primera_eps[nuevo, k] = eps[nuevo]

        split_dia[t - 1] = np.bincount(modo, minlength=4) / N
        t_auto_medio[t - 1] = real[modo == 0, 0].mean() if (modo == 0).any() else np.nan
        t_metro_medio[t - 1] = real[modo == 1, 1].mean() if (modo == 1).any() else np.nan
        V_true = esc.V_ref.copy()
        V_true[:, :2] += esc.btv[:, None] * (real - t_ref)
        bienestar[t - 1] = V_true[np.arange(N), modo].mean()

    ult = modo_hist[:, -ULTIMOS:]
    fila = {
        "sigma": sigma,
        "mu": mu,
        "d": d,
        "split_por_dia": split_dia.tolist(),
        "split_ultimos": split_dia[-ULTIMOS:].mean(axis=0).tolist(),
        "split_ultimos_std_auto": float(split_dia[-ULTIMOS:, 0].std()),
        "t_auto_medio_por_dia": t_auto_medio.tolist(),
        "t_metro_medio_por_dia": t_metro_medio.tolist(),
        "bienestar_por_dia": bienestar.tolist(),
    }
    for k, nombre in ((0, "auto"), (1, "metro")):
        puede = esc.feas[:, k]
        share_ult = (ult == k).mean(axis=1)
        fila[f"abandono_{nombre}"] = float(np.mean(share_ult[puede] == 0.0))
        mala, buena = _suerte(primera_eps[puede, k], share_ult[puede])
        fila[f"share_fin_mala_suerte_{nombre}"] = mala
        fila[f"share_fin_buena_suerte_{nombre}"] = buena
    return fila


def main() -> None:
    t0 = time.time()
    esc = Escenario()
    print(
        f"\n  FASE 1 · población: {esc.N} agentes que eligen, {esc.n_grupos} grupos, "
        f"{DIAS} días  (escenario en {time.time() - t0:.1f} s)"
    )
    print(
        "  partición del equilibrio MSA (día 0): "
        + "  ".join(f"{m} {100 * v:.1f}%" for m, v in zip(MODOS, esc.split_equilibrio, strict=True))
    )
    print(
        f"\n  {'σ':>4}{'μ':>5}{'d':>5}{'auto fin':>10}{'metro fin':>11}{'aband.auto':>12}"
        f"{'aband.metro':>13}{'auto|mala':>11}{'auto|buena':>12}{'t_auto fin':>12}{'s':>6}"
    )
    print("  " + "-" * 99)
    filas = []
    for sigma in SIGMAS:
        for mu in MUS:
            for d in DECAIMIENTOS:
                t1 = time.time()
                r = simular(esc, sigma, mu, d, np.random.default_rng(42))
                filas.append(r)
                print(
                    f"  {sigma:>4.0f}{mu:>5.0f}{d:>5.1f}{r['split_ultimos'][0]:>10.3f}"
                    f"{r['split_ultimos'][1]:>11.3f}{r['abandono_auto']:>12.3f}"
                    f"{r['abandono_metro']:>13.3f}{r['share_fin_mala_suerte_auto']:>11.3f}"
                    f"{r['share_fin_buena_suerte_auto']:>12.3f}"
                    f"{np.nanmean(r['t_auto_medio_por_dia'][-ULTIMOS:]):>12.2f}"
                    f"{time.time() - t1:>6.0f}"
                )
    print()
    print("  Deltas respecto de σ = 0 (misma μ y d): el efecto del ruido y del aprendizaje")
    print(
        f"  {'σ':>4}{'μ':>5}{'d':>5}{'Δ auto fin':>12}{'Δ metro fin':>13}{'Δ aband.auto':>14}"
        f"{'Δ aband.metro':>15}{'Δ bienestar':>13}"
    )
    print("  " + "-" * 81)
    ref = {(r["mu"], r["d"]): r for r in filas if r["sigma"] == 0.0}
    for r in filas:
        if r["sigma"] == 0.0:
            continue
        r0 = ref[(r["mu"], r["d"])]
        r["delta_vs_sigma0"] = {
            "auto_fin": r["split_ultimos"][0] - r0["split_ultimos"][0],
            "metro_fin": r["split_ultimos"][1] - r0["split_ultimos"][1],
            "abandono_auto": r["abandono_auto"] - r0["abandono_auto"],
            "abandono_metro": r["abandono_metro"] - r0["abandono_metro"],
            "bienestar": float(
                np.mean(r["bienestar_por_dia"][-ULTIMOS:])
                - np.mean(r0["bienestar_por_dia"][-ULTIMOS:])
            ),
        }
        dv = r["delta_vs_sigma0"]
        print(
            f"  {r['sigma']:>4.0f}{r['mu']:>5.0f}{r['d']:>5.1f}{dv['auto_fin']:>+12.3f}"
            f"{dv['metro_fin']:>+13.3f}{dv['abandono_auto']:>+14.3f}{dv['abandono_metro']:>+15.3f}"
            f"{dv['bienestar']:>+13.4f}"
        )
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "poblacion.json").write_text(
        json.dumps(
            {
                "N": esc.N,
                "dias": DIAS,
                "ultimos": ULTIMOS,
                "modos": MODOS,
                "split_equilibrio": esc.split_equilibrio,
                "filas": filas,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\n  Datos en {SALIDA / 'poblacion.json'}  ({time.time() - t0:.0f} s en total)\n")


if __name__ == "__main__":
    main()
