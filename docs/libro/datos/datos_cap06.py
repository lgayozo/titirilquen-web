"""Datos del capítulo 6 — Accesibilidad y acoplamiento.

Produce `cap06.json`. El capítulo tiene que contestar tres preguntas: qué es
exactamente la accesibilidad que entra a la puja, qué la hace compatible con
Alonso, y si el loop exterior suelo↔transporte converge a algo — y cuándo.

La segunda es la que más se da por sabida. Desde D-22 (jun-2026) el repo repite
que la accesibilidad por estrato invertía el ordenamiento de Alonso y que el
logsum en pesos lo arregló. Acá se separan las dos cosas que cambiaron a la vez
—el objeto (minutos → logsum) y la moneda (`λ` uniforme → `λ_h = |b_costo_h|`)—
en un 2×2, porque el guard actual sólo verifica la conjunción.

Seis bloques:

1. `accesibilidad` — el perfil de `T` a red vacía, por estrato, en las dos
   unidades, con sus pendientes y sus quiebres.
2. `quien_remueve_la_inversion` — el 2×2 {minutos, logsum} × {λ uniforme,
   λ heterogéneo}.
3. `red_configurada` — D-42: cuánto mueve la red del metro la accesibilidad
   del suelo standalone, y cuánto mueve la ciudad.
4. `loop` — la trayectoria del acoplado de la aplicación, iteración a
   iteración.
5. `criterio` — qué mide el residual exterior contra qué se mueve de verdad,
   qué compran las iteraciones extra y dónde el frontend afloja el criterio.
6. `poblacion` — D-24: la población como palanca de demanda, y hasta dónde el
   loop sigue convergiendo.

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
from titirilquen_core.coupled import iter_coupled
from titirilquen_core.demand.choice import probabilidades_logit
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.land_use.accesibilidad import T_flujo_libre, tiempos_red_vacia
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.presets import DEFAULT_STRATA

SALIDA = Path(__file__).parent / "cap06.json"
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
    return CiudadLineal(
        n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km
    )


def _lambdas() -> list[float]:
    dem = base._config_web().demand
    return [abs(float(dem.estratos[h].betas.b_costo)) for h in (1, 2, 3)]  # type: ignore[index]


def _celda(ciudad: CiudadLineal, km: float) -> int:
    return min(
        ciudad.cbd_index + round(km / ciudad.ancho_celda_km), ciudad.n_celdas - 1
    )


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


def _distancias_medias(
    T: np.ndarray, lambdas: list[float] | None = None
) -> list[float]:
    """Resuelve la subasta con esa `T` y devuelve la distancia media al CBD por
    estrato, ponderada por hogares (`N_hi = S_i·Q_hi`)."""
    ciudad = _ciudad()
    cfg = base._land_use_web()
    if lambdas is not None:
        estratos = tuple(
            e.model_copy(update={"lambda_": lam})
            for e, lam in zip(cfg.estratos, lambdas)
        )
        cfg = cfg.model_copy(update={"estratos": estratos})
    city = LandUseCity.build(
        L=ciudad.n_celdas,
        CBD=ciudad.cbd_index,
        cfg=cfg,
        T=T,
        rng=np.random.default_rng(42),
        ancho_celda_km=ciudad.ancho_celda_km,
    )
    assert city.result is not None
    N = city.result.Q * np.asarray(city.S, dtype=float)[None, :]
    dist = np.abs(np.arange(ciudad.n_celdas) - ciudad.cbd_index) * ciudad.ancho_celda_km
    return [round(float((N[h] * dist).sum() / N[h].sum()), 4) for h in range(3)]


# ---------------------------------------------------------------------------
# 1. La accesibilidad
# ---------------------------------------------------------------------------


def accesibilidad() -> dict:
    """`T_h(i) = −44·logsum_h(i)` sobre la red vacía configurada, por estrato.

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
    d = (
        np.arange(i0, i1 + 1) * ciudad.ancho_celda_km
        - ciudad.cbd_index * ciudad.ancho_celda_km
    )
    pend_ut = [float(np.polyfit(d, T[h, i0 : i1 + 1], 1)[0]) for h in range(3)]
    return {
        "unidad": "T = −VIAJES_MES·logsum; útiles de transporte por mes, y $/mes al dividir por λ_h",
        "lambda_h": [round(x, 9) for x in lam],
        "uno_sobre_lambda_clp": [round(1.0 / x) for x in lam],
        "perfil": perfil,
        "pendiente_1_a_9km": {
            "utiles_mes_por_km": [round(x, 4) for x in pend_ut],
            "clp_mes_por_km": [round(pend_ut[h] / lam[h]) for h in range(3)],
        },
        "rango_utiles_mes": [
            round(float(T[h].max() - T[h].min()), 2) for h in range(3)
        ],
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
    """
    sim = base._config_web()
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
    pend_min = [
        round(float(np.polyfit(d_km, T_min[h, i0 : i1 + 1], 1)[0]), 4) for h in range(3)
    ]
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
# 3. La red configurada (D-42)
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
    sim, land_use, outer_max_iter: int = 12, outer_tol: float = 1.0
) -> list[dict]:
    filas = []
    Q_prev = None
    T_state_prev = None
    T_new_prev = None
    for it in iter_coupled(
        sim=sim,
        land_use_config=land_use,
        outer_max_iter=outer_max_iter,
        outer_tol=outer_tol,
    ):
        k = it.outer_iter
        Q = np.asarray(it.land_use.Q, dtype=float)
        T_state = np.asarray(it.T_matrix, dtype=float)
        # `T_matrix` es el estado AMORTIGUADO. El iterado crudo se recupera
        # invirtiendo el promedio: T_new = T_prev + (T_state − T_prev)/θ,
        # θ = 1/(k+1). Es la cantidad que D-39 llama brecha: lo que el mapa
        # devolvió, sin promediar.
        if k == 0:
            T_new = T_state
        else:
            theta = 1.0 / (k + 1)
            T_new = T_state_prev + (T_state - T_state_prev) / theta
        m = it.metrics
        s = m.sistema
        filas.append(
            {
                "k": k,
                "residual": None
                if not np.isfinite(it.T_residual)
                else round(it.T_residual, 5),
                "brecha_T_new": None
                if T_new_prev is None
                else round(float(np.max(np.abs(T_new - T_new_prev))), 6),
                "max_dQ": None
                if Q_prev is None
                else float(f"{np.max(np.abs(Q - Q_prev)):.3e}"),
                "theil": round(float(s.segregacion_theil), 5),
                "dist_media_km": [
                    round(float(e.dist_media_cbd_km), 4) for e in m.por_estrato
                ],
                "reparto_pct": {
                    c: round(100.0 * v, 3) for c, v in s.reparto_modal.items()
                },
                "tiempo_medio_min": round(float(s.tiempo_medio_min), 4),
                "frecuencia_metro_tph": round(float(s.frecuencia_metro), 4),
                "delta_bienestar_total_clp": round(float(s.delta_bienestar_total_clp)),
                "msa_convergio": bool(it.transport.converged),
                "subasta_convergio": bool(it.land_use.converged),
                "convergio_nucleo": bool(s.convergio_exterior),
            }
        )
        Q_prev, T_state_prev, T_new_prev = Q.copy(), T_state.copy(), T_new.copy()
    return filas


def loop() -> dict:
    """La corrida acoplada de la aplicación: 20 km, 36.000 hogares, 12 vueltas
    como máximo, tolerancia 1,0."""
    filas = _trayectoria(base._config_web(), base._land_use_web())
    ultima = filas[-1]
    primera = filas[0]
    return {
        "outer_max_iter": 12,
        "outer_tol": 1.0,
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
            "tiempo_medio_min": [
                primera["tiempo_medio_min"],
                ultima["tiempo_medio_min"],
            ],
            "frecuencia_metro_tph": [
                primera["frecuencia_metro_tph"],
                ultima["frecuencia_metro_tph"],
            ],
        },
    }


def anatomia_del_residual() -> dict:
    """¿De dónde sale el número que el loop compara contra `outer_tol`?

    El residual es una norma del SUPREMO sobre 3×201 celdas, y la utilidad de la
    bici tiene penalizaciones ESCALONADAS por tramos de duración (>10, >20, >30
    min). Cruzar un escalón cambia la utilidad de golpe, el logsum lo hereda y
    `VIAJES_MES` lo multiplica por 44. Así que conviene mirar la distribución
    del cambio, no sólo su máximo.
    """
    sim = base._config_web()
    ciudad = _ciudad()
    Ts, snaps = [], []
    for it in iter_coupled(
        sim=sim, land_use_config=base._land_use_web(), outer_max_iter=2, outer_tol=1.0
    ):
        Ts.append(np.asarray(it.T_matrix, dtype=float))
        snaps.append(it.transport.iteraciones[-1])
    T_new1 = Ts[0] + (Ts[1] - Ts[0]) / 0.5  # θ = 1/2 en k = 1
    D = np.abs(T_new1 - Ts[0])
    h, i = (int(x) for x in np.unravel_index(int(np.argmax(D)), D.shape))
    d_km = abs(i - ciudad.cbd_index) * ciudad.ancho_celda_km
    t_bici = [round(float(s.t_bici[i]), 4) for s in snaps]
    # El tamaño del escalón que se cruza, en minutos-equivalentes en vehículo:
    # (pen_bici_30) / |b_tiempo_viaje| del estrato del máximo.
    betas = DEFAULT_STRATA[h + 1]["betas"]
    escalon = abs(betas["penalizaciones_fisicas"]["bici_30"]) / abs(
        betas["b_tiempo_viaje"]
    )
    return {
        "max": round(float(D.max()), 4),
        "percentil_50": round(float(np.percentile(D, 50)), 4),
        "percentil_90": round(float(np.percentile(D, 90)), 4),
        "percentil_99": round(float(np.percentile(D, 99)), 4),
        "celdas_sobre_la_tolerancia": int((D > 1.0).sum()),
        "celdas_totales": int(D.size),
        "celda_del_maximo": {
            "estrato": h + 1,
            "indice": i,
            "km_del_cbd": round(d_km, 4),
            "t_bici_min": t_bici,
            "escalon_cruzado_min": 30.0,
            "escalon_min_equivalentes": round(float(escalon), 2),
            "escalon_utiles": round(float(escalon * abs(betas["b_tiempo_viaje"])), 4),
        },
        "nota": (
            "El máximo lo pone una celda donde el tiempo en bici cruza los 30 min "
            "entre una vuelta y la siguiente: 0,1 min de viaje activan el escalón "
            "`bici_30` de la utilidad. El resto de la ciudad se mueve dos órdenes "
            "de magnitud menos."
        ),
    }


def criterio(datos_loop: dict) -> dict:
    """Qué mide el residual exterior, y qué compran las iteraciones que exige.

    El residual es ‖F(T_state) − T_state‖∞ y eso está bien planteado: la ciudad
    que se reporta se construyó con `T_state`. Pero `T_state` es un promedio
    MSA, y su error decae como 1/k aunque el mapa ya no se mueva — de ahí que el
    residual siga bajando cuando `T_new` es idéntico entre vueltas.
    """
    filas = datos_loop["trayectoria"]
    res1 = filas[1]["residual"]
    armonica = [
        {
            "k": f["k"],
            "residual": f["residual"],
            "res1_sobre_k": round(res1 / f["k"], 5),
            "brecha_T_new": f["brecha_T_new"],
        }
        for f in filas
        if f["k"] >= 1
    ]
    k_conv = next((f["k"] for f in filas if f["convergio_nucleo"]), None)
    # La primera vuelta en que la ciudad ya no se mueve más que 1e-2 en Q.
    k_quieta = next(
        (f["k"] for f in filas if f["max_dQ"] is not None and f["max_dQ"] < 1e-2), None
    )
    f_conv = filas[k_conv] if k_conv is not None else filas[-1]
    f_quieta = filas[k_quieta] if k_quieta is not None else filas[-1]

    # El criterio del frontend: `api.ts::resolverAcoplado` reconstruye
    # `converged` como `T_residual < outer_tol` a secas. Con un MSA que no puede
    # converger (max_iter = 2) el núcleo dice que no y el frontend que sí.
    sim_corto = base._config_web().model_copy(update={"max_iter": 2})
    laxo = []
    for it in iter_coupled(
        sim=sim_corto,
        land_use_config=base._land_use_web(),
        outer_max_iter=6,
        outer_tol=1.0,
    ):
        r = it.T_residual
        laxo.append(
            {
                "k": it.outer_iter,
                "residual": None if not np.isfinite(r) else round(r, 5),
                "msa_convergio": bool(it.transport.converged),
                "nucleo_dice": bool(it.metrics.sistema.convergio_exterior),
                "api_ts_diria": bool(np.isfinite(r) and r < 1.0),
            }
        )
    return {
        "decaimiento_armonico": armonica,
        "iteracion_en_que_converge_el_criterio": k_conv,
        "iteracion_en_que_la_ciudad_deja_de_moverse": k_quieta,
        "lo_que_compran_las_vueltas_extra": {
            "desde_k": k_quieta,
            "hasta_k": k_conv,
            "delta_theil": round(f_conv["theil"] - f_quieta["theil"], 6),
            "delta_dist_media_km": [
                round(a - b, 5)
                for a, b in zip(f_conv["dist_media_km"], f_quieta["dist_media_km"])
            ],
            "delta_reparto_pp": {
                c: round(f_conv["reparto_pct"][c] - f_quieta["reparto_pct"][c], 4)
                for c in f_conv["reparto_pct"]
            },
        },
        "tolerancia_en_contexto": {
            "outer_tol": 1.0,
            "unidad_real": "útiles de transporte por mes (D-34)",
            "unidad_documentada_en": [
                "coupled.py:235 y :244 («minutos»)",
                "apps/web/src/lib/types-v2.ts:61 («en minutos»)",
                "i18n simulator.json `eqt.conv_sub` («residual {{res}} min»)",
            ],
        },
        "criterio_laxo_del_frontend": laxo,
        "anatomia_del_residual": anatomia_del_residual(),
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
        tray = _trayectoria(base._config_web(), lu, outer_max_iter=10, outer_tol=1.0)
        u = tray[-1]
        filas.append(
            {
                "poblacion": total,
                "iteraciones": len(tray),
                "convergio": u["convergio_nucleo"],
                "residual_final": u["residual"],
                "theil": u["theil"],
                "tiempo_medio_min": u["tiempo_medio_min"],
                "dist_media_km": u["dist_media_km"],
                "reparto_pct": u["reparto_pct"],
            }
        )
    return filas


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
                "semilla 42, asignación esperada, tolerancia interior 0,1. El "
                "acoplado con `outer_max_iter = 12` y `outer_tol = 1,0`, que es "
                "lo que manda `CoupledPage.tsx`."
            ),
        },
        "accesibilidad": accesibilidad(),
        "quien_remueve_la_inversion": quien_remueve_la_inversion(),
        "red_configurada": red_configurada(),
        "loop": datos_loop,
        "criterio": criterio(datos_loop),
        "poblacion": poblacion(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    a = datos["accesibilidad"]
    print("Pendiente de la accesibilidad (1–9 km):")
    for h, n in enumerate(NOMBRES):
        print(
            f"  {n:<6} {a['pendiente_1_a_9km']['utiles_mes_por_km'][h]:8.3f} ut/mes/km  "
            f"= {a['pendiente_1_a_9km']['clp_mes_por_km'][h]:>8,} $/mes/km"
        )
    print("\n2×2 — qué remueve la inversión de Alonso:")
    for c in datos["quien_remueve_la_inversion"]["casos"]:
        d = c["dist_media_km"]
        print(
            f"  {c['objeto']:<16} × {c['moneda']:<16} "
            f"alto {d[0]:6.3f}  medio {d[1]:6.3f}  bajo {d[2]:6.3f}   "
            f"{'INVERTIDA' if c['invierte_alonso'] else 'Alonso ok'}"
        )
    cr = datos["criterio"]
    print(
        f"\nLoop: converge en k={cr['iteracion_en_que_converge_el_criterio']}, "
        f"la ciudad deja de moverse en k={cr['iteracion_en_que_la_ciudad_deja_de_moverse']}"
    )
    print("  k  residual   res(1)/k   brecha T_new")
    for f in cr["decaimiento_armonico"]:
        print(
            f"  {f['k']:<2} {f['residual']:9.4f}  {f['res1_sobre_k']:9.4f}  "
            f"{f['brecha_T_new'] if f['brecha_T_new'] is not None else float('nan'):12.6f}"
        )
    ar = cr["anatomia_del_residual"]
    print(
        f"\nAnatomía del residual: máx {ar['max']} en la celda {ar['celda_del_maximo']['indice']} "
        f"({ar['celda_del_maximo']['km_del_cbd']} km), mediana {ar['percentil_50']}, "
        f"{ar['celdas_sobre_la_tolerancia']}/{ar['celdas_totales']} celdas sobre la tolerancia"
    )
    print("\nCriterio laxo del frontend (MSA con max_iter=2):")
    for f in cr["criterio_laxo_del_frontend"]:
        print(
            f"  k={f['k']}  residual={f['residual']}  msa={f['msa_convergio']}  "
            f"núcleo={f['nucleo_dice']}  api.ts={f['api_ts_diria']}"
        )
    print("\nPoblación:")
    for f in datos["poblacion"]:
        print(
            f"  {f['poblacion']:>6}  iter={f['iteraciones']:>2}  conv={f['convergio']}  "
            f"t={f['tiempo_medio_min']:6.2f} min  theil={f['theil']:.4f}  "
            f"auto={f['reparto_pct']['Auto']:.2f}"
        )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
