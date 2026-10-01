"""Fase 0-b: el efecto de variabilidad del pago (payoff variability effect), una persona.

    uv run python pve.py

**Qué se prueba.** El efecto de variabilidad del pago dice que al aumentar la
varianza de los pagos, manteniendo sus medias, la elección se vuelve más
aleatoria: la cuota de la alternativa mejor en media se acerca a 1/2. En un
modelo de aprendizaje como el IBL eso tiene un mecanismo concreto: el tiempo
percibido `b_ni` es un promedio ponderado de pocas experiencias ruidosas, y si
su ruido supera la diferencia de medias, elegir por `b_ni` es casi tirar una
moneda.

**Por qué un caso distinto al de la fase 0.** Allí auto y metro estaban en la
indiferencia (P ≈ 0,507), así que no hay recorrido hacia 1/2 que medir. Acá se
usa el estrato Medio a 4,5 km (celda 145): el auto gana por 0,285 útiles, unos
8,6 minutos equivalentes. Se eligió barriendo celdas y estratos por una ventaja
de ~0,3 útiles, que deja la cuota verdadera en 0,57 / 0,70 / 0,95 con
μ = 1 / 3 / 10.

**Tres condiciones de ruido, para separar dos efectos.**
* `ambos`: el mismo σ en auto y metro. Es la prueba limpia del efecto de
  variabilidad: las medias no cambian, sólo la varianza de los dos pagos.
* `solo_mejor`: σ sólo en el auto (el mejor en media). Además del efecto de
  variabilidad actúa el hot stove: una mala racha del auto lo saca del
  muestreo y ya no se corrige, así que la cuota puede caer bajo 1/2.
* `solo_peor`: σ sólo en el metro. El hot stove juega a favor del auto.

**Unidad de análisis: una persona.** Cada réplica es la misma persona con su
propia secuencia de ε; las 500 réplicas estiman la distribución de su
conducta, no una población (no hay congestión ni interacción).

**Supuestos declarados.** Los de la fase 0 (prior en t' = 0, ε normal sin
truncar, ver `persona.py`), y ε sobre el tiempo que pesa `b_tiempo_viaje`: el total
del auto y el tiempo en vehículo del metro, como en la fase 1. La utilidad es
lineal en esos tiempos, así que se llama `calcular_utilidades` una vez, con los
tiempos del equilibrio, y cada día se corrige `V = V_ref + b_tv·(b − t_ref)`.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from titirilquen_core.city import CiudadLineal
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import run_msa

from ibl import tiempo_percibido
from persona import _config_web

SALIDA = Path(__file__).parent / "salida"
MODOS = ("Auto", "Metro")
ESTRATO = 2  # Medio
CELDA = 145  # 4,5 km del CBD
DIAS = 100
ULTIMOS = 20
REPLICAS = 500
SIGMAS = (0.0, 5.0, 10.0, 20.0, 40.0)
MUS = (1.0, 3.0, 10.0)
DECAIMIENTOS = (0.0, 0.5, 1.0)
CONDICIONES = {"ambos": (True, True), "solo_mejor": (True, False), "solo_peor": (False, True)}


def referencia() -> dict:
    """Tiempos del equilibrio MSA en la celda y la utilidad del núcleo con ellos."""
    sim, lu = _config_web()
    s = run_msa(sim, lu, localizacion="equilibrio").iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    t = TiemposObservados(
        auto_total=float(s.t_auto[CELDA]),
        bici_total=float(s.t_bici[CELDA]),
        tren_acceso=float(s.t_tren_acceso[CELDA]),
        tren_espera=float(s.t_tren_espera[CELDA]),
        tren_viaje=float(s.t_tren_viaje[CELDA]),
    )
    u = calcular_utilidades(
        estrato=ESTRATO,
        celda_origen=CELDA,
        tiene_auto=True,
        ciudad=ciudad,
        config=sim.demand,
        tiempos_observados=t,
        modos_habilitados=MODOS,
    )
    return {
        "V_ref": np.array([u[m].valor for m in MODOS]),
        "t_ref": np.array([t.auto_total, t.tren_viaje]),
        "btv": float(sim.demand.estratos[ESTRATO].betas.b_tiempo_viaje),
        "t_auto": t.auto_total,
        "t_metro": t.tren_acceso + t.tren_espera + t.tren_viaje,
    }


def p_mejor(dv: float, mu: float) -> float:
    """Probabilidad logit del auto (el mejor) con escala μ y ventaja `dv` en útiles."""
    return float(1.0 / (1.0 + np.exp(-mu * dv)))


def simular(
    ref: dict, cond: str, sigma: float, mu: float, d: float, *, truncar: bool = False
) -> dict:
    rng = np.random.default_rng(42)
    n = REPLICAS
    ruido = np.array(CONDICIONES[cond], dtype=float) * sigma
    x = np.zeros((n, DIAS + 1, 2))
    a = np.zeros((n, DIAS + 1, 2), dtype=bool)
    x[:, 0, :] = ref["t_ref"]
    a[:, 0, :] = True
    elige_auto = np.zeros((n, DIAS), dtype=bool)
    for t in range(1, DIAS + 1):
        b = tiempo_percibido(x, a, t, d)
        V = ref["V_ref"] + ref["btv"] * (b - ref["t_ref"])
        auto = rng.random(n) < 1.0 / (1.0 + np.exp(-mu * (V[:, 0] - V[:, 1])))
        elige_auto[:, t - 1] = auto
        eps = rng.normal(0.0, 1.0, size=(n, 2)) * ruido
        for k, usa in ((0, auto), (1, ~auto)):
            vivido = ref["t_ref"][k] + eps[usa, k]
            x[usa, t, k] = np.maximum(vivido, 0.0) if truncar else vivido
            a[usa, t, k] = True
    return {
        "condicion": cond,
        "sigma": sigma,
        "mu": mu,
        "d": d,
        "cuota_mejor_ultimos": float(elige_auto[:, -ULTIMOS:].mean()),
        "cuota_mejor_por_dia": elige_auto.mean(axis=0).tolist(),
        "abandono_mejor": float(np.mean(elige_auto[:, -ULTIMOS:].sum(axis=1) == 0)),
    }


def main() -> None:
    ref = referencia()
    dv = float(ref["V_ref"][0] - ref["V_ref"][1])
    print(
        f"\n  FASE 0-b · una persona (estrato {ESTRATO}, celda {CELDA}, {DIAS} días, "
        f"{REPLICAS} réplicas)\n  auto {ref['t_auto']:.1f} min · metro {ref['t_metro']:.1f} min · "
        f"ventaja del auto {dv:+.3f} útiles ({dv / abs(ref['btv']):+.1f} min eq.)"
    )
    filas = []
    for cond in CONDICIONES:
        print(f"\n  condición «{cond}» — cuota del mejor (auto), últimos {ULTIMOS} días")
        print(
            f"  {'μ':>4}{'d':>5}{'P verdad':>10}"
            + "".join(f"{'σ=' + str(int(s)):>9}" for s in SIGMAS)
        )
        for mu in MUS:
            for d in DECAIMIENTOS:
                fila_txt = f"  {mu:>4.0f}{d:>5.1f}{p_mejor(dv, mu):>10.3f}"
                for sigma in SIGMAS:
                    r = simular(ref, cond, sigma, mu, d)
                    r["p_mejor_verdadera"] = p_mejor(dv, mu)
                    filas.append(r)
                    fila_txt += f"{r['cuota_mejor_ultimos']:>9.3f}"
                print(fila_txt)
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "pve.json").write_text(
        json.dumps(
            {
                "estrato": ESTRATO,
                "celda": CELDA,
                "dias": DIAS,
                "ultimos": ULTIMOS,
                "replicas": REPLICAS,
                "t_auto": ref["t_auto"],
                "t_metro": ref["t_metro"],
                "ventaja_utiles": dv,
                "ventaja_min_eq": dv / abs(ref["btv"]),
                "filas": filas,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\n  Datos en {SALIDA / 'pve.json'}\n")


if __name__ == "__main__":
    main()
