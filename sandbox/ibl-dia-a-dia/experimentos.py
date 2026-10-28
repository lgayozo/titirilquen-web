"""Una persona que aprende con IBL: shocks tempranos (E1) y variabilidad (E2).

    uv run python experimentos.py      # escribe salida/experimentos.json

Las ecuaciones llevan el número que tienen en el informe (`informe.html`):

    (1) w_ni(t', t) = a_ni(t') (t − t')^(−d) / Σ_τ a_ni(τ) (t − τ)^(−d)    ibl.pesos_ibl
    (2) b_ni(t)     = Σ_t' w_ni(t', t) x_i(t')                          ibl.tiempo_percibido
    (3) V_ni(t)     = V_i^ref + β (b_ni(t) − τ_i)                       `simular`
    (4) P_n(t)      = 1 / (1 + exp(−[V_n,mejor(t) − V_n,peor(t)]))       `simular`, μ = 1
    (5) x_i(t)      = τ_i + Δ·1[shock] + ε_i(t),   ε_i ~ N(0, σ_i)       `simular`

(1)–(2) son las ecuaciones (1)–(2) de Guevara, Tang y Gao (2018, TR-B 117), con
`a_ni(0) = 1`: el día 0 es la percepción inicial, igual al tiempo de equilibrio.

**Los casos son celdas reales.** `run_msa` con la configuración web da los
tiempos de equilibrio; `calcular_utilidades` del núcleo da `V^ref` con sólo
auto y metro y `tiene_auto = True`. Se eligieron tres celdas cuya probabilidad
verdadera del modo mejor barre 0,60 / 0,75 / 0,85 (`CASOS`), uno por estrato.
Con μ = 1 ninguna celda con metro factible pasa de 0,85 a favor del auto ni de
0,65 a favor del metro; el caso de 0,60 es uno donde gana el metro.

**Una persona, no una población.** Cada réplica es la misma persona con su
propia secuencia aleatoria; no hay congestión. El tratamiento y el control usan
la misma semilla (números aleatorios comunes): la diferencia entre ambos es el
efecto, no ruido de muestreo distinto.

**Qué se mide.** Todo en términos del modo MEJOR en media (el de mayor `V^ref`).
La cuota esperada usa la probabilidad del modelo `P_n(t)`, no la elección
sorteada: así las distribuciones muestran lo que la historia le hizo a cada
persona, sin el ruido de Bernoulli de la elección del día.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from titirilquen_core.city import CiudadLineal
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import run_msa

from ibl import tiempo_percibido
from persona import _config_web

SALIDA = Path(__file__).parent / "salida"
MODOS = ("Auto", "Metro")
DIAS = 250
REPLICAS = 500
SEMILLA = 42
# Horizontes: corto, mediano y largo plazo (días, ambos extremos incluidos).
VENTANAS = {"corto": (1, 10), "medio": (11, 50), "largo": (51, 250)}
# (nombre, estrato, celda). 1 = Alto, 2 = Medio, 3 = Bajo; celda 100 = CBD.
CASOS = (("C1", 3, 198), ("C2", 2, 135), ("C3", 1, 111))
# d = 0: promedio simple. 0,5: valor convencional (Guevara et al. 2018, §3.2).
# 1,28: estimado con los datos de Ben-Elia y Shiftan (2010) (Guevara et al. 2018, tabla 4).
DECAIMIENTOS = (0.0, 0.5, 1.28)
# E1: número de experiencias malas y su tamaño, en múltiplos de la ventaja A (min).
E1_K = (1, 2, 3, 5, 10)
E1_R = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0)
# E2: desviación estándar del ruido de la experiencia (min) y en qué modo actúa.
E2_SIGMAS = (0.0, 10.0, 20.0, 40.0, 80.0)
E2_CONDICIONES = ("ambos", "solo_mejor", "solo_peor")
BINS = np.linspace(0.0, 1.0, 21)


@dataclass(frozen=True)
class Caso:
    nombre: str
    estrato: int
    celda: int
    km: float
    tau: np.ndarray  # (2,) tiempo que pondera β: auto total, metro en vehículo
    t_total: np.ndarray  # (2,) auto total, metro acceso + espera + vehículo
    v_ref: np.ndarray  # (2,) utilidad del núcleo con los tiempos de equilibrio
    beta: float  # b_tiempo_viaje del estrato (< 0)

    @property
    def dv(self) -> float:
        """Ventaja del modo mejor en útiles, |V_auto − V_metro|."""
        return float(abs(self.v_ref[0] - self.v_ref[1]))

    @property
    def mejor(self) -> int:
        return 0 if self.v_ref[0] > self.v_ref[1] else 1

    @property
    def ventaja_min(self) -> float:
        """A = ΔV / |β|: la ventaja expresada en minutos equivalentes."""
        return self.dv / abs(self.beta)

    @property
    def p_verdadera(self) -> float:
        return logistica(self.dv)


def logistica(z: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-z))


def casos() -> list[Caso]:
    sim, lu = _config_web()
    s = run_msa(sim, lu, localizacion="equilibrio").iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    out = []
    for nombre, estrato, celda in CASOS:
        t = TiemposObservados(
            auto_total=float(s.t_auto[celda]),
            bici_total=float(s.t_bici[celda]),
            tren_acceso=float(s.t_tren_acceso[celda]),
            tren_espera=float(s.t_tren_espera[celda]),
            tren_viaje=float(s.t_tren_viaje[celda]),
            bici_libre=float(s.t_bici_libre[celda]),
        )
        u = calcular_utilidades(
            estrato=estrato,
            celda_origen=celda,
            tiene_auto=True,
            ciudad=ciudad,
            config=sim.demand,
            tiempos_observados=t,
            modos_habilitados=MODOS,
        )
        out.append(
            Caso(
                nombre=nombre,
                estrato=estrato,
                celda=celda,
                km=(celda - ciudad.cbd_index) * ciudad.ancho_celda_km,
                tau=np.array([t.auto_total, t.tren_viaje]),
                t_total=np.array([t.auto_total, t.tren_acceso + t.tren_espera + t.tren_viaje]),
                v_ref=np.array([u[m].valor for m in MODOS]),
                beta=float(sim.demand.estratos[estrato].betas.b_tiempo_viaje),
            )
        )
    return out


def peso_shocks(k: int, d: float) -> float:
    """W_k: peso conjunto de k experiencias consecutivas frente al prior, ec. (7).

    Si la persona elige el modo los días 1…k, al decidir el día k + 1 las k
    experiencias tienen antigüedad 1…k y el prior (día 0) antigüedad k + 1.
    Con d = 0 da k / (k + 1) sin importar cuándo ocurrieron.
    """
    act = np.arange(1, k + 1, dtype=float) ** (-d)
    return float(act.sum() / (act.sum() + (k + 1.0) ** (-d)))


def delta_critico(caso: Caso, k: int, d: float) -> float:
    """Δ* en minutos: el shock que deja la ventaja percibida en cero, ec. (8)."""
    return caso.ventaja_min / peso_shocks(k, d)


def p_post_analitica(caso: Caso, k: int, d: float, delta: float) -> float:
    """P del mejor al decidir justo después del k-ésimo shock, ec. (9)."""
    return float(logistica(caso.dv - abs(caso.beta) * peso_shocks(k, d) * delta))


def simular(
    caso: Caso,
    *,
    d: float,
    sigma: tuple[float, float] = (0.0, 0.0),
    k: int = 0,
    delta: float = 0.0,
    replicas: int = REPLICAS,
    dias: int = DIAS,
    semilla: int = SEMILLA,
) -> dict[str, np.ndarray]:
    """`replicas` historias independientes de la misma persona, `dias` días.

    `sigma` = (σ_mejor, σ_peor) en minutos. Las primeras `k` veces que la
    persona usa el modo mejor, su experiencia lleva `+delta` minutos.
    """
    rng = np.random.default_rng(semilla)
    m = caso.mejor
    sig = np.zeros(2)
    sig[m], sig[1 - m] = sigma
    x = np.zeros((replicas, dias + 1, 2))
    a = np.zeros((replicas, dias + 1, 2), dtype=bool)
    x[:, 0, :] = caso.tau  # prior: a(0) = 1, x(0) = τ
    a[:, 0, :] = True
    p = np.zeros((replicas, dias))
    elige_mejor = np.zeros((replicas, dias), dtype=bool)
    usos = np.zeros(replicas, dtype=int)  # veces que usó el mejor
    p_post = np.full(replicas, np.nan)  # P al decidir tras el k-ésimo shock
    filas = np.arange(replicas)

    for t in range(1, dias + 1):
        b = tiempo_percibido(x, a, t, d)  # ec. (1)–(2)
        v = caso.v_ref + caso.beta * (b - caso.tau)  # ec. (3)
        p_t = logistica(v[:, m] - v[:, 1 - m])  # ec. (4)
        if k > 0:
            recien = (usos == k) & np.isnan(p_post)
            p_post[recien] = p_t[recien]
        p[:, t - 1] = p_t
        mejor_hoy = rng.random(replicas) < p_t
        elige_mejor[:, t - 1] = mejor_hoy
        modo = np.where(mejor_hoy, m, 1 - m)
        eps = rng.normal(0.0, 1.0, size=(replicas, 2)) * sig
        shock = np.where(mejor_hoy & (usos < k), delta, 0.0)
        x[filas, t, modo] = caso.tau[modo] + eps[filas, modo] + shock  # ec. (5)
        a[filas, t, modo] = True
        usos += mejor_hoy
    return {"p": p, "elige_mejor": elige_mejor, "p_post": p_post}


# --- Indicadores (sección 3 del informe) ---------------------------------------


def cuota_por_persona(p: np.ndarray, ventana: tuple[int, int]) -> np.ndarray:
    """P̄_n = promedio de P_n(t) en la ventana, ec. (10)."""
    a, b = ventana
    return p[:, a - 1 : b].mean(axis=1)


def resumen_ventanas(p: np.ndarray) -> dict:
    """Por horizonte: S (ec. 11), cuantiles e histograma de P̄_n y fracción invertida (ec. 13)."""
    out = {}
    for nombre, ventana in VENTANAS.items():
        pn = cuota_por_persona(p, ventana)
        out[nombre] = {
            "S": float(pn.mean()),
            "cuantiles": np.percentile(pn, [5, 25, 50, 75, 95]).tolist(),
            "histograma": np.histogram(pn, bins=BINS)[0].tolist(),
            "invertidos": float(np.mean(pn < 0.5)),
        }
    return out


def vida_media(brecha: np.ndarray) -> float | None:
    """Días desde el peor punto hasta recuperar la mitad de la brecha, ec. (12).

    `brecha` es s̄_t(tratamiento) − s̄_t(control). None si no se
    recupera dentro del horizonte; 0 si no hay brecha que recuperar.
    """
    t_min = int(np.argmin(brecha))
    peor = brecha[t_min]
    if peor > -0.005:
        return 0.0
    rec = np.nonzero(brecha[t_min:] >= peor / 2)[0]
    return float(rec[0]) if len(rec) else None


def gauss_logistica(m: float, s: float, n: int = 40) -> float:
    """E[Λ(m + s·Z)], Z ~ N(0, 1), por cuadratura de Gauss–Hermite, ec. (16)."""
    z, w = np.polynomial.hermite_e.hermegauss(n)
    return float(np.sum(w * logistica(m + s * z)) / np.sqrt(2 * np.pi))


def descomposicion(caso: Caso, r: dict, d: float, ventana: tuple[int, int]) -> dict:
    """Separa S − P_verdadera en dispersión (PVE) y sesgo (hot stove), ec. (15)–(17).

    La ventaja percibida es ΔV_n(t) = logit P_n(t). Su media sobre personas y
    días es m̂, su desviación ŝ. Con la media verdadera y la dispersión
    observada, E[Λ(ΔV + ŝZ)] es lo que daría sólo el ruido: el efecto de
    variabilidad. Lo que falta hasta S es el desplazamiento de la media.
    """
    a, b = ventana
    p = np.clip(r["p"][:, a - 1 : b], 1e-12, 1 - 1e-12)
    dvp = np.log(p / (1 - p))
    s_hat = float(dvp.std())
    S = float(p.mean())
    p_disp = gauss_logistica(caso.dv, s_hat)
    return {
        "m": float(dvp.mean()),
        "s": s_hat,
        "S": S,
        "P_disp": p_disp,
        "pve": p_disp - caso.p_verdadera,
        "sesgo": S - p_disp,
    }


# --- Experimentos -------------------------------------------------------------


def e1(caso: Caso) -> list[dict]:
    """Shocks tempranos: k experiencias malas de Δ = r·A minutos en el modo mejor."""
    filas = []
    for d in DECAIMIENTOS:
        ctrl = simular(caso, d=d)
        s_ctrl = ctrl["p"].mean(axis=0)
        v_ctrl = resumen_ventanas(ctrl["p"])
        for k in E1_K:
            for r_ in E1_R:
                delta = r_ * caso.ventaja_min
                r = simular(caso, d=d, k=k, delta=delta)
                brecha = r["p"].mean(axis=0) - s_ctrl
                v = resumen_ventanas(r["p"])
                filas.append(
                    {
                        "caso": caso.nombre,
                        "d": d,
                        "k": k,
                        "r": r_,
                        "delta_min": delta,
                        "p_post_sim": float(np.nanmean(r["p_post"])),
                        "p_post_analitica": p_post_analitica(caso, k, d, delta),
                        "llegan_a_k": float(np.mean(~np.isnan(r["p_post"]))),
                        "ventanas": v,
                        "efecto": {w: v[w]["S"] - v_ctrl[w]["S"] for w in VENTANAS},
                        "vida_media": vida_media(brecha),
                        "brecha_final": float(brecha[-15:].mean()),
                        "brecha_por_dia": brecha.round(4).tolist(),
                    }
                )
        filas.append(
            {
                "caso": caso.nombre,
                "d": d,
                "k": 0,
                "control": True,
                "ventanas": v_ctrl,
                "s_por_dia": s_ctrl.round(4).tolist(),
            }
        )
    return filas


def e2(caso: Caso) -> list[dict]:
    """Variabilidad: σ en ambos modos, sólo en el mejor o sólo en el peor."""
    filas = []
    for d in DECAIMIENTOS:
        for cond in E2_CONDICIONES:
            for sigma in E2_SIGMAS:
                sm = sigma if cond in ("ambos", "solo_mejor") else 0.0
                sp = sigma if cond in ("ambos", "solo_peor") else 0.0
                r = simular(caso, d=d, sigma=(sm, sp))
                v = resumen_ventanas(r["p"])
                filas.append(
                    {
                        "caso": caso.nombre,
                        "d": d,
                        "condicion": cond,
                        "sigma": sigma,
                        "sigma_utiles": sigma * abs(caso.beta),
                        "ventanas": v,
                        # ec. (13): fracción de la ventaja verdadera que sobrevive.
                        "phi": {w: (v[w]["S"] - 0.5) / (caso.p_verdadera - 0.5) for w in VENTANAS},
                        "descomposicion": {
                            w: descomposicion(caso, r, d, VENTANAS[w]) for w in VENTANAS
                        },
                        "s_por_dia": r["p"].mean(axis=0).round(4).tolist(),
                    }
                )
    return filas


def main() -> None:
    cs = casos()
    print(f"\n  {DIAS} días · {REPLICAS} réplicas · μ = 1\n")
    for c in cs:
        print(
            f"  {c.nombre}: estrato {c.estrato}, celda {c.celda} ({c.km:+.1f} km) · "
            f"auto {c.t_total[0]:.1f} min, metro {c.t_total[1]:.1f} min · mejor {MODOS[c.mejor]} · "
            f"ΔV {c.dv:.3f} útiles = A {c.ventaja_min:.1f} min · P verdadera {c.p_verdadera:.3f}"
        )
    out = {
        "dias": DIAS,
        "replicas": REPLICAS,
        "semilla": SEMILLA,
        "ventanas": VENTANAS,
        "bins": BINS.tolist(),
        "casos": [
            {
                "nombre": c.nombre,
                "estrato": c.estrato,
                "celda": c.celda,
                "km": c.km,
                "t_auto": float(c.t_total[0]),
                "t_metro": float(c.t_total[1]),
                "tau": c.tau.tolist(),
                "v_ref": c.v_ref.tolist(),
                "beta": c.beta,
                "mejor": MODOS[c.mejor],
                "dv": c.dv,
                "ventaja_min": c.ventaja_min,
                "p_verdadera": c.p_verdadera,
                "w_k": {str(d): {str(k): peso_shocks(k, d) for k in E1_K} for d in DECAIMIENTOS},
                "delta_critico": {
                    str(d): {str(k): delta_critico(c, k, d) for k in E1_K} for d in DECAIMIENTOS
                },
            }
            for c in cs
        ],
        "e1": [],
        "e2": [],
    }
    for c in cs:
        print(f"  E1 {c.nombre} …", flush=True)
        out["e1"] += e1(c)
        print(f"  E2 {c.nombre} …", flush=True)
        out["e2"] += e2(c)
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "experimentos.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"\n  Datos en {SALIDA / 'experimentos.json'}\n")


if __name__ == "__main__":
    main()
