"""Fase 0: una persona que aprende el tiempo del auto día a día.

    uv run python persona.py

**Qué se prueba.** El hot stove effect en su forma mínima: una persona elige
cada día entre auto y metro. El tiempo «verdadero» de cada modo es fijo —el del
equilibrio MSA de la configuración por defecto de la app, en su celda— pero el
del auto lo experimenta con un error idiosincrático `ε ~ N(0, σ)` cada día que
lo usa. Percibe el auto según el IBL (`ibl.py`) y elige con el logit del
núcleo. Si una mala racha temprana en el auto la deja en el metro aunque el
auto sea mejor en media, eso es el hot stove effect.

**Qué se reutiliza del núcleo, y qué no.** La utilidad es exactamente
`calcular_utilidades` del núcleo, con el tiempo percibido del auto en lugar
del observado: no se reimplementa. Lo único que se agrega es una **escala
`μ`** sobre las utilidades antes del softmax, porque la escala del logit
decide si el efecto se ve (con μ = 1 es `probabilidades_logit` tal cual). El
tiempo «verdadero» sale de `run_msa` con la configuración web de
`tests/test_linea_base.py`.

**Réplicas.** Una persona sola es una trayectoria aleatoria; para medir hay
que correr muchas personas independientes con los mismos parámetros. Cada
réplica es una persona idéntica con su propia secuencia de `ε`.

**Supuestos declarados.**
* El prior del día 1 es una instancia con `a = 1` para los dos modos (ver `ibl.py`).
* `ε` es normal, i.i.d. por día, sólo sobre el auto y con media cero; NO se
  trunca en flujo libre (ver el comentario en `simular`: truncar sesga).
* Bici y caminata quedan deshabilitadas: el documento habla de auto contra
  el otro modo, y cada modo extra diluye el efecto sin agregar nada en fase 0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import run_msa
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import DEFAULT_STRATA

from ibl import tiempo_percibido

SALIDA = Path(__file__).parent / "salida"
MODOS = ("Auto", "Metro")
# El caso: estrato Medio a 5,8 km. Es donde auto y metro están más parejos en
# el equilibrio (auto 12,0 min vs metro 20,3; V_auto − V_metro = +0,03 útiles,
# +0,8 min equivalentes). Se eligió barriendo celdas y estratos: en el Alto a
# 5 km el auto gana por 1,2 útiles (36 min equivalentes) y ningún shock lo da
# vuelta — hot stove = 0 en las 27 combinaciones. El efecto vive donde las
# alternativas compiten, como en la figura 6.b del paper.
ESTRATO = 2  # StratumId: 1 = Alto, 2 = Medio, 3 = Bajo
CELDA = 158  # 5,8 km del CBD en la ciudad de 201 celdas y 20 km
DIAS = 100
REPLICAS = 500
SIGMAS = (5.0, 10.0, 20.0)  # min
MUS = (1.0, 3.0, 10.0)  # escala del logit; 1 = el logit del núcleo tal cual
DECAIMIENTOS = (0.0, 0.5, 1.0)


def _config_web() -> tuple[SimulationConfig, LandUseConfig]:
    """La corrida por defecto de la app (copiada de tests/test_linea_base.py)."""
    sim = SimulationConfig(
        city=CityConfig(n_celdas=201, largo_ciudad_km=20),
        supply=SupplyConfig(),
        demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}),
        max_iter=20,
        tolerance=0.1,
        seed=42,
        assignment="expected",
    )
    lu = LandUseConfig(
        H_por_estrato=(7200, 18000, 10800), forma="normal", oferta_sigma_frac=0.5, max_iter=2000
    )
    return sim, lu


@dataclass(frozen=True)
class Escenario:
    ciudad: CiudadLineal
    demand: DemandConfig
    equilibrio: TiemposObservados  # tiempos «verdaderos» en la celda
    t_auto_libre: float


def escenario() -> Escenario:
    sim, lu = _config_web()
    trace = run_msa(sim, lu, localizacion="equilibrio")
    s = trace.iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    eq = TiemposObservados(
        auto_total=float(s.t_auto[CELDA]),
        bici_total=float(s.t_bici[CELDA]),
        tren_acceso=float(s.t_tren_acceso[CELDA]),
        tren_espera=float(s.t_tren_espera[CELDA]),
        tren_viaje=float(s.t_tren_viaje[CELDA]),
    )
    dist_km = abs(ciudad.cbd_index - CELDA) * ciudad.ancho_celda_km
    libre = dist_km / sim.demand.globales.v_auto * 60
    return Escenario(ciudad, sim.demand, eq, libre)


def utilidades(esc: Escenario, t_auto_percibido: float) -> np.ndarray:
    """`V = (V_auto, V_metro)` del núcleo, con el auto percibido en lugar del observado."""
    tiempos = TiemposObservados(
        auto_total=t_auto_percibido,
        bici_total=esc.equilibrio.bici_total,
        tren_acceso=esc.equilibrio.tren_acceso,
        tren_espera=esc.equilibrio.tren_espera,
        tren_viaje=esc.equilibrio.tren_viaje,
    )
    u = calcular_utilidades(
        estrato=ESTRATO,
        celda_origen=CELDA,
        tiene_auto=True,
        ciudad=esc.ciudad,
        config=esc.demand,
        tiempos_observados=tiempos,
        modos_habilitados=MODOS,
    )
    return np.array([u[m].valor for m in MODOS])


def prob_auto(v: np.ndarray, mu: float) -> float:
    """Softmax con escala μ. Con μ = 1 coincide con `probabilidades_logit`."""
    z = mu * (v - v.max())
    e = np.exp(z)
    return float(e[0] / e.sum())


def simular(esc: Escenario, sigma: float, mu: float, d: float, rng: np.random.Generator) -> dict:
    """`REPLICAS` personas idénticas e independientes, `DIAS` días cada una."""
    n = REPLICAS
    x = np.zeros((n, DIAS + 1, 2))
    a = np.zeros((n, DIAS + 1, 2), dtype=bool)
    # Prior: día 0, ambos modos «experimentados» con el tiempo de equilibrio.
    x[:, 0, 0] = esc.equilibrio.auto_total
    x[:, 0, 1] = esc.equilibrio.tren_acceso + esc.equilibrio.tren_espera + esc.equilibrio.tren_viaje
    a[:, 0, :] = True

    elige_auto = np.zeros((n, DIAS), dtype=bool)
    percibido_auto = np.zeros((n, DIAS))
    # La utilidad es lineal en el tiempo del auto, así que se evalúa una vez
    # por valor percibido distinto: cache por redondeo a 0,01 min.
    cache: dict[float, np.ndarray] = {}

    for t in range(1, DIAS + 1):
        b = tiempo_percibido(x, a, t, d)  # (n, 2)
        percibido_auto[:, t - 1] = b[:, 0]
        p = np.empty(n)
        for k, ta in enumerate(b[:, 0]):
            key = round(float(ta), 2)
            v = cache.get(key)
            if v is None:
                v = utilidades(esc, key)
                cache[key] = v
            p[k] = prob_auto(v, mu)
        auto = rng.random(n) < p
        elige_auto[:, t - 1] = auto
        # Experiencia del día: el auto con su ε, el metro sin ruido (fase 0).
        # SIN truncar en flujo libre: el equilibrio del auto (12,0 min) está a
        # 0,8 min del flujo libre (11,2), así que truncar por abajo sesga la
        # media experimentada varios minutos hacia arriba y eso, con una ventaja
        # real de 0,8 min, vuelca a todos por sesgo y no por hot stove (medido:
        # «cree que el auto es peor» ≈ 100 % en las 27 combinaciones). ε es ruido
        # de percepción con media cero; sólo se impide un tiempo negativo.
        eps = rng.normal(0.0, sigma, size=n)
        x[auto, t, 0] = np.maximum(esc.equilibrio.auto_total + eps[auto], 0.0)
        a[auto, t, 0] = True
        x[~auto, t, 1] = x[0, 0, 1]
        a[~auto, t, 1] = True

    v_true = utilidades(esc, esc.equilibrio.auto_total)
    auto_es_mejor = bool(v_true[0] > v_true[1])
    ult = elige_auto[:, -20:]

    # --- Las medidas del hot stove, como lo describe el documento ---
    # (1) Abandono: en los últimos 20 días no tomó el auto ni una vez.
    abandono = float(np.mean(ult.sum(axis=1) == 0))
    # (2) Mala suerte temprana: la PRIMERA experiencia en auto (ε del primer
    # día que lo eligió) está en el decil peor vs el decil mejor. Si el hot
    # stove existe, los del decil peor usan menos el auto al final.
    primer_dia = np.argmax(a[:, 1:, 0], axis=1) + 1  # 0 si nunca (argmax de todo False)
    tomo_auto = a[:, 1:, 0].any(axis=1)
    primera = np.where(tomo_auto, x[np.arange(n), primer_dia, 0], np.nan)
    ok = ~np.isnan(primera)
    q10, q90 = np.nanpercentile(primera, [10, 90])
    share_mala = (
        float(ult[ok & (primera >= q90)].mean()) if (ok & (primera >= q90)).any() else float("nan")
    )
    share_buena = (
        float(ult[ok & (primera <= q10)].mean()) if (ok & (primera <= q10)).any() else float("nan")
    )
    # (3) Creencia final: cree que el auto es peor. Débil bajo indiferencia
    # (con ventaja real de 0,8 min, el puro ruido simétrico vuelca a la mitad),
    # se guarda como referencia.
    v_fin = np.array([utilidades(esc, round(float(ta), 2)) for ta in percibido_auto[:, -1]])
    cree_auto_peor = float(np.mean(v_fin[:, 0] < v_fin[:, 1]))

    # Trayectoria ilustrativa: la persona con la peor primera experiencia.
    k = int(np.nanargmax(primera))
    return {
        "sigma": sigma,
        "mu": mu,
        "d": d,
        "auto_es_mejor": auto_es_mejor,
        "p_auto_verdadera": prob_auto(v_true, mu),
        "share_auto_por_dia": elige_auto.mean(axis=0).tolist(),
        "share_auto_ultimos_20": float(ult.mean()),
        "abandono": abandono,
        "share_fin_mala_suerte": share_mala,
        "share_fin_buena_suerte": share_buena,
        "primera_experiencia_q10_q90": [float(q10), float(q90)],
        "cree_auto_peor": cree_auto_peor,
        "percibido_auto_medio_por_dia": percibido_auto.mean(axis=0).tolist(),
        "percibido_auto_p10_por_dia": np.percentile(percibido_auto, 10, axis=0).tolist(),
        "percibido_auto_p90_por_dia": np.percentile(percibido_auto, 90, axis=0).tolist(),
        "ejemplo": {
            "persona": k,
            "primera_experiencia": float(primera[k]),
            "percibido_auto": percibido_auto[k].tolist(),
            "elige_auto": elige_auto[k].tolist(),
            "experimentado_auto": x[k, 1:, 0].tolist(),
        },
    }


def main() -> None:
    esc = escenario()
    eq = esc.equilibrio
    t_metro = eq.tren_acceso + eq.tren_espera + eq.tren_viaje
    v_true = utilidades(esc, eq.auto_total)
    print(f"\n  FASE 0 · una persona ({ESTRATO}, celda {CELDA}, {DIAS} días, {REPLICAS} réplicas)")
    print(
        f"  tiempos de equilibrio: auto {eq.auto_total:.1f} min (flujo libre {esc.t_auto_libre:.1f}), metro {t_metro:.1f} min"
    )
    print(
        f"  utilidad verdadera: auto {v_true[0]:.3f}  metro {v_true[1]:.3f}  → P(auto | μ=1) = {prob_auto(v_true, 1.0):.3f}\n"
    )
    print(
        f"  {'σ':>5}{'μ':>6}{'d':>5}{'P(auto) verdad':>16}{'share fin':>11}{'abandono':>10}"
        f"{'fin|mala':>10}{'fin|buena':>11}{'cree peor':>11}"
    )
    print("  " + "-" * 85)
    filas = []
    for sigma in SIGMAS:
        for mu in MUS:
            for d in DECAIMIENTOS:
                rng = np.random.default_rng(42)
                r = simular(esc, sigma, mu, d, rng)
                filas.append(r)
                print(
                    f"  {sigma:>5.0f}{mu:>6.1f}{d:>5.1f}{r['p_auto_verdadera']:>16.3f}"
                    f"{r['share_auto_ultimos_20']:>11.3f}{r['abandono']:>10.3f}"
                    f"{r['share_fin_mala_suerte']:>10.3f}{r['share_fin_buena_suerte']:>11.3f}"
                    f"{r['cree_auto_peor']:>11.3f}"
                )
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "persona.json").write_text(
        json.dumps(
            {
                "estrato": ESTRATO,
                "celda": CELDA,
                "dias": DIAS,
                "replicas": REPLICAS,
                "t_auto_eq": eq.auto_total,
                "t_auto_libre": esc.t_auto_libre,
                "t_metro_eq": t_metro,
                "v_true": v_true.tolist(),
                "filas": filas,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\n  Datos en {SALIDA / 'persona.json'}\n")


if __name__ == "__main__":
    main()
