"""Fase 1: la población completa aprende día a día, con la congestión endógena.

    uv run python poblacion.py

**Qué se prueba.** Lo mismo que en fase 0 pero con la ciudad entera y el
feedback de la oferta: cada día todos eligen con sus tiempos percibidos, los
flujos cargan la red (`resolver_oferta`: BPR del auto, frecuencia del metro),
y cada persona experimenta el tiempo real de su modo en su celda más un `ε`
propio. Al día siguiente decide con el IBL sobre lo que vivió.

**Sólo auto y metro, y todos con auto (desde el 30-sep-2026).** La ciudad de
la app con dos cambios: `prob_auto = 1` en los tres estratos y
`modos_habilitados = (Auto, Metro)`. Así cada persona elige entre los mismos
dos modos que en las fases 0 y 0-b, y los dos tienen ruido. Hasta esa fecha la
fase 1 tenía los cuatro modos, con bici y caminata sin ruido: eran un refugio
hacia el que migraba la elección por construcción, y parte de la pérdida de
cuota de auto y metro era ese artefacto. Quien vive a menos de 1 km del CBD no
tiene metro (D-69) y sólo puede ir en auto: carga la red, pero no elige.

**Día 0 = el equilibrio MSA de esa ciudad.** `run_msa` entrega la población
(agentes con celda y estrato; la localización de equilibrio ya lee la
accesibilidad con auto para todos), los tiempos de equilibrio por celda y la
partición modal. Esos tiempos son la «información exógena de buena calidad»
del documento: el prior de todos.

**Cómo entra la utilidad del núcleo sin reimplementarla.** La utilidad de un
modo es lineal en su tiempo de viaje: `V = … + b_tiempo_viaje · t`. Se llama
`calcular_utilidades` UNA vez por grupo (estrato, celda, tiene_auto) con los
tiempos del día 0 —`V_ref`— y la utilidad de cada persona cada día es
`V_ref + b_tiempo_viaje · (b_ni − t_ref)`, donde `b_ni` es su tiempo percibido.
Todo lo que cambia día a día vive en `b_ni`; la parte no lineal (ASC, costo,
penalizaciones, factibilidad) queda tal como la calcula el núcleo.

**Unidad de análisis: la población.** Los 29.008 agentes del equilibrio que
eligen, a la vez y acoplados por la congestión; las cuotas son fracciones de
agentes (o de sus viajes), no de réplicas de una persona.

**Supuestos declarados.**
* `ε ~ N(0, σ)`, i.i.d. por persona y día, sobre el AUTO (tiempo total) y sobre
  el METRO (tiempo en vehículo, que es el que pesa `b_tiempo_viaje`; espera y
  acceso quedan en `V_ref`). Sin truncar (ver `persona.py`).
* Teletrabajadores fuera: no eligen.
**La ciudad de la app con los cuatro modos (`python poblacion.py ciudad`).**
La configuración de la app tal cual (tenencia de auto por estrato, auto, metro,
bici y caminata), con el ruido en tres condiciones (`CONDICIONES`): sólo en el
auto, sólo en el metro, y en los dos. Bici y caminata nunca llevan ruido. El
IBL aprende auto, metro y bici —la bici se congestiona en la ciclovía—; la
caminata no: su tiempo es geométrico, sin congestión ni ruido, y queda en
`V_ref`. Las medidas se generalizan a los J modos factibles de cada persona
(con J = 2 son las de la fase 1). Escribe `salida/ciudad4.json`.

* La escala del logit `μ` multiplica las utilidades antes del softmax; `μ = 1`
  es el logit del núcleo y la única escala que se analiza.
"""

from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import run_msa
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.supply.oferta import resolver_oferta

from experimentos import DECAIMIENTOS, VENTANAS
from ibl import tiempo_percibido
from persona import _config_web

#: Los dos modos que se eligen en la fase 1 (y en las fases 0 y 0-b).
MODOS_FASE1 = ("Auto", "Metro")


def _config_fase1() -> tuple[SimulationConfig, LandUseConfig]:
    """La ciudad de la app con todos los estratos con auto y sólo auto y metro."""
    sim, lu = _config_web()
    for h in sim.demand.estratos:
        sim.demand.estratos[h].prob_auto = 1.0
    sim.modos_habilitados = MODOS_FASE1
    return sim, lu


SALIDA = Path(__file__).parent / "salida"
MODOS = ("Auto", "Metro", "Bici", "Caminata")
DIAS = VENTANAS["largo"][1]  # 250: los mismos horizontes que E1 y E2
ULTIMOS = 20
# σ = 0 es la referencia de cada μ: la misma dinámica sin ruido converge al
# equilibrio del logit con escala μ, y el hot stove es la diferencia con σ > 0.
# Hasta 80 min, el mismo rango que E2 (experimentos.py) para una persona.
SIGMAS = (0.0, 5.0, 10.0, 20.0, 40.0, 80.0)
# Escala única: μ = 1, el logit del núcleo. Todos los análisis se hacen con ella.
MUS = (1.0,)


class Escenario:
    """La ciudad, la población y la referencia del día 0, listas para vectorizar.

    Se aprenden los `K` primeros modos de `MODOS`: auto y metro (fase 1), más la
    bici en la ciudad con cuatro modos. La caminata nunca: no tiene congestión
    ni ruido, así que su tiempo percibido es siempre el geométrico.
    """

    def __init__(self, sim: SimulationConfig, lu: LandUseConfig, K: int) -> None:
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
        # Referencia del día 0: tiempos del equilibrio por celda de los modos que
        # se aprenden (auto total, metro en vehículo, bici total), (L, K).
        self.K = K
        self.t_ref = np.stack([s.t_auto, s.t_tren_viaje, s.t_bici][:K], axis=1).astype(float)
        ref = [
            TiemposObservados(
                auto_total=float(s.t_auto[i]),
                bici_total=float(s.t_bici[i]),
                tren_acceso=float(s.t_tren_acceso[i]),
                tren_espera=float(s.t_tren_espera[i]),
                tren_viaje=float(s.t_tren_viaje[i]),
                bici_libre=float(s.t_bici_libre[i]),
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
        # El modo mejor de cada persona y su ventaja sobre el segundo, en el
        # equilibrio (día 0): la referencia de Φ, como el modo mejor y P* de E2
        # (experimentos.py). Sólo cuentan quienes pueden elegir: J ≥ 2 modos.
        Vf = np.where(self.feas, self.V_ref, -np.inf)
        self.J = self.feas.sum(axis=1)
        self.elige = self.J >= 2
        self.mejor = Vf.argmax(axis=1)
        orden = np.sort(Vf, axis=1)
        self.dv = orden[:, -1] - orden[:, -2]


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


#: Bandas de la ventaja del mejor sobre el segundo (útiles) para leer el efecto de
#: variabilidad por tamaño de la ventaja: con ventajas grandes no hay recorrido.
BANDAS = ((0.0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, np.inf))


def _cuota_mejor(esc: Escenario, ult: np.ndarray, v_ult: np.ndarray) -> dict:
    """Efecto de variabilidad del pago, en la población.

    Entre quienes pueden elegir (J ≥ 2 modos factibles), la fracción de sus
    viajes de los últimos días hecha en el modo que de verdad es mejor para
    ellos —por la utilidad verdadera media de esos días—. El efecto dice que con
    más σ esa cuota se acerca a 1/J. Se promedia por persona, en total y por
    banda de ventaja del mejor sobre el segundo.
    """
    Vf = np.where(esc.feas, v_ult, -np.inf)
    mejor = Vf.argmax(axis=1)
    orden = np.sort(Vf, axis=1)
    ventaja = orden[:, -1] - orden[:, -2]
    ok = esc.elige
    cuota = (ult == mejor[:, None]).mean(axis=1)
    out = {"todos": float(cuota[ok].mean()), "n": int(ok.sum()), "bandas": []}
    for lo, hi in BANDAS:
        sel = ok & (ventaja >= lo) & (ventaja < hi)
        out["bandas"].append(
            {
                "desde": lo,
                "hasta": None if np.isinf(hi) else hi,
                "cuota": float(cuota[sel].mean()) if sel.any() else float("nan"),
                "n": int(sel.sum()),
            }
        )
    return out


def _dispersion_iguales(esc: Escenario, ult: np.ndarray) -> float:
    """Varianza del share de días en el modo mejor entre personas iguales, sobre la binomial.

    Personas iguales = mismo (estrato, celda, tenencia de auto) y J ≥ 2: tienen
    el mismo modo mejor del equilibrio. Si todas eligieran con la misma P, la
    varianza de su share en los últimos días sería la binomial p̄(1 − p̄)/ULTIMOS;
    la razón agregada (ponderada por tamaño de grupo) mide cuánto la historia
    diferenció a personas idénticas. Con σ = 0 debe dar ≈ 1. Con dos modos es
    la del share de auto.
    """
    el = esc.elige
    share = (ult[el] == esc.mejor[el][:, None]).mean(axis=1)
    clave = (esc.estrato[el] * esc.ciudad.n_celdas + esc.celda[el]) * 2 + esc.tiene_auto[el]
    _, g = np.unique(clave, return_inverse=True)
    n = np.bincount(g).astype(float)
    p = np.bincount(g, weights=share) / n
    var_obs = np.bincount(g, weights=(share - p[g]) ** 2) / n
    var_bin = p * (1.0 - p) / ult.shape[1]
    ok = n >= 2
    return float((n[ok] * var_obs[ok]).sum() / (n[ok] * var_bin[ok]).sum())


def _phi(esc: Escenario, p_ventana: dict[str, np.ndarray], mu: float) -> dict:
    """Φ = (S − 1/J)/(P* − 1/J) por horizonte, ec. (13) del informe, en la población.

    Con dos modos 1/J = ½ y es la (13) tal cual; con más, el punto de comparación
    es el reparto uniforme entre los J modos factibles de cada persona. S es la
    media de P̄_n del modo mejor del equilibrio; P* la media de su probabilidad
    con los tiempos del equilibrio. Sólo quienes pueden elegir (J ≥ 2); en total
    y por banda de ventaja sobre el segundo. Con σ = 0 debe dar ≈ 1.
    """
    el = esc.elige
    p_est = np.full(esc.N, np.nan)
    P_ref = _softmax_filas(np.where(esc.feas[el], esc.V_ref[el], -np.inf), mu)
    p_est[el] = P_ref[np.arange(el.sum()), esc.mejor[el]]
    u = 1.0 / np.maximum(esc.J, 1)

    def phi(sel: np.ndarray, w: str) -> float:
        U = u[sel].mean()
        return float((p_ventana[w][sel].mean() - U) / (p_est[sel].mean() - U))

    out: dict = {"todos": {w: phi(el, w) for w in VENTANAS}, "bandas": []}
    for lo, hi in BANDAS:
        sel = el & (esc.dv >= lo) & (esc.dv < hi)
        fila = {"desde": lo, "hasta": None if np.isinf(hi) else hi, "n": int(sel.sum())}
        fila["p_estrella"] = float(p_est[sel].mean())
        for w in VENTANAS:
            fila[w] = phi(sel, w)
        out["bandas"].append(fila)
    # Por modo mejor del equilibrio: separa a quienes viven el ruido en su modo
    # mejor de quienes lo viven en uno peor («sólo el mejor» / «sólo el peor» de E2).
    out["por_mejor"] = {}
    for k, m in enumerate(MODOS):
        sel = el & (esc.mejor == k)
        if sel.any():
            fila = {"n": int(sel.sum()), "p_estrella": float(p_est[sel].mean())}
            fila.update({w: phi(sel, w) for w in VENTANAS})
            out["por_mejor"][m] = fila
    return out


def simular(
    esc: Escenario,
    sigma: float,
    mu: float,
    d: float,
    rng: np.random.Generator,
    *,
    ruido: tuple[bool, ...] | None = None,
    truncar: bool = False,
) -> dict:
    # ruido[k]: si el modo aprendido k lleva ε (por defecto, todos).
    N, L, K = esc.N, esc.ciudad.n_celdas, esc.K
    ruido = (True,) * K if ruido is None else ruido
    x = np.zeros((N, DIAS + 1, K))
    a = np.zeros((N, DIAS + 1, K), dtype=bool)
    x[:, 0, :] = esc.t_ref[esc.celda]
    a[:, 0, :] = True
    t_ref = x[:, 0, :].copy()

    modo_hist = np.zeros((N, DIAS), dtype=np.int8)
    p_ventana = {w: np.zeros(N) for w in VENTANAS}  # P̄_n del modo mejor, ec. (10)
    primera_eps = np.full((N, K), np.nan)  # el ε del primer día en cada modo con ruido
    split_dia = np.zeros((DIAS, 4))
    t_auto_medio = np.zeros(DIAS)  # tiempo real del auto, promedio sobre quienes lo usaron
    t_metro_medio = np.zeros(DIAS)
    bienestar = np.zeros(DIAS)  # utilidad VERDADERA media del modo elegido
    bienestar_decision = np.zeros(DIAS)  # la PERCIBIDA, con la que se decidió
    # Utilidad verdadera de cada modo acumulada en los últimos días: define
    # cuál es el mejor para cada persona (efecto de variabilidad).
    v_ult = np.zeros((N, len(MODOS)))

    for t in range(1, DIAS + 1):
        b = tiempo_percibido(x, a, t, d)
        V = esc.V_ref.copy()
        V[:, :K] += esc.btv[:, None] * (b - t_ref)
        V[~esc.feas] = -np.inf
        P = _softmax_filas(V, mu)
        modo = _sortear(P, rng)
        p_mejor = P[np.arange(N), esc.mejor]
        for w, (ini, fin) in VENTANAS.items():
            if ini <= t <= fin:
                p_ventana[w] += p_mejor / (fin - ini + 1)
        modo_hist[:, t - 1] = modo
        bienestar_decision[t - 1] = V[np.arange(N), modo].mean()

        d_auto = np.bincount(esc.celda[modo == 0], minlength=L).astype(float)
        d_metro = np.bincount(esc.celda[modo == 1], minlength=L).astype(float)
        d_bici = np.bincount(esc.celda[modo == 2], minlength=L).astype(float)
        oferta = resolver_oferta(esc.sim, esc.ciudad, d_auto, d_bici, d_metro)
        red = (oferta.auto.t_usuarios_min, oferta.tren.t_viaje_min, oferta.bici.t_usuarios_min)

        eps = rng.normal(0.0, sigma, size=N)
        real = np.stack([np.asarray(r, dtype=float)[esc.celda] for r in red[:K]], axis=1)
        for k in range(K):
            usa = modo == k
            vivido = real[usa, k] + eps[usa] if ruido[k] else real[usa, k]
            x[usa, t, k] = np.maximum(vivido, 0.0) if truncar else vivido
            a[usa, t, k] = True
            if ruido[k]:
                nuevo = usa & np.isnan(primera_eps[:, k])
                primera_eps[nuevo, k] = eps[nuevo]

        split_dia[t - 1] = np.bincount(modo, minlength=4) / N
        t_auto_medio[t - 1] = real[modo == 0, 0].mean() if (modo == 0).any() else np.nan
        t_metro_medio[t - 1] = real[modo == 1, 1].mean() if (modo == 1).any() else np.nan
        V_true = esc.V_ref.copy()
        V_true[:, :K] += esc.btv[:, None] * (real - t_ref)
        bienestar[t - 1] = V_true[np.arange(N), modo].mean()
        if t > DIAS - ULTIMOS:
            v_ult += V_true / ULTIMOS

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
        "bienestar_decision_por_dia": bienestar_decision.tolist(),
    }
    fila["cuota_mejor_auto_metro"] = _cuota_mejor(esc, ult, v_ult)
    fila["dispersion_iguales"] = _dispersion_iguales(esc, ult)
    fila["phi"] = _phi(esc, p_ventana, mu)
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
    esc = Escenario(*_config_fase1(), K=2)
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


#: Ruido de la ciudad con cuatro modos: si ε entra en (auto, metro, bici).
#: Bici y caminata nunca llevan ruido; la caminata ni siquiera se aprende.
CONDICIONES = {
    "auto": (True, False, False),
    "tp": (False, True, False),
    "auto_tp": (True, True, False),
}
_ESC: Escenario | None = None


def _inicia_ciudad() -> None:
    global _ESC
    _ESC = Escenario(*_config_web(), K=3)


def _corre_ciudad(clave: tuple[str, float, float]) -> dict:
    cond, sigma, d = clave
    ruido = CONDICIONES.get(cond, (False, False, False))
    r = simular(_ESC, sigma, MUS[0], d, np.random.default_rng(42), ruido=ruido)
    r["condicion"] = cond
    return r


def main_ciudad() -> None:
    """La ciudad de la app con los cuatro modos → salida/ciudad4.json."""
    t0 = time.time()
    esc = Escenario(*_config_web(), K=3)
    print(
        f"\n  CIUDAD · cuatro modos: {esc.N} agentes que eligen, {esc.n_grupos} grupos, "
        f"{DIAS} días · partición del equilibrio: "
        + "  ".join(
            f"{m} {100 * v:.1f}%" for m, v in zip(MODOS, esc.split_equilibrio, strict=True)
        ),
        flush=True,
    )
    claves = [("sin_ruido", 0.0, d) for d in DECAIMIENTOS] + [
        (c, s, d) for c in CONDICIONES for s in SIGMAS if s > 0 for d in DECAIMIENTOS
    ]
    filas = []
    with Pool(6, initializer=_inicia_ciudad) as pool:
        for i, r in enumerate(pool.imap_unordered(_corre_ciudad, claves), 1):
            filas.append(r)
            print(
                f"  [{i}/{len(claves)}] {r['condicion']:<9} σ={r['sigma']:>3.0f} d={r['d']:<4}"
                f" Φ corto {r['phi']['todos']['corto']:.3f} largo {r['phi']['todos']['largo']:.3f}"
                f"  ({time.time() - t0:.0f} s)",
                flush=True,
            )
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "ciudad4.json").write_text(
        json.dumps(
            {
                "N": esc.N,
                "dias": DIAS,
                "ultimos": ULTIMOS,
                "modos": MODOS,
                "split_equilibrio": esc.split_equilibrio,
                "condiciones": CONDICIONES,
                "filas": filas,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\n  Datos en {SALIDA / 'ciudad4.json'}  ({time.time() - t0:.0f} s en total)\n")


if __name__ == "__main__":
    if "ciudad" in sys.argv[1:]:
        main_ciudad()
    else:
        main()
