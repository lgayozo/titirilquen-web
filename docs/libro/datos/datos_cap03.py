"""Datos del capítulo 3 — Demanda y elección modal.

Produce `cap03.json`. Todo se mide en **minutos-equivalentes en vehículo**:
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
4. `elasticidades` — respuesta del reparto a la tarifa del metro y al combustible.
5. `logit_vs_determinista` — cuánto cambia el reparto según el método.

Correr desde `packages/titirilquen_core` (~2 min):

    uv run python ../../docs/libro/datos/datos_cap03.py
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
from titirilquen_core.demand.choice import (
    probabilidades_logit,
    probabilidades_todo_o_nada,
)
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.presets import DEFAULT_STRATA

SALIDA = Path(__file__).parent / "cap03.json"
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
            "asc_auto_min": round(
                -(b["asc_auto"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2
            ),
            "asc_bici_min": round(
                -(b["asc_bici"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2
            ),
            "asc_caminata_min": round(
                -(b["asc_caminata"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2
            ),
            # Penalizaciones escalonadas, acumuladas, en minutos-equivalentes.
            "pen_bici_min": {
                ">10": round(abs(pen["bici_10"]) / bt, 2),
                ">20": round(abs(pen["bici_10"] + pen["bici_20"]) / bt, 2),
                ">30": round(
                    abs(pen["bici_10"] + pen["bici_20"] + pen["bici_30"]) / bt, 2
                ),
            },
            "pen_caminata_min": {
                ">5": round(abs(pen["walk_5"]) / bt, 2),
                ">15": round(abs(pen["walk_5"] + pen["walk_15"]) / bt, 2),
                ">25": round(
                    abs(pen["walk_5"] + pen["walk_15"] + pen["walk_25"]) / bt, 2
                ),
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
    ciudad = CiudadLineal(
        n_celdas=cfg.city.n_celdas, largo_total_km=cfg.city.largo_ciudad_km
    )
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
    ciudad = CiudadLineal(
        n_celdas=cfg.city.n_celdas, largo_total_km=cfg.city.largo_ciudad_km
    )
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


def _corre(sim) -> dict:
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, base._land_use_web(), trace, localizacion="original"
    ):
        pass
    s = trace.iteraciones[-1].modal_split
    t = sum(s.values())
    return {m: round(100.0 * v / t, 3) for m, v in s.items()}


def elasticidades() -> dict:
    """Respuesta del reparto a las dos palancas de precio."""
    out = {}
    for campo, valores in (
        ("costo_tarifa_metro", (0, 400, 800, 1200, 1600)),
        ("costo_combustible_km", (60, 120, 240, 480)),
    ):
        filas = []
        for v in valores:
            sim = base._config_web()
            gl = sim.demand.globales.model_copy(update={campo: v})
            dem = sim.demand.model_copy(update={"globales": gl})
            filas.append({campo: v, **_corre(sim.model_copy(update={"demand": dem}))})
        out[campo] = filas
    return out


def logit_vs_determinista() -> dict:
    """El mismo escenario con las dos reglas de elección."""
    out = {}
    for metodo in ("expected", "todo_o_nada"):
        sim = base._config_web()
        out[metodo] = _corre(sim.model_copy(update={"assignment": metodo}))
    # Y en una celda concreta: probabilidades contra el argmax.
    cfg = base._config_web()
    ciudad = CiudadLineal(
        n_celdas=cfg.city.n_celdas, largo_total_km=cfg.city.largo_ciudad_km
    )
    celda = ciudad.cbd_index + int(round(3.0 / ciudad.ancho_celda_km))
    u = _utils(2, celda, ciudad, cfg, True)
    out["celda_a_3km_estrato_medio"] = {
        "logit": {m: round(p, 4) for m, p in probabilidades_logit(u).items()},
        "todo_o_nada": {
            m: round(p, 4) for m, p in probabilidades_todo_o_nada(u).items()
        },
    }
    return out


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap03.py",
            "configuracion": (
                "Demanda de la aplicación (`presets.DEFAULT_STRATA`, homoscedástica "
                "desde D-33) sobre la ciudad por defecto: 201 celdas, 20 km, "
                "localización «original». Los costos por modo son a flujo libre."
            ),
        },
        "anatomia": anatomia(),
        "costo_por_modo": costo_por_modo(),
        "factibilidad": factibilidad(),
        "elasticidades": elasticidades(),
        "logit_vs_determinista": logit_vs_determinista(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

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
