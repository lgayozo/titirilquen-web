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

Correr desde `packages/titirilquen_core` (~2 min):

    uv run python ../../docs/libro/datos/datos_cap04.py
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
import titirilquen_core.equilibrium.msa as msa
from titirilquen_core.bienestar import calcular_agregados
from titirilquen_core.city import CiudadLineal
from titirilquen_core.constantes import VOT_SOCIAL_CLP_HORA
from titirilquen_core.demand.choice import (
    probabilidades_logit,
    probabilidades_todo_o_nada,
)
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.presets import DEFAULT_STRATA

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


def _traza(sim) -> ConvergenceTrace:
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, base._land_use_web(), trace, localizacion="original"):
        pass
    return trace


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
    for v in (0, 50, 100, 150, 200, 250, 275, 300, 350, 400, 500, 600):
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
            "Localización «original», tolerancia de la app (0,2 min). Sin "
            "teletrabajo por defecto (oct-2026) el máximo pasó de 150 a 250–300 $/km."
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


def logit_vs_determinista() -> dict:
    """El mismo escenario con las dos reglas de elección."""
    out = {}
    for metodo in ("expected", "todo_o_nada"):
        tr = _traza(base._config_web().model_copy(update={"assignment": metodo}))
        s = tr.iteraciones[-1].modal_split
        out[metodo] = {m: round(100.0 * v / sum(s.values()), 3) for m, v in s.items()}
        # Todo o nada no tiene punto fijo (D9b): su reparto es la última iteración.
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
        "elasticidades": elasticidades(),
        "logit_vs_determinista": logit_vs_determinista(),
        "peaje_y_bienestar": peaje_y_bienestar(),
        "ancla_vot": ancla_vot(),
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
