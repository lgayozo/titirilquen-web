"""Datos del capítulo 4 — Demanda y elección modal.

Produce `cap04.json`. Todo se mide en **minutos-equivalentes en vehículo**:
dividir cada término de la utilidad por `|b_tiempo_viaje|` del estrato cancela la
escala de su utilidad, que es lo único que hace comparables los coeficientes
entre estratos y entre modos. Es la misma cuenta que hace
`scripts/diagnostico_calibracion.py`, y desde D-33 el denominador es común.

Cinco bloques:

1. `anatomia` — los betas por estrato en minutos-equivalentes: qué pesa cada
   componente de tiempo, cada ASC y cada penalización.
2. `costo_por_modo` — el costo generalizado completo de un viaje según la
   distancia, modo por modo, con sus saltos.
3. `factibilidad` — qué modos existen a cada distancia, y cuánta población queda
   de cada lado de los cortes.
4. `elasticidades` — respuesta del reparto a la tarifa, al combustible y al
   peaje por km.
5. `logit_vs_determinista` — cuánto cambia el reparto según el método.
6. `peaje_y_bienestar` — el bienestar social a lo largo del peaje por km (D7),
   contra el parking de 5.000 que era la «Tarificación Vial» hasta oct-2026.
7. `ancla_vot` — la media de los VoT ponderada por viajeros y por hogares,
   contra el VST de Precios Sociales 2026 (D5).
8. `umbrales` — «escalones» contra «suaves» (`globales.umbrales`): reparto,
   saltos del logsum y del metro, la ciudad Compacta con cada política y el
   valle de Q_alto en el suelo con su sensibilidad a `a` y `ω`.

Correr desde `packages/titirilquen_core` (~2 min):

    uv run python ../../docs/libro/datos/datos_cap04.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "packages" / "titirilquen_core" / "tests"))

import test_linea_base as base
import titirilquen_core.demand.utility as utility_mod
import titirilquen_core.equilibrium.msa as msa
from titirilquen_core.bienestar import calcular_agregados
from titirilquen_core.city import CiudadLineal
from titirilquen_core.constantes import VOT_SOCIAL_CLP_HORA
from titirilquen_core.demand.choice import (
    probabilidades_logit,
    probabilidades_todo_o_nada,
)
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.accesibilidad import T_flujo_libre, lambda_desde_demanda
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.presets import CITY_PRESETS, DEFAULT_STRATA, POLICY_PRESETS

SALIDA = Path(__file__).parent / "cap04.json"
ESTRATOS = (1, 2, 3)
NOMBRES = {1: "alto", 2: "medio", 3: "bajo"}


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


def anatomia() -> dict:
    """Los betas en minutos-equivalentes en vehículo (dividir por |b_tiempo_viaje|)."""
    filas = {}
    for h in ESTRATOS:
        b = DEFAULT_STRATA[h]["betas"]
        bt = abs(b["b_tiempo_viaje"])
        pen = b["penalizaciones_fisicas"]
        filas[NOMBRES[h]] = {
            "b_tiempo_viaje": b["b_tiempo_viaje"],
            "b_costo": b["b_costo"],
            "vot_clp_hora": round(b["b_tiempo_viaje"] / b["b_costo"] * 60, 1),
            # Cuánto pesa un minuto de cada modo, en minutos de viaje en vehículo.
            "peso_min_en_vehiculo": 1.0,
            "peso_min_bici": 1.0,  # usa b_tiempo_viaje, igual que ir sentado
            "peso_min_caminata": round(abs(b["b_tiempo_caminata"]) / bt, 3),
            "peso_min_espera": round(abs(b["b_tiempo_espera"]) / bt, 3),
            "peso_min_acceso": round(abs(b["b_tiempo_acceso"]) / bt, 3),
            # ASC en minutos-equivalentes, respecto del metro.
            "asc_auto_min": round(-(b["asc_auto"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2),
            "asc_bici_min": round(-(b["asc_bici"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2),
            "asc_caminata_min": round(
                -(b["asc_caminata"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2
            ),
            # Penalizaciones escalonadas, acumuladas, en minutos-equivalentes.
            "pen_bici_min": {
                ">10": round(abs(pen["bici_10"]) / bt, 2),
                ">20": round(abs(pen["bici_10"] + pen["bici_20"]) / bt, 2),
                ">30": round(abs(pen["bici_10"] + pen["bici_20"] + pen["bici_30"]) / bt, 2),
            },
            "pen_caminata_min": {
                ">5": round(abs(pen["walk_5"]) / bt, 2),
                ">15": round(abs(pen["walk_5"] + pen["walk_15"]) / bt, 2),
                ">25": round(abs(pen["walk_5"] + pen["walk_15"] + pen["walk_25"]) / bt, 2),
            },
        }
    return filas


def _utils(h: int, celda: int, ciudad, cfg, tiene_auto: bool):
    return calcular_utilidades(
        estrato=h,
        celda_origen=celda,
        tiene_auto=tiene_auto,
        ciudad=ciudad,
        config=cfg.demand,
        tiempos_observados=None,
    )


def costo_por_modo() -> dict:
    """El costo generalizado a flujo libre, en minutos-equivalentes, por distancia."""
    cfg = base._config_web()
    ciudad = CiudadLineal(n_celdas=cfg.city.n_celdas, largo_total_km=cfg.city.largo_ciudad_km)
    bt = abs(DEFAULT_STRATA[2]["betas"]["b_tiempo_viaje"])
    filas = []
    for km in (0.5, 1, 2, 3, 5, 7, 10):
        celda = ciudad.cbd_index + int(round(km / ciudad.ancho_celda_km))
        celda = min(celda, ciudad.n_celdas - 1)
        u = _utils(2, celda, ciudad, cfg, True)
        fila = {"km": km}
        for m, bd in u.items():
            fila[m] = None if not bd.feasible else round(-bd.valor / bt, 2)
        filas.append(fila)
    return {
        "estrato": "medio",
        "unidad": "minutos-equivalentes en vehículo (−V/|b_t|); menor es mejor",
        "nota": "A flujo libre. Incluye ASC, tiempo, dinero y penalizaciones.",
        "filas": filas,
    }


def factibilidad() -> dict:
    """Qué modos existen a cada distancia, y cuánta gente queda de cada lado."""
    cfg = base._config_web()
    ciudad = CiudadLineal(n_celdas=cfg.city.n_celdas, largo_total_km=cfg.city.largo_ciudad_km)
    gl = cfg.demand.globales
    umbral_cam = gl.corte_caminata_min * gl.v_caminata / 60
    umbral_bici = gl.corte_bici_min * gl.v_bici / 60

    perfil = []
    for km in (0.5, 1, 2, 2.4, 3, 5, 7, 10):
        celda = min(
            ciudad.cbd_index + int(round(km / ciudad.ancho_celda_km)),
            ciudad.n_celdas - 1,
        )
        u = _utils(2, celda, ciudad, cfg, True)
        perfil.append({"km": km, **{m: bool(bd.feasible) for m, bd in u.items()}})

    # Fracción de celdas (y de la ciudad) más allá de cada umbral.
    d = np.abs(np.arange(ciudad.n_celdas) - ciudad.cbd_index) * ciudad.ancho_celda_km
    return {
        "umbral_caminata_km": round(umbral_cam, 3),
        "umbral_bici_km": round(umbral_bici, 3),
        "corte_caminata_min": gl.corte_caminata_min,
        "corte_bici_min": gl.corte_bici_min,
        "celdas_sin_caminata_pct": round(100.0 * float(np.mean(d > umbral_cam)), 2),
        "celdas_sin_bici_pct": round(100.0 * float(np.mean(d > umbral_bici)), 2),
        "perfil": perfil,
    }


def _traza(sim, localizacion: str = "original", lu=None) -> ConvergenceTrace:
    trace = ConvergenceTrace()
    lu = lu or base._land_use_web()
    for _ in iter_msa_desde_suelo(sim, lu, trace, localizacion=localizacion):
        pass
    return trace


def bici_saturada() -> dict:
    """Auditoría D, ítem 12 (oct-2026): el corte de la bici se evalúa sobre t⁰ (D9) y
    el tramo congestionado se acota a la caminata (D-15), así que una ciclovía
    saturada no saca la bici del conjunto: la deja más lenta que el corte y, en
    la periferia, a paso de caminata."""
    filas = []
    for cap in (200, 1000, 2000, 6000):
        sim = base._config_web().model_copy(deep=True)
        sim.supply.bike.capacidad_pista = cap
        s = _traza(sim).iteraciones[-1]
        gl = sim.demand.globales
        ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
        dist = np.abs(np.arange(ciudad.n_celdas) - ciudad.cbd_index) * ciudad.ancho_celda_km
        d = s.demanda_bici
        con = d > 0
        a_pie = con & (dist > 0) & (s.t_bici >= 0.98 * dist / gl.v_caminata * 60)
        filas.append(
            {
                "capacidad_bici_h": cap,
                "bici_pct": round(100.0 * float(d.sum()) / sum(s.modal_split.values()), 1),
                "sobre_corte_pct": round(
                    100.0 * float(d[s.t_bici > gl.corte_bici_min].sum() / d.sum()), 1
                ),
                "a_paso_caminata_pct": round(100.0 * float(d[a_pie].sum() / d.sum()), 1),
                "t_max_min": round(float(s.t_bici[con].max()), 0),
                "t_libre_max_min": round(float(s.t_bici_libre[con].max()), 0),
            }
        )
    return {
        "nota": "Base, localización «original». % de los viajes en bici; t con demanda.",
        "filas": filas,
    }


def tenencia_por_celda() -> dict:
    """Auditoría D, ítem 15 (oct-2026): `round(n_viaja·prob_auto)` por celda y estrato
    (population.py) da dientes en la fracción con auto entre celdas vecinas."""
    out = {}
    for loc in ("original", "equilibrio"):
        sim = base._config_web()
        trace = _traza(sim, loc)
        n = sim.city.n_celdas
        viaja = np.zeros((3, n))
        auto = np.zeros((3, n))
        for a in trace.agentes:
            if not a.teletrabaja:
                viaja[a.estrato - 1, a.celda_origen] += 1
                auto[a.estrato - 1, a.celda_origen] += a.tiene_auto
        saltos, minimo = [], []
        for h in range(3):
            ok = viaja[h] > 0
            f = np.where(ok, auto[h] / np.maximum(viaja[h], 1), np.nan)
            par = ok[:-1] & ok[1:]
            saltos.extend(100.0 * np.abs(np.diff(f))[par])
            minimo.append(viaja[h][ok].min())
        out[loc] = {
            "salto_mediana_pp": round(float(np.median(saltos)), 1),
            "salto_max_pp": round(float(np.max(saltos)), 1),
            "hogares_min_celda": int(min(minimo)),
            "tenencia_agregada": [
                round(float(auto[h].sum() / viaja[h].sum()), 4) for h in range(3)
            ],
        }
    return out


def _con_globales(**cambios):
    sim = base._config_web()
    gl = sim.demand.globales.model_copy(update=cambios)
    return sim.model_copy(update={"demand": sim.demand.model_copy(update={"globales": gl})})


def _corre(sim) -> dict:
    trace = _traza(sim)
    s = trace.iteraciones[-1].modal_split
    t = sum(s.values())
    return {m: round(100.0 * v / t, 3) for m, v in s.items()}


def elasticidades() -> dict:
    """Respuesta del reparto a las palancas de precio."""
    out = {}
    for campo, valores in (
        ("costo_tarifa_metro", (0, 400, 800, 1200, 1600)),
        ("costo_combustible_km", (60, 120, 240, 480)),
        ("peaje_km", (0, 50, 100, 150, 200, 300)),
    ):
        out[campo] = [{campo: v, **_corre(_con_globales(**{campo: v}))} for v in valores]
    return out


def peaje_y_bienestar() -> dict:
    """D7: el bienestar social (excedente + recaudación − operador) a lo largo
    del peaje por km, con el parking base; y el parking de 5.000 sin peaje,
    que era la «Tarificación Vial» hasta oct-2026. Δ contra la base."""

    def mide(sim) -> dict:
        tr = _traza(sim)
        a = calcular_agregados(sim, tr)
        s = tr.iteraciones[-1].modal_split
        return {
            "bienestar": a["bienestar_social_clp"],
            "auto_pct": round(100.0 * s["Auto"] / sum(s.values()), 2),
            "vc_auto": round(float(np.max(tr.flujos_auto_veh_h)) / tr.capacidad_auto, 3),
            "recaudacion_peaje_clp": round(a["recaudacion_peaje_clp"]),
            "recaudacion_parking_clp": round(a["recaudacion_parking_clp"]),
            "iteraciones": len(tr.iteraciones),
        }

    w0 = None
    filas = []
    for v in (0, 25, 50, 75, 100, 150, 200, 250, 275, 300, 350, 400, 500, 600):
        m = mide(_con_globales(peaje_km=v))
        w0 = m["bienestar"] if w0 is None else w0
        filas.append({"peaje_km": v, **m})
    parking = mide(_con_globales(costo_parking=5000))
    for f in (*filas, parking):
        f["delta_bienestar_clp"] = round(f.pop("bienestar") - w0)
    from titirilquen_core.presets import POLICY_PRESETS

    return {
        "peaje_preset_tarificacion_vial": POLICY_PRESETS["Tarificación Vial"]["peaje"],
        "nota": (
            "Localización «original», tolerancia de la app "
            f"({str(base._config_web().tolerance).replace('.', ',')} min). Sin "
            "teletrabajo por defecto (oct-2026) el máximo pasó de 150 a 250–300 $/km; "
            "con la base de 4 pistas y ciclovía 6.000 (oct-2026), a 25–50 $/km."
        ),
        "barrido": filas,
        "parking_5000_sin_peaje": parking,
    }


#: VoT heredados antes de D5, sin fuente (`presets.py`, «ANCLA EN EL VST»). Son
#: la historia del ancla, no un parámetro vigente.
VOT_HEREDADOS = {1: 6200.0, 2: 3100.0, 3: 1600.0}


def ancla_vot() -> dict:
    """D5: la media de los VoT de la calibración contra el VST social, y la
    historia: cuánto daban los VoT heredados y el factor que se les aplicó. D5 se
    definió sobre los hogares NOMINALES (`H_por_estrato`, como
    `test_presets.py`); los de la ciudad difieren en decenas por el redondeo por
    celda. Sin teletrabajo por defecto, viajeros = hogares."""
    capturados = {}
    original = msa.generar_poblacion_desde_land_use_det

    def espia(**kw):
        capturados["agentes"] = original(**kw)
        return capturados["agentes"]

    msa.generar_poblacion_desde_land_use_det = espia
    try:
        sim = base._config_web()
        _traza(sim)
    finally:
        msa.generar_poblacion_desde_land_use_det = original
    agentes = capturados["agentes"]
    filas = {}
    for h in ESTRATOS:
        b = sim.demand.estratos[h].betas
        filas[NOMBRES[h]] = {
            "vot_clp_hora": round(b.b_tiempo_viaje / b.b_costo * 60, 1),
            "hogares": sum(1 for a in agentes if a.estrato == h),
            "viajeros": sum(1 for a in agentes if a.estrato == h and not a.teletrabaja),
        }

    def media(peso: str) -> float:
        n = sum(f[peso] for f in filas.values())
        return sum(f[peso] * f["vot_clp_hora"] for f in filas.values()) / n

    por_viajero, por_hogar = media("viajeros"), media("hogares")
    H = dict(zip(ESTRATOS, base._land_use_web().H_por_estrato, strict=True))
    heredada = sum(H[h] * VOT_HEREDADOS[h] for h in ESTRATOS) / sum(H.values())
    return {
        "por_estrato": filas,
        "vst_clp_hora": VOT_SOCIAL_CLP_HORA,
        "media_por_viajero_clp_hora": round(por_viajero, 1),
        "media_por_hogar_clp_hora": round(por_hogar, 1),
        "brecha_por_viajero_pct": round(100 * (por_viajero / VOT_SOCIAL_CLP_HORA - 1), 2),
        "brecha_por_hogar_pct": round(100 * (por_hogar / VOT_SOCIAL_CLP_HORA - 1), 2),
        "factor_para_igualar_por_viajero": round(VOT_SOCIAL_CLP_HORA / por_viajero, 4),
        "historia": {
            "vot_heredados_clp_hora": [VOT_HEREDADOS[h] for h in ESTRATOS],
            "hogares_nominales": [H[h] for h in ESTRATOS],
            "media_heredada_clp_hora": round(heredada, 1),
            "brecha_heredada_pct": round(100 * (heredada / VOT_SOCIAL_CLP_HORA - 1), 2),
            "factor_aplicado": round(VOT_SOCIAL_CLP_HORA / heredada, 4),
        },
    }


def _tope_todo_o_nada() -> int:
    """`MAX_ITER_TODO_O_NADA` de `SandboxPage.tsx`: al elegir todo o nada la
    interfaz lleva el tope a ese valor como mínimo (auditoría B)."""
    ts = (RAIZ / "apps" / "web" / "src" / "pages" / "SandboxPage.tsx").read_text(encoding="utf-8")
    return int(re.search(r"const MAX_ITER_TODO_O_NADA = (\d+);", ts).group(1))


def logit_vs_determinista() -> dict:
    """El mismo escenario con las dos reglas de elección."""
    out = {}
    for metodo in ("expected", "todo_o_nada"):
        # Al elegir todo o nada la app sube el tope: converge lento (D-70).
        tope = (
            {"max_iter": max(base._config_web().max_iter, _tope_todo_o_nada())}
            if metodo == "todo_o_nada"
            else {}
        )
        tr = _traza(base._config_web().model_copy(update={"assignment": metodo, **tope}))
        s = tr.iteraciones[-1].modal_split
        out[metodo] = {m: round(100.0 * v / sum(s.values()), 3) for m, v in s.items()}
        out[f"{metodo}_convergencia"] = {
            "convergio": bool(tr.converged),
            "iteraciones": len(tr.iteraciones),
            "brecha_final_min": round(float(tr.gap_final_min), 3),
        }
    # Y en una celda concreta: probabilidades contra el argmax.
    cfg = base._config_web()
    ciudad = CiudadLineal(n_celdas=cfg.city.n_celdas, largo_total_km=cfg.city.largo_ciudad_km)
    celda = ciudad.cbd_index + int(round(3.0 / ciudad.ancho_celda_km))
    u = _utils(2, celda, ciudad, cfg, True)
    out["celda_a_3km_estrato_medio"] = {
        "logit": {m: round(p, 4) for m, p in probabilidades_logit(u).items()},
        "todo_o_nada": {m: round(p, 4) for m, p in probabilidades_todo_o_nada(u).items()},
    }
    return out


def _con_umbrales(sim, umbrales: str):
    gl = sim.demand.globales.model_copy(update={"umbrales": umbrales})
    return sim.model_copy(update={"demand": sim.demand.model_copy(update={"globales": gl})})


def _reparto(trace: ConvergenceTrace) -> dict:
    s = trace.iteraciones[-1].modal_split
    t = sum(v for m, v in s.items() if m != "Teletrabajo")
    return {m: round(100.0 * v / t, 2) for m, v in s.items() if m != "Teletrabajo"}


#: Espejo de `applyPolicy` en `apps/web/src/components/modules/PresetGallery.tsx`:
#: clave del preset de política → ruta en la config. Pistas y ciclovía van a la
#: escala de la ciudad (A3); Compacta no declara ninguna de las dos, así que su
#: escala es la de referencia y la política se aplica con sus valores.
_MAPA_POLITICA = {
    "num_pistas": ("supply", "car", "num_pistas"),
    "cap_bici": ("supply", "bike", "capacidad_pista"),
    "num_estaciones": ("supply", "train", "num_estaciones"),
    "frec_max": ("supply", "train", "frec_max"),
    "cap_tren": ("supply", "train", "capacidad_tren"),
    "tarifa": ("demand", "globales", "costo_tarifa_metro"),
    "parking": ("demand", "globales", "costo_parking"),
    "bencina": ("demand", "globales", "costo_combustible_km"),
    "peaje": ("demand", "globales", "peaje_km"),
    "factor_flota": ("demand", "globales", "factor_flota_auto"),
}


def _compacta(politica: str, umbrales: str):
    c = CITY_PRESETS["Compacta"]
    assert "num_pistas" not in c and "cap_bici" not in c and "poblacion" not in c
    d = base._config_web().model_dump()
    d["city"]["largo_ciudad_km"] = c["largo_ciudad"]
    for k, v in POLICY_PRESETS[politica].items():
        a, b, h = _MAPA_POLITICA[k]
        d[a][b][h] = v
    d["demand"]["globales"]["umbrales"] = umbrales
    lu = base._land_use_web().model_copy(update={"oferta_sigma_frac": c["sigma"]})
    return type(base._config_web()).model_validate(d), lu


def _saltos(serie: np.ndarray, km: np.ndarray) -> dict:
    d = np.abs(np.diff(serie))
    k = int(np.argmax(d))
    return {
        "max": round(float(d[k]), 3),
        "km": round(float(km[k + 1]), 2),
        "paso_mediano": round(float(np.median(d)), 3),
    }


def _perfil_logsum(sim, trace: ConvergenceTrace) -> dict:
    """Lado derecho del CBD, estrato medio, tiempos del estado final: saltos del
    logsum (promedio por tenencia de auto) entre celdas vecinas, y de la
    utilidad del metro sin auto donde cambia la estación asignada (cambia
    `t_tren_viaje`, constante dentro de cada captación; ítem 13)."""
    snap = trace.iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    cbd, dx = ciudad.cbd_index, ciudad.ancho_celda_km
    celdas = range(cbd + 1, sim.city.n_celdas)
    pa = sim.demand.estratos[2].prob_auto
    ls, vm = [], []
    for i in celdas:
        t = TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            bici_libre=float(snap.t_bici_libre[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        lsi = 0.0
        for tiene_auto, w in ((True, pa), (False, 1.0 - pa)):
            u = calcular_utilidades(
                estrato=2,
                celda_origen=i,
                tiene_auto=tiene_auto,
                ciudad=ciudad,
                config=sim.demand,
                tiempos_observados=t,
            )
            lsi += w * float(np.logaddexp.reduce([x.valor for x in u.values() if x.feasible]))
            if not tiene_auto:
                vm.append(u["Metro"].valor if u["Metro"].feasible else np.nan)
        ls.append(lsi)
    km = np.array([(i - cbd) * dx for i in celdas])
    vm = np.asarray(vm)
    tv = np.asarray(snap.t_tren_viaje, dtype=float)[cbd + 1 :]
    cambio = (np.abs(np.diff(tv)) > 1e-9) & ~np.isnan(vm[1:]) & ~np.isnan(vm[:-1])
    dv = np.abs(np.diff(vm))[cambio]
    return {
        "logsum": _saltos(np.asarray(ls), km),
        "metro_cambio_estacion": {
            "limites": int(cambio.sum()),
            "min": round(float(dv.min()), 3),
            "max": round(float(dv.max()), 3),
        },
        "metro_infactible_hasta_km": (
            round(float(km[np.isnan(vm)].max()), 2) if np.isnan(vm).any() else 0.0
        ),
    }


def _q_alto_suelo(sim) -> tuple[np.ndarray, np.ndarray]:
    """Q del estrato alto del uso de suelo solo, con la T de red vacía (lo que
    resuelve la página Uso de suelo, `land_use_solve_from_json`)."""
    L = sim.city.n_celdas
    dx = sim.city.largo_ciudad_km / L
    T = T_flujo_libre(sim.demand, L, L // 2, dx, sim.modos_habilitados, supply=sim.supply)
    city = LandUseCity.build(
        L=L,
        CBD=L // 2,
        cfg=base._land_use_web(),
        ancho_celda_km=dx,
        T=T,
        lambda_h=lambda_desde_demanda(sim.demand),
        rng=np.random.default_rng(42),
    )
    assert city.result is not None and city.result.converged
    km = (np.arange(L) - L // 2) * dx
    return np.asarray(city.result.Q[0], dtype=float), km


def _valle(q: np.ndarray, km: np.ndarray) -> dict | None:
    """Primer mínimo local de Q_alto entre 0,5 y 3 km a la derecha del CBD,
    con el máximo que lo sigue; None si es monótono ahí."""
    idx = np.where((km > 0.5) & (km <= 3.0))[0]
    seg = q[idx]
    for j in range(1, len(seg) - 1):
        if seg[j] < seg[j - 1] and seg[j] < seg[j + 1]:
            k = j + int(np.argmax(seg[j:]))
            return {
                "km_min": round(float(km[idx[j]]), 2),
                "q_min": round(float(seg[j]), 3),
                "km_max": round(float(km[idx[k]]), 2),
                "q_max": round(float(seg[k]), 3),
                "profundidad": round(float(seg[k] - seg[j]), 3),
            }
    return None


def umbrales() -> dict:
    """«escalones» contra «suaves». (a) El reparto de la app con cada una; (b)
    los saltos del logsum y del metro (ítem 13 de la auditoría D); (c) la
    ciudad Compacta con cada política de la galería, con la frecuencia del
    metro para ver dónde actúa Mohring (ítem 17); (d) el valle de Q_alto en el
    suelo con «suaves» y su sensibilidad a `A_DOMINANCIA_METRO` y
    `OMEGA_DOMINANCIA_METRO`, supuestos sin calibrar (ítem 14). Para (d) las
    dos constantes se reemplazan EN MEMORIA en `demand.utility` y se
    restauran; ningún archivo cambia."""
    sim0 = base._config_web()
    out: dict = {"base": {}, "compacta": {}}
    for esp in ("escalones", "suaves"):
        sim = _con_umbrales(sim0, esp)
        fila = {}
        for loc in ("original", "equilibrio"):
            tr = _traza(sim, loc)
            fila[loc] = {"reparto_pct": _reparto(tr), "iteraciones": len(tr.iteraciones)}
            if loc == "original":
                fila["saltos_medio"] = _perfil_logsum(sim, tr)
        out["base"][esp] = fila
    for pol in POLICY_PRESETS:
        if pol == "Personalizado":
            continue
        fila = {}
        for esp in ("escalones", "suaves"):
            sim, lu = _compacta(pol, esp)
            tr = _traza(sim, "original", lu)
            fila[esp] = {
                "metro_pct": _reparto(tr)["Metro"],
                "frecuencia_metro_tph": round(float(tr.iteraciones[-1].frecuencia_metro), 2),
                "convergio": bool(tr.converged),
            }
        fila["delta_metro_pp"] = round(
            fila["suaves"]["metro_pct"] - fila["escalones"]["metro_pct"], 2
        )
        fila["frec_min"] = sim.supply.train.frec_min
        out["compacta"][pol] = fila
    dm = [f["delta_metro_pp"] for f in out["compacta"].values()]
    out["compacta_rango_delta_metro_pp"] = [min(dm), max(dm)]
    out["compacta_largo_km"] = CITY_PRESETS["Compacta"]["largo_ciudad"]

    q, km = _q_alto_suelo(_con_umbrales(sim0, "escalones"))
    out["suelo_escalones_valle"] = _valle(q, km)
    a0, w0 = utility_mod.A_DOMINANCIA_METRO, utility_mod.OMEGA_DOMINANCIA_METRO
    sens = []
    try:
        for a in (1.0, 1.2, 1.5):
            for w in (0.1, 0.25, 1.0):
                utility_mod.A_DOMINANCIA_METRO, utility_mod.OMEGA_DOMINANCIA_METRO = a, w
                q, km = _q_alto_suelo(_con_umbrales(sim0, "suaves"))
                sens.append({"a": a, "omega": w, "valle": _valle(q, km)})
    finally:
        utility_mod.A_DOMINANCIA_METRO, utility_mod.OMEGA_DOMINANCIA_METRO = a0, w0
    out["suelo_suaves_valle"] = next(
        f["valle"] for f in sens if f["a"] == a0 and f["omega"] == w0
    )
    out["suelo_suaves_sensibilidad"] = sens
    out["a_vigente"], out["omega_vigente"] = a0, w0
    return out


def parametros_vigentes() -> dict:
    """Los parámetros de demanda con los que corre la aplicación, tal como
    están en el schema y en `presets.DEFAULT_STRATA`."""
    sim = base._config_web()
    g = sim.demand.globales
    por_estrato = {}
    for h, nombre in ((1, "alto"), (2, "medio"), (3, "bajo")):
        e = sim.demand.estratos[h]
        b = e.betas
        por_estrato[nombre] = {
            "prob_auto": e.prob_auto,
            "prob_teletrabajo": e.prob_teletrabajo,
            "asc_auto": b.asc_auto,
            "asc_metro": b.asc_metro,
            "asc_bici": b.asc_bici,
            "asc_caminata": b.asc_caminata,
            "b_tiempo_viaje": b.b_tiempo_viaje,
            "b_costo": b.b_costo,
            "b_tiempo_espera": b.b_tiempo_espera,
            "b_tiempo_acceso": b.b_tiempo_acceso,
            "b_tiempo_caminata": b.b_tiempo_caminata,
            "penalizaciones": dict(b.penalizaciones_fisicas.model_dump()),
        }
    return {
        "globales": {
            "v_auto": g.v_auto,
            "v_metro": g.v_metro,
            "v_bici": g.v_bici,
            "v_caminata": g.v_caminata,
            "costo_parking": g.costo_parking,
            "costo_combustible_km": g.costo_combustible_km,
            "peaje_km": g.peaje_km,
            "costo_tarifa_metro": g.costo_tarifa_metro,
            "corte_caminata_min": g.corte_caminata_min,
            "corte_bici_min": g.corte_bici_min,
            "teletrabajo_factor": g.teletrabajo_factor,
            "factor_flota_auto": g.factor_flota_auto,
        },
        "iteracion_cero": {"tren_acceso_min": 10.0, "tren_espera_min": 5.0},
        "por_estrato": por_estrato,
    }


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap04.py",
            "configuracion": (
                "Demanda de la aplicación (`presets.DEFAULT_STRATA`, homoscedástica "
                "desde D-33) sobre la ciudad por defecto: 201 celdas, 20 km, "
                "localización «original». Los costos por modo son a flujo libre."
            ),
        },
        "parametros_vigentes": parametros_vigentes(),
        "anatomia": anatomia(),
        "costo_por_modo": costo_por_modo(),
        "factibilidad": factibilidad(),
        "bici_saturada": bici_saturada(),
        "tenencia_por_celda": tenencia_por_celda(),
        "elasticidades": elasticidades(),
        "logit_vs_determinista": logit_vs_determinista(),
        "peaje_y_bienestar": peaje_y_bienestar(),
        "ancla_vot": ancla_vot(),
        "umbrales": umbrales(),
    }
    SALIDA.write_text(json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    a = datos["anatomia"]["medio"]
    print("Pesos relativos (minutos-equivalentes en vehículo), estrato medio:")
    print(
        f"  en vehículo {a['peso_min_en_vehiculo']}  ·  bici {a['peso_min_bici']}  ·  "
        f"caminata {a['peso_min_caminata']}  ·  espera {a['peso_min_espera']}  ·  "
        f"acceso {a['peso_min_acceso']}"
    )
    print(f"  penalización bici acumulada: {a['pen_bici_min']}")
    print(f"  penalización caminata:       {a['pen_caminata_min']}")
    f = datos["factibilidad"]
    print(
        f"\nCortes: caminata {f['corte_caminata_min']} min = {f['umbral_caminata_km']} km "
        f"({f['celdas_sin_caminata_pct']}% de las celdas sin ella)"
    )
    print(
        f"        bici     {f['corte_bici_min']} min = {f['umbral_bici_km']} km "
        f"({f['celdas_sin_bici_pct']}%)"
    )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
