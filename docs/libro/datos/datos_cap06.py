"""Datos del capítulo 6 — Accesibilidad y acoplamiento.

Produce `cap06.json`. El capítulo tiene que contestar tres preguntas: qué es
exactamente la accesibilidad que entra a la puja, qué la hace compatible con
Alonso, y si el loop exterior suelo↔transporte converge a algo — y cuándo.

La segunda es la que más se da por sabida. Desde D-22 (jun-2026) el repo repite
que la accesibilidad por estrato invertía el ordenamiento de Alonso y que el
logsum en pesos lo arregló. Acá se separan las dos cosas que cambiaron a la vez
—el objeto (minutos → logsum) y la moneda (`λ` uniforme → `λ_h = |b_costo_h|`)—
en un 2×2, porque el guard actual sólo verifica la conjunción.

Bloques:

1. `accesibilidad` — el perfil de `T` a red vacía, por estrato, en las dos
   unidades, con sus pendientes y sus quiebres.
2. `quien_remueve_la_inversion` — el 2×2 {minutos, logsum} × {λ uniforme,
   λ heterogéneo}, sin teletrabajo para aislar ese mecanismo.
3. `teletrabajo` — D11: `T` cobra los viajes esperados, 44·(1 − p_tele,h);
   cuánto mueve eso las pendientes y la ciudad.
4. `red_configurada` — D-42: cuánto mueve la red del metro la accesibilidad
   del suelo standalone, y cuánto mueve la ciudad.
5. `loop` — la trayectoria del acoplado de la aplicación, iteración a
   iteración, con la brecha en $/hogar-mes y el ΔCS mensual.
6. `paso`, `brecha_distribucion`, `parada`, `tolerancia` — D10: la regla del
   paso exterior contra la vieja, en la base y en dos casos de estrés; de
   dónde sale la brecha; el corte con un MSA que no converge.
7. `poblacion` — D-24: la población como palanca de demanda, y hasta dónde el
   loop sigue convergiendo.

Más `parametros_vigentes`: lo que el acoplado usa y de dónde lo toma, leído del
núcleo por introspección y de la app, la API y el worker desde su fuente.

Correr desde `packages/titirilquen_core` (~2 min):

    uv run python ../../docs/libro/datos/datos_cap06.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "packages" / "titirilquen_core" / "tests"))

import test_linea_base as base

from titirilquen_core.city import CiudadLineal
from titirilquen_core.constantes import TOL_ACOPLADO_CLP_MES, VUELTAS_ACOPLADO_MAX
from titirilquen_core.coupled import (
    _run_transport_with_population,
    _T_logsum_snapshot,
    iter_coupled,
)
from titirilquen_core.coupled_metrics import _theil
from titirilquen_core.demand.choice import probabilidades_logit
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.land_use.accesibilidad import (
    T_flujo_libre,
    lambda_desde_demanda,
    tiempos_red_vacia,
    viajes_mes_por_estrato,
)
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.population import generar_poblacion_desde_land_use_det

SALIDA = Path(__file__).parent / "cap06.json"
#: Referencias externas que cita el capítulo, en la forma en que se citan.
FUENTES_EXTERNAS = {
    "alonso_1964": (
        "Alonso, W. (1964). Location and Land Use: Toward a General Theory of "
        "Land Rent. Harvard University Press."
    ),
    "williams_1977": (
        "Williams, H. C. W. L. (1977). On the formation of travel demand models "
        "and economic evaluation measures of user benefit. Environment and "
        "Planning A, 9(3), 285–344."
    ),
    "small_rosen_1981": (
        "Small, K. A. y Rosen, H. S. (1981). Applied welfare economics with "
        "discrete choice models. Econometrica, 49(1), 105–130."
    ),
}
NOMBRES = ("alto", "medio", "bajo")
#: `λ_h = |b_costo_h|` del default de la app (D-34). Se leen del núcleo, no se
#: tipean: si `presets.py` cambia, este capítulo cambia con él.
KM_PERFIL = (0.5, 1.0, 2.0, 3.0, 5.0, 8.0)


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "desconocido"


def _ciudad() -> CiudadLineal:
    sim = base._config_web()
    return CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)


def _lambdas() -> list[float]:
    return [float(x) for x in lambda_desde_demanda(base._config_web().demand)]


def _celda(ciudad: CiudadLineal, km: float) -> int:
    return min(ciudad.cbd_index + round(km / ciudad.ancho_celda_km), ciudad.n_celdas - 1)


def _T_minutos_por_estrato() -> np.ndarray:
    """Reconstruye la accesibilidad que el acoplado usó hasta sep-2026: el
    **tiempo esperado** del viaje desde cada celda, por estrato.

    `_aggregate_T_expected` se borró al implementar D-34, así que se rehace acá
    con las mismas piezas del núcleo (`probabilidades_logit` sobre
    `calcular_utilidades`, esperanza sobre la tenencia de auto). Es el único
    cálculo de este capítulo que no llama a una función viva: existe para poder
    medir el contrafactual de D-22, no para volver a usarlo.
    """
    sim = base._config_web()
    ciudad = _ciudad()
    tiempos = tiempos_red_vacia(sim, ciudad)
    dem = sim.demand
    c, dx = ciudad.cbd_index, ciudad.ancho_celda_km

    def t_modo(i: int, m: str) -> float:
        o = tiempos[i]
        d = abs(i - c) * dx
        return {
            "Auto": o.auto_total,
            "Metro": o.tren_acceso + o.tren_espera + o.tren_viaje,
            "Bici": o.bici_total,
            "Caminata": d / dem.globales.v_caminata * 60.0,
        }[m]

    T = np.zeros((3, ciudad.n_celdas))
    for h, estrato in enumerate((1, 2, 3)):
        p_a = float(dem.estratos[estrato].prob_auto)  # type: ignore[index]
        for i in range(ciudad.n_celdas):
            num = den = 0.0
            for tiene_auto, w in ((True, p_a), (False, 1.0 - p_a)):
                if w <= 0:
                    continue
                u = calcular_utilidades(
                    estrato=estrato,  # type: ignore[arg-type]
                    celda_origen=i,
                    tiene_auto=tiene_auto,
                    ciudad=ciudad,
                    config=dem,
                    tiempos_observados=tiempos[i],
                )
                p = probabilidades_logit(u)
                if not p:
                    continue
                num += w * sum(pr * t_modo(i, m) for m, pr in p.items())
                den += w
            T[h, i] = num / den if den > 0 else np.nan
    return T


def _distancias_medias(T: np.ndarray, lambdas: list[float] | None = None) -> list[float]:
    """Resuelve la subasta con esa `T` y devuelve la distancia media al CBD por
    estrato, ponderada por hogares (`N_hi = S_i·Q_hi`)."""
    return _resolver(T, lambdas)[0]


def _resolver(T: np.ndarray, lambdas: list[float] | None = None) -> tuple[list[float], float]:
    """La subasta con esa `T`: distancias medias por estrato y Theil."""
    ciudad = _ciudad()
    cfg = base._land_use_web()
    # `lambdas` explícito = contrafactual: λ movido sin tocar la demanda ni T.
    lam = _lambdas() if lambdas is None else lambdas
    city = LandUseCity.build(
        L=ciudad.n_celdas,
        CBD=ciudad.cbd_index,
        cfg=cfg,
        T=T,
        lambda_h=np.asarray(lam, dtype=float),
        rng=np.random.default_rng(42),
        ancho_celda_km=ciudad.ancho_celda_km,
    )
    assert city.result is not None
    N = city.result.Q * np.asarray(city.S, dtype=float)[None, :]
    dist = np.abs(np.arange(ciudad.n_celdas) - ciudad.cbd_index) * ciudad.ancho_celda_km
    d = [round(float((N[h] * dist).sum() / N[h].sum()), 4) for h in range(3)]
    return d, round(float(_theil(city.result.Q, np.asarray(city.S, dtype=float))), 4)


# ---------------------------------------------------------------------------
# 1. La accesibilidad
# ---------------------------------------------------------------------------


def accesibilidad() -> dict:
    """`T_h(i) = −44·(1 − p_tele,h)·logsum_h(i)` sobre la red vacía configurada,
    por estrato.

    Se reporta en útiles de transporte por mes (lo que entra a `f_h`) y en
    $/mes (`T/λ_h`, lo que la puja pone sobre la mesa). El NIVEL no significa
    nada —el logsum arrastra las ASC, cero arbitrario— así que lo interpretable
    son las diferencias y la pendiente.
    """
    sim = base._config_web()
    ciudad = _ciudad()
    lam = _lambdas()
    T = T_flujo_libre(
        sim.demand,
        ciudad.n_celdas,
        ciudad.cbd_index,
        ciudad.ancho_celda_km,
        supply=sim.supply,
    )
    gl = sim.demand.globales
    perfil = []
    for km in KM_PERFIL:
        i = _celda(ciudad, km)
        perfil.append(
            {
                "km": km,
                "utiles_mes": [round(float(T[h, i]), 2) for h in range(3)],
                "clp_mes": [round(float(T[h, i] / lam[h])) for h in range(3)],
            }
        )
    # Pendiente por mínimos cuadrados sobre el semicorredor útil (1 a 9 km):
    # entre 0 y 1 km el perfil está dominado por la caminata y no es recta.
    i0, i1 = _celda(ciudad, 1.0), _celda(ciudad, 9.0)
    d = np.arange(i0, i1 + 1) * ciudad.ancho_celda_km - ciudad.cbd_index * ciudad.ancho_celda_km
    pend_ut = [float(np.polyfit(d, T[h, i0 : i1 + 1], 1)[0]) for h in range(3)]
    return {
        "unidad": (
            "T = −VIAJES_MES·(1 − p_tele,h)·logsum; útiles de transporte por mes, "
            "y $/mes al dividir por λ_h"
        ),
        "viajes_mes_por_estrato": [round(float(v), 2) for v in viajes_mes_por_estrato(sim.demand)],
        "lambda_h": [round(x, 9) for x in lam],
        "uno_sobre_lambda_clp": [round(1.0 / x) for x in lam],
        "perfil": perfil,
        "pendiente_1_a_9km": {
            "utiles_mes_por_km": [round(x, 4) for x in pend_ut],
            "clp_mes_por_km": [round(pend_ut[h] / lam[h]) for h in range(3)],
        },
        "rango_utiles_mes": [round(float(T[h].max() - T[h].min()), 2) for h in range(3)],
        "cortes_modales_km": {
            "caminata": round(gl.corte_caminata_min * gl.v_caminata / 60.0, 3),
            "bici": round(gl.corte_bici_min * gl.v_bici / 60.0, 3),
        },
        "monotona_celda_a_celda": [
            bool(np.all(np.diff(T[h, ciudad.cbd_index :]) > 0)) for h in range(3)
        ],
        "nota": (
            "`T` NO es monótona celda a celda: cerca de cada estación el acceso al "
            "metro baja y la accesibilidad mejora. Es la red configurada, no una "
            "función de la distancia (D-42)."
        ),
    }


# ---------------------------------------------------------------------------
# 2. Qué remueve la inversión de Alonso
# ---------------------------------------------------------------------------


def quien_remueve_la_inversion() -> dict:
    """El 2×2. D-22 atribuyó la inversión a la accesibilidad POR ESTRATO y
    D-34 su desaparición al logsum; entre medio también cambió `λ`.

    Para que la comparación sea del objeto y no de su escala, la `T` en minutos
    se reescala por el factor que iguala su rango al del logsum en el estrato
    medio: así el balance accesibilidad/densidad (`α·T` contra `ρ·dens`, que es
    para lo que se calibró `ρ`) es el mismo en las cuatro celdas del cuadro.

    Sin teletrabajo (`teletrabajo_factor = 0`): el tiempo en minutos no lo
    descuenta, y desde D11 el logsum sí, así que con teletrabajo la fila del
    logsum mezclaría dos mecanismos. Con factor 0, `T` es la de antes de D11.
    """
    sim = base._config_web()
    sim = sim.model_copy(
        update={
            "demand": sim.demand.model_copy(
                update={
                    "globales": sim.demand.globales.model_copy(update={"teletrabajo_factor": 0.0})
                }
            )
        }
    )
    ciudad = _ciudad()
    T_ls = T_flujo_libre(
        sim.demand,
        ciudad.n_celdas,
        ciudad.cbd_index,
        ciudad.ancho_celda_km,
        supply=sim.supply,
    )
    T_min = _T_minutos_por_estrato()
    k = float((T_ls[1].max() - T_ls[1].min()) / (T_min[1].max() - T_min[1].min()))
    T_min_esc = T_min * k

    het = _lambdas()
    uni = [het[1]] * 3
    casos = []
    for objeto, Tm in (("logsum (D-34)", T_ls), ("minutos (D-22)", T_min_esc)):
        for moneda, lam in (("λ heterogéneo", het), ("λ uniforme", uni)):
            d = _distancias_medias(Tm, lam)
            casos.append(
                {
                    "objeto": objeto,
                    "moneda": moneda,
                    "dist_media_km": d,
                    "invierte_alonso": bool(d[0] > d[2]),
                }
            )
    # La pendiente en minutos por km, que es lo que el bid-rent leía antes.
    i0, i1 = _celda(ciudad, 1.0), _celda(ciudad, 9.0)
    d_km = (np.arange(i0, i1 + 1) - ciudad.cbd_index) * ciudad.ancho_celda_km
    pend_min = [round(float(np.polyfit(d_km, T_min[h, i0 : i1 + 1], 1)[0]), 4) for h in range(3)]
    # El criterio de ordenamiento de Alonso, explícito. Con `α` común el
    # gradiente de la puja en $/km es (1/λ_h)·∂T_h/∂x, así que el estrato alto
    # ocupa el centro si y sólo si λ_bajo/λ_alto > (∂T_bajo/∂x)/(∂T_alto/∂x):
    # la ventaja de MONEDA tiene que superar a la de TIEMPO.
    pend_ls = [float(np.polyfit(d_km, T_ls[h, i0 : i1 + 1], 1)[0]) for h in range(3)]
    criterio_alonso = {}
    for nombre, pend in (("logsum", pend_ls), ("minutos", pend_min)):
        razon_pend = pend[2] / pend[0]
        criterio_alonso[nombre] = {
            "razon_pendientes_bajo_sobre_alto": round(razon_pend, 4),
            "razon_lambda_bajo_sobre_alto": round(het[2] / het[0], 4),
            "margen_con_lambda_heterogeneo": round((het[2] / het[0]) / razon_pend, 4),
            "margen_con_lambda_uniforme": round(1.0 / razon_pend, 4),
        }
    return {
        "factor_escala_minutos": round(k, 4),
        "pendiente_minutos_por_km": pend_min,
        "criterio_de_alonso": criterio_alonso,
        "casos": casos,
        "veredicto": (
            "La fila (minutos vs logsum) no decide nada; la columna (λ uniforme vs "
            "heterogéneo) decide todo. Lo que remueve la inversión es la MONEDA, "
            "no el objeto: con `λ_h = |b_costo_h|` el estrato alto puja más "
            "empinado en $/km aunque su tiempo crezca más lento en min/km."
        ),
    }


# ---------------------------------------------------------------------------
# 3. El teletrabajo en la accesibilidad (D11)
# ---------------------------------------------------------------------------


#: Tasas de teletrabajo sólo para ilustrar D11: las heredadas, sin fuente.
TELETRABAJO_ILUSTRATIVO = (0.40, 0.20, 0.05)


def teletrabajo() -> dict:
    """`T_h` cobra `VIAJES_MES·(1 − p_tele,h)` viajes: quien teletrabaja no
    valora estar cerca del CBD. Desde oct-2026 la app parte SIN teletrabajo, así
    que acá se fijan tasas ILUSTRATIVAS, sin fuente —las heredadas 0,40 / 0,20 /
    0,05—: con ellas la pendiente en pesos del alto cae más que la del medio.
    Factor 0 = la base de la app (44 viajes a todos); 2 = una política."""
    sim = base._config_web()
    sim.demand = sim.demand.model_copy(deep=True)
    for e, p in zip((1, 2, 3), TELETRABAJO_ILUSTRATIVO, strict=True):
        sim.demand.estratos[e].prob_teletrabajo = p  # type: ignore[index]
    ciudad = _ciudad()
    lam = _lambdas()
    i0, i1 = _celda(ciudad, 1.0), _celda(ciudad, 9.0)
    d_km = (np.arange(i0, i1 + 1) - ciudad.cbd_index) * ciudad.ancho_celda_km
    filas = []
    for factor in (0.0, 0.5, 1.0, 2.0):
        dem = sim.demand.model_copy(
            update={
                "globales": sim.demand.globales.model_copy(update={"teletrabajo_factor": factor})
            }
        )
        T = T_flujo_libre(
            dem, ciudad.n_celdas, ciudad.cbd_index, ciudad.ancho_celda_km, supply=sim.supply
        )
        pend = [float(np.polyfit(d_km, T[h, i0 : i1 + 1], 1)[0]) for h in range(3)]
        dist, theil = _resolver(T)
        filas.append(
            {
                "teletrabajo_factor": factor,
                "viajes_mes": [round(float(v), 2) for v in viajes_mes_por_estrato(dem)],
                "pendiente_clp_mes_por_km": [round(pend[h] / lam[h]) for h in range(3)],
                "dist_media_km": dist,
                "theil": theil,
            }
        )
    return {
        "prob_teletrabajo_ilustrativo": list(TELETRABAJO_ILUSTRATIVO),
        "filas": filas,
    }


# ---------------------------------------------------------------------------
# 4. La red configurada (D-42)
# ---------------------------------------------------------------------------


def red_configurada() -> dict:
    """¿Cuánto mueve la oferta de metro la accesibilidad del suelo standalone?

    Hasta D-42 la respuesta era cero: `T_flujo_libre` usaba velocidades de la
    demanda y 10 min de acceso fijos. Ahora usa la red vacía configurada.
    """
    sim = base._config_web()
    ciudad = _ciudad()
    ref = None
    filas = []
    for n_est in (4, 6, 10, 20, 30):
        train = sim.supply.train.model_copy(update={"num_estaciones": n_est})
        T = T_flujo_libre(
            sim.demand,
            ciudad.n_celdas,
            ciudad.cbd_index,
            ciudad.ancho_celda_km,
            supply=sim.supply.model_copy(update={"train": train}),
        )
        if ref is None:
            ref = T
        filas.append(
            {
                "num_estaciones": n_est,
                "max_dT_vs_4_estaciones": round(float(np.max(np.abs(T - ref))), 3),
                "dist_media_km": _distancias_medias(T),
            }
        )
    return {
        "default_app": 10,
        "filas": filas,
        "nota": (
            "La accesibilidad se mueve fuerte y localmente (decenas de útiles/mes "
            "junto a las estaciones), pero la ASIGNACIÓN casi no: la localización "
            "la fija la pendiente del corredor, no dónde para el tren."
        ),
    }


# ---------------------------------------------------------------------------
# 4 y 5. El loop exterior
# ---------------------------------------------------------------------------


def _trayectoria(
    sim,
    land_use,
    outer_max_iter: int = VUELTAS_ACOPLADO_MAX,
    outer_tol: float = TOL_ACOPLADO_CLP_MES,
) -> list[dict]:
    filas = []
    Q_prev = None
    for it in iter_coupled(
        sim=sim,
        land_use_config=land_use,
        outer_max_iter=outer_max_iter,
        outer_tol=outer_tol,
    ):
        Q = np.asarray(it.land_use.Q, dtype=float)
        m = it.metrics
        s = m.sistema
        filas.append(
            {
                "k": it.outer_iter,
                # La brecha del mapa en $/hogar-mes (D10): lo que compara el
                # criterio. `inf` en la vuelta 0, que no tiene contra qué medirse.
                "brecha_clp_mes": None
                if not np.isfinite(it.T_residual)
                else round(it.T_residual, 3),
                "max_dQ": None if Q_prev is None else float(f"{np.max(np.abs(Q - Q_prev)):.3e}"),
                "theil": round(float(s.segregacion_theil), 5),
                "dist_media_km": [round(float(e.dist_media_cbd_km), 4) for e in m.por_estrato],
                "reparto_pct": {c: round(100.0 * v, 3) for c, v in s.reparto_modal.items()},
                "tiempo_medio_min": round(float(s.tiempo_medio_min), 4),
                "frecuencia_metro_tph": round(float(s.frecuencia_metro), 4),
                "delta_excedente_hogar_mes_clp": [
                    round(float(e.delta_excedente_hogar_mes_clp)) for e in m.por_estrato
                ],
                "delta_bienestar_total_mes_clp": round(float(s.delta_bienestar_total_mes_clp)),
                "msa_convergio": bool(it.transport.converged),
                "msa_iteraciones": len(it.transport.iteraciones),
                "subasta_convergio": bool(it.land_use.converged),
                "convergio_nucleo": bool(s.convergio_exterior),
            }
        )
        Q_prev = Q.copy()
    return filas


def loop() -> dict:
    """La corrida acoplada de la aplicación: 20 km, 36.000 hogares, el tope de
    vueltas y la tolerancia del núcleo."""
    filas = _trayectoria(base._config_web(), base._land_use_web())
    ultima = filas[-1]
    primera = filas[0]
    return {
        "outer_max_iter": VUELTAS_ACOPLADO_MAX,
        "outer_tol": TOL_ACOPLADO_CLP_MES,
        "iteraciones_corridas": len(filas),
        "convergio": ultima["convergio_nucleo"],
        "trayectoria": filas,
        "sin_feedback_vs_con_feedback": {
            "nota": (
                "La iteración 0 es la ciudad resuelta con la accesibilidad de la red "
                "VACÍA: el baseline honesto de D-23, en la misma escala que el resto."
            ),
            "theil": [primera["theil"], ultima["theil"]],
            "dist_media_km": [primera["dist_media_km"], ultima["dist_media_km"]],
            "reparto_pct": [primera["reparto_pct"], ultima["reparto_pct"]],
            "tiempo_medio_min": [primera["tiempo_medio_min"], ultima["tiempo_medio_min"]],
            "frecuencia_metro_tph": [
                primera["frecuencia_metro_tph"],
                ultima["frecuencia_metro_tph"],
            ],
        },
    }


def _loop_msa(sim, land_use, n_outer: int) -> list[dict]:
    """El loop exterior con la regla que tuvo hasta oct-2026: promedio MSA de
    paso 1/(k+1), sin corte. Es una réplica de `iter_coupled` —el núcleo ya no
    la tiene— y existe sólo para medir contra qué se cambió (D10). Mide lo
    mismo que el núcleo: la brecha |F(T) − T|/λ_h en $/hogar-mes."""
    sim_eq = sim.model_copy(update={"assignment": "expected"})
    rng = np.random.default_rng(sim.seed)
    L = sim.city.n_celdas
    cbd = L // 2
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)
    lam = lambda_desde_demanda(sim.demand)
    T0 = T_flujo_libre(
        sim.demand, L, cbd, ciudad.ancho_celda_km, sim.modos_habilitados, supply=sim.supply
    )
    city = LandUseCity.build(
        L=L,
        CBD=cbd,
        cfg=land_use,
        T=T0,
        lambda_h=lam,
        rng=rng,
        ancho_celda_km=ciudad.ancho_celda_km,
    )
    T_state = None
    filas = []
    for k in range(n_outer):
        assert city.result is not None
        agentes = generar_poblacion_desde_land_use_det(
            Q=city.result.Q,
            S=city.S,
            cbd_index=cbd,
            demand_config=sim.demand,
            teletrabajo_factor=sim.demand.globales.teletrabajo_factor,
        )
        _, snap = _run_transport_with_population(sim_eq, agentes, ciudad)
        T_new = _T_logsum_snapshot(sim_eq, ciudad, snap)
        brecha = None if T_state is None else float(np.max(np.abs(T_new - T_state) / lam[:, None]))
        filas.append({"k": k, "brecha_clp_mes": None if brecha is None else round(brecha, 3)})
        T_state = T_new if T_state is None else T_new / (k + 1) + T_state * k / (k + 1)
        city.update(T=T_state, rng=rng)
    return filas


def paso() -> dict:
    """D10: la regla vieja (MSA 1/(k+1)) contra la del núcleo (paso 1, a la
    mitad si la brecha crece), sin corte (`outer_tol = 0`), en la base y en dos
    casos de estrés: ρ = 54 —el del tutorial `alonso_invertido`, ciudad con
    mucha retroalimentación por densidad— y la población ×2,5."""
    sim = base._config_web()
    lu0 = base._land_use_web()
    casos = {
        "base": lu0,
        "rho_54": lu0.model_copy(
            update={"estratos": [e.model_copy(update={"rho": 54.0}) for e in lu0.estratos]}
        ),
        "poblacion_x2_5": lu0.model_copy(
            update={"H_por_estrato": [round(h * 2.5) for h in lu0.H_por_estrato]}
        ),
    }
    n = 8
    out = {}
    for nombre, lu in casos.items():
        nucleo = _trayectoria(sim, lu, outer_max_iter=n, outer_tol=0.0)
        msa = _loop_msa(sim, lu, n)
        out[nombre] = {
            "msa_1_sobre_k": [f["brecha_clp_mes"] for f in msa],
            "nucleo": [f["brecha_clp_mes"] for f in nucleo],
            "msa_interior_convergio": [f["msa_convergio"] for f in nucleo],
            "k_bajo_tol_nucleo": next(
                (
                    f["k"]
                    for f in nucleo
                    if f["brecha_clp_mes"] is not None
                    and f["brecha_clp_mes"] < TOL_ACOPLADO_CLP_MES
                ),
                None,
            ),
            "k_bajo_tol_msa": next(
                (
                    f["k"]
                    for f in msa
                    if f["brecha_clp_mes"] is not None
                    and f["brecha_clp_mes"] < TOL_ACOPLADO_CLP_MES
                ),
                None,
            ),
        }
    return {"n_vueltas": n, "casos": out}


def brecha_distribucion() -> dict:
    """La brecha es una norma del SUPREMO sobre 3×201 celdas: ¿la pone la
    ciudad o una celda? Primera medición de la corrida base. Con paso 1 en la
    vuelta 1, `T_matrix` de la vuelta 1 es F(T⁰) sin promediar, así que la
    brecha por celda es |T₁ − T₀|/λ_h."""
    lam = np.asarray(_lambdas())
    ciudad = _ciudad()
    Ts = [
        np.asarray(it.T_matrix, dtype=float)
        for it in iter_coupled(
            sim=base._config_web(),
            land_use_config=base._land_use_web(),
            outer_max_iter=2,
            outer_tol=0.0,
        )
    ]
    D = np.abs(Ts[1] - Ts[0]) / lam[:, None]
    h, i = (int(x) for x in np.unravel_index(int(np.argmax(D)), D.shape))
    return {
        "max": round(float(D.max()), 1),
        "percentil_50": round(float(np.percentile(D, 50)), 1),
        "percentil_90": round(float(np.percentile(D, 90)), 1),
        "percentil_99": round(float(np.percentile(D, 99)), 1),
        "celdas_sobre_la_tolerancia": int((D > TOL_ACOPLADO_CLP_MES).sum()),
        "celdas_totales": int(D.size),
        "celda_del_maximo": {
            "estrato": h + 1,
            "indice": i,
            "km_del_cbd": round(abs(i - ciudad.cbd_index) * ciudad.ancho_celda_km, 4),
        },
    }


def parada() -> dict:
    """El criterio compuesto con un MSA interior que no puede converger
    (`max_iter = 2`): la brecha exterior cumple igual —el transporte casi no se
    mueve—, el loop para y el veredicto es «no convergió» (D-39). Antes de D10
    seguía girando hasta el tope con la misma ciudad."""
    sim_corto = base._config_web().model_copy(update={"max_iter": 2})
    filas = _trayectoria(sim_corto, base._land_use_web(), outer_max_iter=6)
    return {
        "max_iter_interior": 2,
        "outer_max_iter": 6,
        "filas": [
            {
                "k": f["k"],
                "brecha_clp_mes": f["brecha_clp_mes"],
                "msa_convergio": f["msa_convergio"],
                "nucleo_dice": f["convergio_nucleo"],
            }
            for f in filas
        ],
    }


def tolerancia() -> dict:
    """La tolerancia en contexto: cuánto era 1 útil/mes —la de antes— en
    pesos por estrato, y la brecha de la base sin corte."""
    lam = _lambdas()
    filas = _trayectoria(base._config_web(), base._land_use_web(), outer_max_iter=6, outer_tol=0.0)
    brechas = [f["brecha_clp_mes"] for f in filas if f["brecha_clp_mes"] is not None]
    return {
        "outer_tol_clp_mes": TOL_ACOPLADO_CLP_MES,
        "un_util_mes_en_clp": [round(1.0 / x) for x in lam],
        "brechas_sin_corte": brechas,
    }


# ---------------------------------------------------------------------------
# 6. La población como palanca (D-24)
# ---------------------------------------------------------------------------


def poblacion() -> list[dict]:
    """D-24: la escala de demanda del acoplado es ΣH, y pasado cierto punto el
    corredor monocéntrico se congestiona sin techo."""
    filas = []
    base_lu = base._land_use_web()
    shares = np.array(base_lu.H_por_estrato, dtype=float)
    shares = shares / shares.sum()
    for total in (12_000, 24_000, 36_000, 60_000, 90_000):
        H = tuple(round(total * s) for s in shares)
        lu = base_lu.model_copy(update={"H_por_estrato": H})
        tray = _trayectoria(base._config_web(), lu, outer_max_iter=10)
        u = tray[-1]
        filas.append(
            {
                "poblacion": total,
                "iteraciones": len(tray),
                "convergio": u["convergio_nucleo"],
                "msa_convergio": u["msa_convergio"],
                "brecha_final_clp_mes": u["brecha_clp_mes"],
                "delta_bienestar_total_mes_clp": u["delta_bienestar_total_mes_clp"],
                "theil": u["theil"],
                "tiempo_medio_min": u["tiempo_medio_min"],
                "dist_media_km": u["dist_media_km"],
                "reparto_pct": u["reparto_pct"],
            }
        )
    return filas


def parametros_vigentes() -> dict:
    """Los parámetros del acoplado y de dónde los toma cada consumidor.

    El módulo no introduce parámetros de modelo: `VIAJES_MES`, `p_tele`,
    `alpha`, `rho` y `lambda_h` son de suelo y transporte. Los suyos son de
    método —el paso, la tolerancia exterior y el tope de vueltas—. La
    tolerancia es una constante del núcleo que nadie pisa (D10), y el tope
    también (`VUELTAS_ACOPLADO_MAX`, D-61). Se leen de su fuente, no se
    tipean.
    """
    import inspect
    import re

    from titirilquen_core.constantes import VIAJES_MES

    firma = inspect.signature(iter_coupled).parameters
    lu = base._land_use_web()

    def _lee(rel: str, patron: str) -> str:
        txt = (RAIZ / rel).read_text(encoding="utf-8")
        m = re.search(patron, txt)
        assert m, f"{rel}: no se encontró {patron!r}"
        return m.group(1)

    api = "apps/api/src/api/main.py"
    worker = "apps/web/src/workers/pyodide.worker.ts"
    return {
        "viajes_mes": int(VIAJES_MES),
        "prob_teletrabajo": [
            float(base._config_web().demand.estratos[e].prob_teletrabajo)  # type: ignore[index]
            for e in (1, 2, 3)
        ],
        "viajes_mes_por_estrato": [
            round(float(v), 2) for v in viajes_mes_por_estrato(base._config_web().demand)
        ],
        "rho": [float(e.rho) for e in lu.estratos],
        "lambda_h": _lambdas(),
        "paso": "1; a la mitad cada vez que la brecha crece",
        "assignment_forzado": "expected",
        "tolerancia_interior_min": float(base._config_web().tolerance),
        "outer_tol": {
            "nucleo": float(firma["outer_tol"].default),
            "constante": float(TOL_ACOPLADO_CLP_MES),
            # La API y el worker toman la constante por nombre; la app y el
            # comparador no mandan el campo. Se verifica que así sea.
            "api_usa_la_constante": bool(
                _lee(api, r"outer_tol: float = Field\(\s*default=(TOL_ACOPLADO_CLP_MES)")
            ),
            "worker_usa_la_constante": bool(_lee(worker, r'"outer_tol",\s*(TOL_ACOPLADO_CLP_MES)')),
            "app_lo_manda": "outer_tol"
            in (RAIZ / "apps/web/src/pages/CoupledPage.tsx").read_text(encoding="utf-8"),
            "comparador_lo_manda": "outer_tol"
            in (RAIZ / "apps/web/src/pages/ComparePage.tsx").read_text(encoding="utf-8"),
        },
        "veredicto_motor_local_es_el_del_nucleo": "metrics.sistema.convergio_exterior"
        in (RAIZ / "apps/web/src/lib/api.ts").read_text(encoding="utf-8"),
        # D-61: un solo tope, `VUELTAS_ACOPLADO_MAX`, como default y cota. Se
        # verifica que cada consumidor lo tome por nombre en vez de transcribirlo.
        "outer_max_iter": {
            "constante": int(VUELTAS_ACOPLADO_MAX),
            "nucleo": int(firma["outer_max_iter"].default),
            "api_usa_la_constante": bool(
                _lee(
                    api,
                    r"outer_max_iter: int = Field\(\s*"
                    r"default=(VUELTAS_ACOPLADO_MAX), ge=1, le=VUELTAS_ACOPLADO_MAX",
                )
            ),
            "worker_usa_la_constante": bool(
                _lee(worker, r'"outer_max_iter",\s*(VUELTAS_ACOPLADO_MAX)')
            ),
            "app_usa_la_constante": bool(
                _lee(
                    "apps/web/src/store/landUseStore.ts",
                    r"coupledOuterMaxIter:\s*(VUELTAS_ACOPLADO_MAX),",
                )
            ),
            "comparador_usa_la_constante": bool(
                _lee(
                    "apps/web/src/pages/ComparePage.tsx",
                    r"outer_max_iter:\s*(VUELTAS_ACOPLADO_MAX),",
                )
            ),
        },
    }


def main() -> None:
    datos_loop = loop()
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap06.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web` y "
                "`_land_use_web`): 201 celdas, 20 km, 36.000 hogares 20/50/30, "
                "semilla 42, asignación esperada, brecha interior < 0,2 min. El "
                f"acoplado con `outer_max_iter = {VUELTAS_ACOPLADO_MAX}` y la "
                "tolerancia del núcleo, 100 $/hogar-mes."
            ),
        },
        "fuentes_externas": FUENTES_EXTERNAS,
        "parametros_vigentes": parametros_vigentes(),
        "accesibilidad": accesibilidad(),
        "quien_remueve_la_inversion": quien_remueve_la_inversion(),
        "teletrabajo": teletrabajo(),
        "red_configurada": red_configurada(),
        "loop": datos_loop,
        "paso": paso(),
        "brecha_distribucion": brecha_distribucion(),
        "parada": parada(),
        "tolerancia": tolerancia(),
        "poblacion": poblacion(),
    }
    SALIDA.write_text(json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    a = datos["accesibilidad"]
    print("Pendiente de la accesibilidad (1–9 km):")
    for h, n in enumerate(NOMBRES):
        print(
            f"  {n:<6} {a['pendiente_1_a_9km']['utiles_mes_por_km'][h]:8.3f} ut/mes/km  "
            f"= {a['pendiente_1_a_9km']['clp_mes_por_km'][h]:>8,} $/mes/km"
        )
    print("\n2×2 — qué remueve la inversión de Alonso (sin teletrabajo):")
    for c in datos["quien_remueve_la_inversion"]["casos"]:
        d = c["dist_media_km"]
        print(
            f"  {c['objeto']:<16} × {c['moneda']:<16} "
            f"alto {d[0]:6.3f}  medio {d[1]:6.3f}  bajo {d[2]:6.3f}   "
            f"{'INVERTIDA' if c['invierte_alonso'] else 'Alonso ok'}"
        )
    print("\nTeletrabajo:")
    for f in datos["teletrabajo"]["filas"]:
        print(
            f"  factor {f['teletrabajo_factor']:.1f}  viajes {f['viajes_mes']}  "
            f"pend $/km {f['pendiente_clp_mes_por_km']}  d {f['dist_media_km']}  "
            f"theil {f['theil']}"
        )
    print("\nLoop de la aplicación:")
    for f in datos_loop["trayectoria"]:
        print(
            f"  k={f['k']}  brecha={f['brecha_clp_mes']}  dQ={f['max_dQ']}  "
            f"conv={f['convergio_nucleo']}  ΔCS/hogar-mes={f['delta_excedente_hogar_mes_clp']}"
        )
    print("\nPaso (sin corte):")
    for nombre, c in datos["paso"]["casos"].items():
        print(f"  {nombre}: msa {c['msa_1_sobre_k']}")
        print(f"  {' ' * len(nombre)}  núcleo {c['nucleo']}")
    print("\nBrecha por celda:", datos["brecha_distribucion"])
    print("\nParada con MSA interior corto:")
    for f in datos["parada"]["filas"]:
        print(f"  {f}")
    print("\nTolerancia:", datos["tolerancia"])
    print("\nPoblación:")
    for f in datos["poblacion"]:
        print(
            f"  {f['poblacion']:>6}  iter={f['iteraciones']:>2}  conv={f['convergio']}  "
            f"msa={f['msa_convergio']}  t={f['tiempo_medio_min']:6.2f} min  "
            f"theil={f['theil']:.4f}  auto={f['reparto_pct']['Auto']:.2f}"
        )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
