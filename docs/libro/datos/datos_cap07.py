"""Datos del capítulo 7 — Bienestar e indicadores.

Produce `cap07.json`. El módulo contesta la pregunta que el reparto modal no
contesta —¿esta política mejora al sistema?— y su dificultad no es calcular sino
**elegir la unidad**: el mismo estado de la ciudad da signos distintos según con
qué se agreguen los útiles de estratos distintos.

El capítulo audita esa elección. El informe de bienestar sostiene que agregar al
VoT social es «implícitamente redistributivo» porque `1/|β_t|` variaba 3,7 veces
entre estratos mientras `1/λ_h` era casi plano. Eso era cierto antes de D-33.
Con transporte homoscedástico los dos factores intercambiaron papeles, así que
acá se vuelve a medir todo: los pesos, lo que le pasa al dinero, y si el
resultado que el informe destaca —Downs-Thomson aparece o no según la unidad—
sobrevive.

Siete bloques:

1. `dos_monedas` — los dos factores de conversión de útiles a pesos y el peso
   implícito que cada uno le da a cada estrato.
2. `el_dinero_tambien_se_reprecia` — prueba de envolvente: derivada de cada
   excedente respecto de la tarifa, a tiempos y demanda fijos.
3. `downs_thomson_por_unidad` — el barrido de pistas con las dos medidas y los
   dos métodos de asignación.
4. `bienestar_social` — de qué está hecho el número que la interfaz titula
   «bienestar social», y cuánto pesa el factor día/punta.
5. `poblacion_que_desaparece` — qué pasa con quien se queda sin ningún modo
   factible cuando la interfaz apaga uno.
6. `segregacion` — el Theil: convergencia de grilla y poblacional vs territorial.
7. `costo_generalizado` — D-37: cuánto mueve ponderar espera y acceso.

Correr desde `packages/titirilquen_core` (~1 min):

    uv run python ../../docs/libro/datos/datos_cap07.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "packages" / "titirilquen_core" / "tests"))

import test_linea_base as base
from titirilquen_core.bienestar import (
    PONDERADOR_SNI_ACCESO,
    PONDERADOR_SNI_ESPERA,
    calcular_agregados,
    minutos_ponderados,
    vot_clp_hora,
)
from titirilquen_core.city import CiudadLineal
from titirilquen_core.constantes import MODOS, VOT_SOCIAL_CLP_HORA
from titirilquen_core.coupled_metrics import _theil
from titirilquen_core.demand.utility import TiemposObservados
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.accesibilidad import T_flujo_libre
from titirilquen_core.land_use.ciudad import LandUseCity

SALIDA = Path(__file__).parent / "cap07.json"
NOMBRES = ("alto", "medio", "bajo")
ESTRATOS = (1, 2, 3)


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


def _corre(sim, land_use=None):
    """Corre el MSA de la aplicación y devuelve `(agregados, trace)`."""
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, land_use or base._land_use_web(), trace, localizacion="original"
    ):
        pass
    return calcular_agregados(sim, trace), trace


# ---------------------------------------------------------------------------
# 1. Las dos monedas
# ---------------------------------------------------------------------------


def dos_monedas() -> dict:
    """Los dos factores que pasan útiles a pesos, y el peso que implican.

        conductual:  1/λ_h        con λ_h = |b_costo_h|
        social:      1/λ^soc_h    con λ^soc_h = |b_tiempo_h|·60 / VoT_social

    El cociente entre ambos es el peso relativo que la medida social le da a
    cada estrato, y es exactamente `VoT_social / VoT_h`.
    """
    sim = base._config_web()
    filas = {}
    for h in ESTRATOS:
        b = sim.demand.estratos[h].betas  # type: ignore[index]
        lam = abs(float(b.b_costo))
        lam_soc = abs(float(b.b_tiempo_viaje)) * 60.0 / VOT_SOCIAL_CLP_HORA
        filas[NOMBRES[h - 1]] = {
            "b_costo": float(b.b_costo),
            "b_tiempo_viaje": float(b.b_tiempo_viaje),
            "vot_conductual_clp_hora": round(vot_clp_hora(sim, h), 1),  # type: ignore[arg-type]
            "lambda_conductual": round(lam, 9),
            "lambda_social": round(lam_soc, 9),
            "util_en_clp_conductual": round(1.0 / lam, 1),
            "util_en_clp_social": round(1.0 / lam_soc, 1),
            "peso_relativo_social": round(lam / lam_soc, 4),
        }
    pesos = [filas[n]["peso_relativo_social"] for n in NOMBRES]
    utiles_soc = [filas[n]["util_en_clp_social"] for n in NOMBRES]
    utiles_cond = [filas[n]["util_en_clp_conductual"] for n in NOMBRES]
    return {
        "vot_social_clp_hora": VOT_SOCIAL_CLP_HORA,
        "por_estrato": filas,
        "razon_extremos_conductual": round(max(utiles_cond) / min(utiles_cond), 4),
        "razon_extremos_social": round(max(utiles_soc) / min(utiles_soc), 4),
        "lambda_social_es_comun": bool(max(utiles_soc) - min(utiles_soc) < 1e-6),
        "peso_relativo_social_bajo_sobre_alto": round(pesos[2] / pesos[0], 4),
        "nota": (
            "Desde D-33 el transporte es homoscedástico: `b_tiempo_viaje` es común "
            "a los tres estratos, así que `λ^soc` también lo es y la medida social "
            "es la suma LLANA de útiles. La que pondera es la conductual, y "
            "pondera a favor del estrato alto. Antes de D-33 era al revés, y el "
            "informe de bienestar todavía cuenta esa versión."
        ),
    }


# ---------------------------------------------------------------------------
# 2. El dinero también se reprecia
# ---------------------------------------------------------------------------


def el_dinero_tambien_se_reprecia() -> dict:
    """Prueba de envolvente sobre la tarifa del metro.

    Subir la tarifa en $1 con los TIEMPOS y la DEMANDA fijos tiene que costar
    exactamente $1 por viaje de metro, si el dinero vale un peso. Se reusa el
    mismo `trace` para las dos evaluaciones, así que no hay respuesta de
    equilibrio: es la derivada parcial, no la total.
    """
    sim = base._config_web()
    a, trace = _corre(sim)
    d = 1.0
    gl = sim.demand.globales.model_copy(
        update={"costo_tarifa_metro": sim.demand.globales.costo_tarifa_metro + d}
    )
    sim2 = sim.model_copy(
        update={"demand": sim.demand.model_copy(update={"globales": gl})}
    )
    b = calcular_agregados(sim2, trace)
    assert a is not None and b is not None

    viajes_metro = float(a["viajes_por_modo"]["Metro"])
    pred_social = sum(
        -float(a["viajes_por_modo_estrato"][str(h)]["Metro"])
        * VOT_SOCIAL_CLP_HORA
        / float(a["vot_por_estrato_clp_hora"][str(h)])
        for h in ESTRATOS
    )
    der_cond = (b["excedente_total_clp"] - a["excedente_total_clp"]) / d
    der_soc = (b["excedente_social_total_clp"] - a["excedente_social_total_clp"]) / d
    return {
        "viajes_de_metro": round(viajes_metro, 1),
        "derivada_conductual": round(der_cond, 1),
        "derivada_social": round(der_soc, 1),
        "prediccion_si_el_peso_vale_un_peso": round(-viajes_metro, 1),
        "prediccion_si_el_dinero_se_reprecia": round(pred_social, 1),
        "error_relativo_conductual": round(abs(der_cond / -viajes_metro - 1.0), 5),
        "error_relativo_social": round(abs(der_soc / pred_social - 1.0), 5),
        "pesos_por_peso_de_tarifa": {
            NOMBRES[h - 1]: round(
                VOT_SOCIAL_CLP_HORA / float(a["vot_por_estrato_clp_hora"][str(h)]), 4
            )
            for h in ESTRATOS
        },
        "nota": (
            "La medida conductual cobra $1 por cada $1 de tarifa. La social cobra "
            "$0,54 al estrato alto y $2,09 al bajo: el reescalado no toca sólo el "
            "TIEMPO, toca la utilidad entera, dinero incluido. Es un ponderador "
            "distributivo legítimo, pero el rótulo de la interfaz dice otra cosa."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Downs-Thomson según la unidad
# ---------------------------------------------------------------------------


def downs_thomson_por_unidad() -> dict:
    """¿Sigue en pie que el signo del Δ depende de la unidad de agregación?

    Se barre el número de pistas con los dos métodos: el de la aplicación
    (`expected`, medida = logsum) y el del informe (`todo_o_nada`, medida =
    utilidad máxima, tolerancia 0,02 y 120 iteraciones).
    """
    out = {}
    for metodo, tol, max_iter in (("expected", 0.1, 20), ("todo_o_nada", 0.02, 120)):
        filas = []
        for pistas in (1, 2, 3, 4, 6):
            sim = base._config_web()
            car = sim.supply.car.model_copy(update={"num_pistas": pistas})
            sim = sim.model_copy(
                update={
                    "supply": sim.supply.model_copy(update={"car": car}),
                    "assignment": metodo,
                    "tolerance": tol,
                    "max_iter": max_iter,
                }
            )
            a, trace = _corre(sim)
            assert a is not None
            n = a["viajeros"]
            emparejado = (
                a["excedente_max_total_clp"]
                if a["medida_bienestar"] == "utilidad_maxima"
                else a["excedente_total_clp"]
            )
            filas.append(
                {
                    "num_pistas": pistas,
                    "iteraciones": len(trace.iteraciones),
                    "convergio": bool(trace.converged),
                    "metro_pct": round(100.0 * a["viajes_por_modo"]["Metro"] / n, 2),
                    "exc_conductual_por_viajero": round(emparejado / n, 1),
                    "exc_social_por_viajero": round(
                        a["excedente_social_total_clp"] / n, 1
                    ),
                }
            )
        base_c = filas[0]["exc_conductual_por_viajero"]
        base_s = filas[0]["exc_social_por_viajero"]
        for f in filas:
            f["delta_conductual"] = round(f["exc_conductual_por_viajero"] - base_c, 1)
            f["delta_social"] = round(f["exc_social_por_viajero"] - base_s, 1)
        dc = [f["delta_conductual"] for f in filas]
        ds = [f["delta_social"] for f in filas]
        out[metodo] = {
            "medida": "utilidad_maxima" if metodo == "todo_o_nada" else "logsum",
            "filas": filas,
            "conductual_monotono_creciente": all(
                b >= a - 1e-9 for a, b in pairwise(dc)
            ),
            "social_monotono_creciente": all(b >= a - 1e-9 for a, b in pairwise(ds)),
            "las_dos_unidades_dan_el_mismo_orden": [x > 0 for x in dc[1:]]
            == [x > 0 for x in ds[1:]],
        }
    return out


# ---------------------------------------------------------------------------
# 4. De qué está hecho el «bienestar social»
# ---------------------------------------------------------------------------


def bienestar_social() -> dict:
    """La composición del titular, y el peso del factor día/punta.

    `bienestar_social = excedente + recaudación − costo del operador`. Los tres
    primeros términos son flujos de la HORA PUNTA; el cuarto lleva un factor
    día/punta que lo lleva a base diaria por viaje. La composición dice cuánto
    de la cifra depende de esa asimetría.
    """
    sim = base._config_web()
    a, _ = _corre(sim)
    assert a is not None
    comp = {
        "excedente_emparejado_clp": round(
            a["excedente_max_total_clp"]
            if a["medida_bienestar"] == "utilidad_maxima"
            else a["excedente_total_clp"]
        ),
        "recaudacion_parking_clp": round(a["recaudacion_parking_clp"]),
        "recaudacion_tarifa_clp": round(a["recaudacion_tarifa_clp"]),
        "costo_operador_clp": round(a["costo_operador_clp"]),
        "bienestar_social_clp": round(a["bienestar_social_clp"]),
    }
    sensibilidad = []
    for f in (1.0, 2.0, 3.0, 3.7):
        train = sim.supply.train.model_copy(update={"factor_dia_punta": f})
        s = sim.model_copy(
            update={"supply": sim.supply.model_copy(update={"train": train})}
        )
        b, _ = _corre(s)
        assert b is not None
        sensibilidad.append(
            {
                "factor_dia_punta": f,
                "costo_operador_clp": round(b["costo_operador_clp"]),
                "subsidio_metro_clp": round(b["subsidio_metro_clp"]),
                "autofinancia": bool(b["subsidio_metro_clp"] < 0),
                "bienestar_social_clp": round(b["bienestar_social_clp"]),
            }
        )
    ref = next(x for x in sensibilidad if x["factor_dia_punta"] == 2.0)
    uno = next(x for x in sensibilidad if x["factor_dia_punta"] == 1.0)

    # El NIVEL del titular tiene cero arbitrario, así que lo que hay que mirar es
    # el Δ entre escenarios. El factor no se cancela en ese Δ porque la
    # frecuencia del metro es endógena: menos pasajeros ⇒ menos trenes ⇒ menos
    # costo. Se mide con el mismo barrido de pistas del bloque 3.
    delta = []
    for f in (1.0, 2.0, 3.0):
        vals = {}
        for pistas in (2, 4):
            train = sim.supply.train.model_copy(update={"factor_dia_punta": f})
            car = sim.supply.car.model_copy(update={"num_pistas": pistas})
            s2 = sim.model_copy(
                update={
                    "supply": sim.supply.model_copy(update={"train": train, "car": car})
                }
            )
            c, _ = _corre(s2)
            assert c is not None
            vals[pistas] = c
        delta.append(
            {
                "factor_dia_punta": f,
                "d_costo_operador_clp": round(
                    vals[4]["costo_operador_clp"] - vals[2]["costo_operador_clp"]
                ),
                "d_bienestar_social_clp": round(
                    vals[4]["bienestar_social_clp"] - vals[2]["bienestar_social_clp"]
                ),
            }
        )
    return {
        "parametros_del_metro": {
            "costo_operacion_tren_km": float(sim.supply.train.costo_operacion_tren_km),
            "factor_dia_punta_default": float(sim.supply.train.factor_dia_punta),
        },
        "composicion": comp,
        "sensibilidad_factor_dia_punta": sensibilidad,
        "efecto_en_el_delta_2_a_4_pistas": delta,
        "salto_de_factor_1_a_2_sobre_el_titular": round(
            (ref["bienestar_social_clp"] - uno["bienestar_social_clp"])
            / abs(ref["bienestar_social_clp"]),
            4,
        ),
        "nota": (
            "El excedente tiene cero arbitrario (arrastra las ASC), así que el "
            "NIVEL del titular no significa nada por sí solo: la interfaz lo "
            "muestra contra un escenario de referencia. Lo que sí es propio de "
            "este número es la base contable mixta — tres términos de hora punta "
            "y uno llevado a día."
        ),
    }


# ---------------------------------------------------------------------------
# 5. La población que desaparece
# ---------------------------------------------------------------------------


def poblacion_que_desaparece() -> list[dict]:
    """Quien no tiene ningún modo factible sale del agregado en vez de contar
    como bienestar muy bajo.

    El módulo declara el riesgo y lo midió en cero (agosto de 2026). Los
    interruptores de modo de `SandboxPage` permiten activarlo.
    """
    sim = base._config_web()
    filas = []
    for etiqueta, modos in (
        ("todos", ("Auto", "Metro", "Bici", "Caminata")),
        ("sin metro", ("Auto", "Bici", "Caminata")),
        ("sin auto", ("Metro", "Bici", "Caminata")),
        ("sin bici ni caminata", ("Auto", "Metro")),
    ):
        s = sim.model_copy(update={"modos_habilitados": modos})
        a, trace = _corre(s)
        assert a is not None
        agentes = trace.agentes
        varados = sum(
            1 for x in agentes if not x.teletrabaja and x.modo_elegido is None
        )
        no_teletrabajan = sum(1 for x in agentes if not x.teletrabaja)
        n = a["viajeros"]
        filas.append(
            {
                "escenario": etiqueta,
                "modos": list(modos),
                "viajeros_en_el_agregado": round(n, 1),
                "agentes_varados": varados,
                "varados_pct_de_la_poblacion": round(100.0 * varados / len(agentes), 2),
                "varados_pct_de_quienes_viajarian": round(
                    100.0 * varados / no_teletrabajan, 2
                ),
                "excedente_total_clp": round(a["excedente_total_clp"]),
                "excedente_por_viajero_clp": round(a["excedente_total_clp"] / n, 1),
                "bienestar_social_clp": round(a["bienestar_social_clp"]),
                # Apagar un modo lo saca del conjunto de ELECCIÓN, no de la
                # oferta: el metro sigue circulando a frecuencia mínima y
                # costando, con cero recaudación.
                "tren_km_hora": round(a["tren_km_hora"], 1),
                "costo_operador_clp": round(a["costo_operador_clp"]),
                "recaudacion_tarifa_clp": round(a["recaudacion_tarifa_clp"]),
            }
        )
    todos, sin_metro = filas[0], filas[1]
    # Cota inferior del bienestar que no se contabiliza: si los varados valieran
    # lo mismo que el viajero promedio del escenario, ya faltaría esto.
    faltante = sin_metro["excedente_por_viajero_clp"] * (
        todos["viajeros_en_el_agregado"] - sin_metro["viajeros_en_el_agregado"]
    )
    return [
        *filas,
        {
            "escenario": "_cota",
            "cota_inferior_del_excedente_no_contado_clp": round(faltante),
            "dano_medido_clp": round(
                sin_metro["excedente_total_clp"] - todos["excedente_total_clp"]
            ),
            "dano_con_los_varados_al_promedio_clp": round(
                sin_metro["excedente_total_clp"]
                + faltante
                - todos["excedente_total_clp"]
            ),
            "subestimacion_del_dano_pct": round(
                100.0
                * abs(faltante)
                / abs(sin_metro["excedente_total_clp"] - todos["excedente_total_clp"]),
                2,
            ),
            "nota": (
                "Cota INFERIOR: valora a los varados al excedente del viajero medio "
                "del mismo escenario. Su pérdida real es mayor —por eso quedaron "
                "varados— así que el agregado subestima el daño por al menos esto."
            ),
        },
    ]


# ---------------------------------------------------------------------------
# 6. Segregación
# ---------------------------------------------------------------------------


def segregacion() -> dict:
    """El índice H de Theil: ¿depende de la grilla? ¿cuánto pesa D-38?"""
    sim = base._config_web()
    lu = base._land_use_web()
    filas = []
    for n in (51, 101, 201, 401, 801):
        ciudad = CiudadLineal(n_celdas=n, largo_total_km=sim.city.largo_ciudad_km)
        s = sim.model_copy(update={"city": sim.city.model_copy(update={"n_celdas": n})})
        T = T_flujo_libre(
            s.demand, n, ciudad.cbd_index, ciudad.ancho_celda_km, supply=s.supply
        )
        city = LandUseCity.build(
            L=n,
            CBD=ciudad.cbd_index,
            cfg=lu,
            T=T,
            rng=np.random.default_rng(42),
            ancho_celda_km=ciudad.ancho_celda_km,
        )
        assert city.result is not None
        Q = np.asarray(city.result.Q, dtype=float)
        S = np.asarray(city.S, dtype=float)
        filas.append(
            {
                "n_celdas": n,
                "theil_poblacional": round(_theil(Q, S), 5),
                "theil_territorial": round(_theil(Q), 5),
            }
        )
    dif = [f["theil_poblacional"] for f in filas]
    ref = next(f for f in filas if f["n_celdas"] == 201)
    return {
        "filas": filas,
        "diferencias_sucesivas": [round(b - a, 5) for a, b in pairwise(dif)],
        "brecha_territorial_vs_poblacional_pct_en_la_base": round(
            100.0 * (ref["theil_territorial"] / ref["theil_poblacional"] - 1.0), 2
        ),
        "nota": (
            "Converge al refinar la grilla —las diferencias sucesivas se reducen a "
            "la mitad al duplicar `n_celdas`—, así que el índice es una propiedad "
            "de la ciudad y no del enrejado. El valor de la aplicación (201) queda "
            "un ~2 % por debajo del límite."
        ),
    }


# ---------------------------------------------------------------------------
# 7. El costo generalizado y los ponderadores (D-37)
# ---------------------------------------------------------------------------


def costo_generalizado() -> dict:
    """Cuánto mueve pesar espera y acceso como corresponde.

    El término de tiempo se recalcula con `minutos_ponderados` sobre la misma
    demanda esperada del núcleo, con los ponderadores reales y con 1/1/1; la
    diferencia es el efecto puro de D-37 (el dinero no cambia).
    """
    sim = base._config_web()
    a, trace = _corre(sim)
    assert a is not None and trace.demanda_estrato is not None
    ciudad = CiudadLineal(
        n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km
    )
    snap = trace.iteraciones[-1]
    d_soc = d_plano = d_perc = d_perc_plano = 0.0
    for i in range(ciudad.n_celdas):
        dist = abs(ciudad.cbd_index - i) * ciudad.ancho_celda_km
        t_cam = dist / sim.demand.globales.v_caminata * 60.0
        tiempos = TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        for h in ESTRATOS:
            b = sim.demand.estratos[h].betas  # type: ignore[index]
            bt = abs(float(b.b_tiempo_viaje)) or 1.0
            for k, modo in enumerate(MODOS):
                dem = float(trace.demanda_estrato[h - 1, k, i])
                if dem <= 0:
                    continue
                d_soc += dem * minutos_ponderados(
                    modo,
                    tiempos,
                    t_cam,
                    w_espera=PONDERADOR_SNI_ESPERA,
                    w_acceso=PONDERADOR_SNI_ACCESO,
                    w_caminata=1.0,
                )
                d_perc += dem * minutos_ponderados(
                    modo,
                    tiempos,
                    t_cam,
                    w_espera=abs(float(b.b_tiempo_espera)) / bt,
                    w_acceso=abs(float(b.b_tiempo_acceso)) / bt,
                    w_caminata=abs(float(b.b_tiempo_caminata)) / bt,
                )
                plano = dem * minutos_ponderados(
                    modo, tiempos, t_cam, w_espera=1.0, w_acceso=1.0, w_caminata=1.0
                )
                d_plano += plano
                d_perc_plano += plano
    cg_soc_plano = a["costo_generalizado_social_clp"] - (
        (d_soc - d_plano) / 60.0 * VOT_SOCIAL_CLP_HORA
    )
    pesos = {}
    for h in ESTRATOS:
        b = sim.demand.estratos[h].betas  # type: ignore[index]
        bt = abs(float(b.b_tiempo_viaje))
        pesos[NOMBRES[h - 1]] = {
            "espera": round(abs(float(b.b_tiempo_espera)) / bt, 3),
            "acceso": round(abs(float(b.b_tiempo_acceso)) / bt, 3),
            "caminata": round(abs(float(b.b_tiempo_caminata)) / bt, 3),
        }
    return {
        "ponderadores_percibidos": pesos,
        "ponderadores_sni": {
            "espera": PONDERADOR_SNI_ESPERA,
            "acceso": PONDERADOR_SNI_ACCESO,
            "caminata": 1.0,
        },
        "minutos_totales_planos": round(d_plano, 1),
        "minutos_totales_sni": round(d_soc, 1),
        "minutos_totales_percibidos": round(d_perc, 1),
        "recargo_sni_pct": round(100.0 * (d_soc / d_plano - 1.0), 2),
        "recargo_percibido_pct": round(100.0 * (d_perc / d_plano - 1.0), 2),
        "cg_social_clp": round(a["costo_generalizado_social_clp"]),
        "cg_social_con_minutos_planos_clp": round(cg_soc_plano),
        "efecto_d37_sobre_el_cg_social_pct": round(
            100.0 * (a["costo_generalizado_social_clp"] / cg_soc_plano - 1.0), 2
        ),
        "cg_percibido_clp": round(a["costo_generalizado_percibido_clp"]),
        "nota": (
            "Las penalizaciones escalonadas de bici y caminata quedan fuera a "
            "propósito: son desutilidad, no tiempo. Los ponderadores de espera y "
            "acceso del percibido COINCIDEN con los del SNI (2,0 y 2,0) porque "
            "`presets.py` calibró los betas contra esa misma tabla; toda la "
            "diferencia entre los dos recargos la pone la caminata, 1,7 en la "
            "utilidad y 1,0 en la norma, que no la cubre. Y desde D-33 los tres "
            "estratos comparten los tres ponderadores."
        ),
    }


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap07.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web`), rama "
                "«original»: 201 celdas, 20 km, 36.000 hogares, semilla 42, "
                "asignación esperada, tolerancia 0,1. El barrido de pistas repite "
                "además el método del informe de bienestar (`todo_o_nada`, "
                "tolerancia 0,02, 120 iteraciones)."
            ),
        },
        "dos_monedas": dos_monedas(),
        "el_dinero_tambien_se_reprecia": el_dinero_tambien_se_reprecia(),
        "downs_thomson_por_unidad": downs_thomson_por_unidad(),
        "bienestar_social": bienestar_social(),
        "poblacion_que_desaparece": poblacion_que_desaparece(),
        "segregacion": segregacion(),
        "costo_generalizado": costo_generalizado(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    m = datos["dos_monedas"]
    print("Un útil, en pesos:")
    for n in NOMBRES:
        f = m["por_estrato"][n]
        print(
            f"  {n:<6} conductual {f['util_en_clp_conductual']:>8,.1f}   "
            f"social {f['util_en_clp_social']:>8,.1f}   "
            f"peso social/conductual {f['peso_relativo_social']:.3f}"
        )
    print(
        f"  razón extremos: conductual {m['razon_extremos_conductual']}  ·  "
        f"social {m['razon_extremos_social']}  ·  λ social común: {m['lambda_social_es_comun']}"
    )
    d = datos["el_dinero_tambien_se_reprecia"]
    print("\nDerivada del excedente respecto de la tarifa (tiempos y demanda fijos):")
    print(
        f"  conductual {d['derivada_conductual']:>10}  vs  {d['prediccion_si_el_peso_vale_un_peso']} "
        f"(error {d['error_relativo_conductual']:.2%})"
    )
    print(
        f"  social     {d['derivada_social']:>10}  vs  {d['prediccion_si_el_dinero_se_reprecia']} "
        f"(error {d['error_relativo_social']:.2%})"
    )
    print("\nDowns-Thomson por unidad:")
    for metodo, blq in datos["downs_thomson_por_unidad"].items():
        print(f"  {metodo} (medida {blq['medida']}):")
        for f in blq["filas"]:
            print(
                f"    {f['num_pistas']} pista(s)  metro {f['metro_pct']:>6.2f}%  "
                f"conductual {f['exc_conductual_por_viajero']:>9.1f} (Δ {f['delta_conductual']:>+7.1f})  "
                f"social {f['exc_social_por_viajero']:>9.1f} (Δ {f['delta_social']:>+7.1f})"
            )
        print(
            f"    conductual monótono: {blq['conductual_monotono_creciente']}  ·  "
            f"social monótono: {blq['social_monotono_creciente']}  ·  "
            f"mismo orden: {blq['las_dos_unidades_dan_el_mismo_orden']}"
        )
    print("\nPoblación que desaparece:")
    for f in datos["poblacion_que_desaparece"]:
        if f["escenario"] == "_cota":
            print(
                f"  cota inferior no contada: {f['cota_inferior_del_excedente_no_contado_clp']:,} $"
            )
            continue
        print(
            f"  {f['escenario']:<22} viajeros {f['viajeros_en_el_agregado']:>9,.1f}  "
            f"varados {f['agentes_varados']:>5} ({f['varados_pct_de_la_poblacion']:>5.2f}%)"
        )
    s = datos["segregacion"]
    print("\nTheil:")
    for f in s["filas"]:
        print(
            f"  n={f['n_celdas']:>4}  poblacional {f['theil_poblacional']:.5f}  "
            f"territorial {f['theil_territorial']:.5f}"
        )
    print(
        f"  brecha territorial/poblacional en la base: "
        f"{s['brecha_territorial_vs_poblacional_pct_en_la_base']} %"
    )
    c = datos["costo_generalizado"]
    print(
        f"\nD-37: recargo SNI {c['recargo_sni_pct']} % sobre minutos planos; "
        f"efecto sobre el CG social {c['efecto_d37_sobre_el_cg_social_pct']} %"
    )
    b = datos["bienestar_social"]
    print(
        f"\nBienestar social: {b['composicion']['bienestar_social_clp']:,} $ · "
        f"pasar el factor día/punta de 2 a 1 lo mueve "
        f"{b['salto_de_factor_1_a_2_sobre_el_titular']:.0%} del titular"
    )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
