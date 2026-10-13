"""Datos del capítulo 5 — Equilibrio de transporte.

Produce `cap05.json`. El capítulo tiene que responder tres preguntas incómodas:
si el MSA converge de verdad, si converge al mismo punto por caminos distintos,
y qué tan lejos del punto fijo queda la corrida que la aplicación declara
convergida.

La tercera fue D-39 y la cerró D8 (oct-2026): el residuo medía el cambio del
iterado **amortiguado**, `f·brecha`, y con paso 1/n la tolerancia se aflojaba
sola. Desde D8 el residuo ES la brecha no amortiguada `max |c(x(t)) − t|`, y la
parada la mira a ella.

Diez bloques:

1. `trayectoria` — brecha iteración a iteración, y dónde paraba la regla vieja.
2. `tolerancia` — qué cambia al exigir más: reparto, iteraciones y brecha.
3. `variantes` — promediar tiempos (el default) contra promediar flujos (el
   algoritmo estándar de Boyles, §6.2, el único con argumento de convergencia).
4. `unicidad` — ¿el punto fijo depende del punto de partida?
5. `emisiones` — el reparto entre auto y metro (D-29, tren-km).
6. `downs_thomson` — el barrido de pistas que absorbe el informe homónimo.
7. `bici_umbrales` — D9: cuánto mueve la congestión el tiempo de la bici y
   cuánta demanda cambiaría de escalón si se evaluaran sobre él.
8. `todo_o_nada` — D9: la asignación determinística no tiene punto fijo.
9. `montecarlo` — D8: el ruido de muestreo pone un piso a la brecha.
10. `presets` — D8: si el tope de iteraciones alcanza para los presets de política.

Correr desde `packages/titirilquen_core` (~6 min):

    uv run python ../../docs/libro/datos/datos_cap05.py
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
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo

SALIDA = Path(__file__).parent / "cap05.json"


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


def _corre(sim, *, promediar_flujos: bool = False, localizacion: str = "original"):
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim,
        base._land_use_web(),
        trace,
        localizacion=localizacion,
        promediar_flujos=promediar_flujos,
    ):
        pass
    return trace


def _reparto(trace) -> dict:
    s = trace.iteraciones[-1].modal_split
    t = sum(s.values())
    return {m: round(100.0 * v / t, 3) for m, v in s.items()}


def _resumen(trace) -> dict:
    return {
        "iteraciones": len(trace.iteraciones),
        "convergio": bool(trace.converged),
        "residuo_final_min": round(float(trace.iteraciones[-1].residuo), 5),
        "gap_final_min": round(float(trace.gap_final_min), 5),
        "reparto_pct": _reparto(trace),
        "emisiones_kg_h": round(float(trace.emisiones_total_kg), 1),
    }


def _regla_vieja(trace, tol: float = 0.1) -> int | None:
    """Iteración (contada desde 1, como `len(iteraciones)`) en que la regla
    anterior a D8 —`f·brecha < tol` dos veces seguidas— habría cortado."""
    estables = 0
    for k, s in enumerate(trace.iteraciones):
        if np.isfinite(s.residuo) and s.f_msa * s.residuo < tol:
            estables += 1
            if estables >= 2:
                return k + 1
        else:
            estables = 0
    return None


def trayectoria() -> dict:
    """Brecha iteración a iteración y el cambio amortiguado que medía la regla
    vieja. La serie se corre sin corte hasta `max_iter` para ver dónde habría
    parado cada regla; el resumen es el de la corrida con la regla vigente."""
    sim = base._config_web()
    serie = _corre(sim.model_copy(update={"tolerance": 0.0}))
    vieja = _regla_vieja(serie)
    return {
        "tolerancia": sim.tolerance,
        "brecha_por_iteracion": [
            None if not np.isfinite(s.residuo) else round(float(s.residuo), 5)
            for s in serie.iteraciones
        ],
        "cambio_amortiguado_por_iteracion": [
            None if not np.isfinite(s.residuo) else round(float(s.f_msa * s.residuo), 5)
            for s in serie.iteraciones
        ],
        "paso_msa_por_iteracion": [round(float(s.f_msa), 5) for s in serie.iteraciones],
        "regla_vieja_paraba_en": vieja,
        "brecha_donde_paraba_la_vieja": round(float(serie.iteraciones[vieja - 1].residuo), 5),
        **_resumen(_corre(sim)),
    }


def tolerancia() -> list[dict]:
    """Qué compra exigir más precisión."""
    filas = []
    for tol, max_iter in ((0.5, 100), (0.2, 100), (0.1, 100), (0.05, 100)):
        sim = base._config_web()
        filas.append(
            {
                "tolerancia": tol,
                **_resumen(_corre(sim.model_copy(update={"tolerance": tol, "max_iter": max_iter}))),
            }
        )
    return filas


def variantes() -> dict:
    """Promediar tiempos (default) contra promediar flujos (Boyles §6.2).

    El argumento de convergencia del MSA se apoya en promediar la variable
    PRIMAL —los flujos—: con la carga todo-o-nada, `x* − x` es dirección de
    descenso de la función de Beckmann. Promediando tiempos no hay tal
    argumento. La aplicación usa la segunda.

    Mismo presupuesto para las dos —40 iteraciones, sin corte— y se comparan
    por `gap_final_min`: con promedio de flujos el residuo vuelve a ser un
    cambio amortiguado (los tiempos salen de un flujo que se movió sólo una
    fracción f), así que la regla de parada no las trataría igual.
    """
    sim = base._config_web().model_copy(update={"tolerance": 0.0, "max_iter": 40})
    out = {}
    for nombre, pf in (
        ("promedia_tiempos_default", False),
        ("promedia_flujos_boyles", True),
    ):
        out[nombre] = _resumen(_corre(sim.model_copy(deep=True), promediar_flujos=pf))
    a, b = (
        out["promedia_tiempos_default"]["reparto_pct"],
        out["promedia_flujos_boyles"]["reparto_pct"],
    )
    out["diferencia_maxima_pp"] = round(max(abs(a[m] - b[m]) for m in a), 3)
    return out


def unicidad() -> dict:
    """¿El punto fijo depende de por dónde se entre?

    Se cambia la semilla y el método de asignación de arranque; si el equilibrio
    es único, el reparto final no debería moverse más que el ruido de muestreo.
    """
    sim = base._config_web()
    filas = []
    for semilla in (1, 42, 777):
        filas.append(
            {
                "semilla": semilla,
                **_resumen(_corre(sim.model_copy(update={"seed": semilla}))),
            }
        )
    repartos = [f["reparto_pct"] for f in filas]
    return {
        "por_semilla": filas,
        "dispersion_maxima_pp": round(
            max(max(r[m] for r in repartos) - min(r[m] for r in repartos) for m in repartos[0]),
            4,
        ),
        "nota": (
            "Con `assignment='expected'` la asignación es determinista (flujos "
            "fraccionales), así que la semilla sólo afecta la generación de la "
            "población. Una dispersión nula indica que el punto fijo no depende "
            "del sorteo."
        ),
    }


def emisiones() -> dict:
    """El reparto de CO₂ entre auto y metro (D-29: el metro va por tren-km)."""
    trace = _corre(base._config_web())
    total = float(trace.emisiones_total_kg)
    return {
        "total_kg_h": round(total, 1),
        "auto_kg_h": round(float(trace.emisiones_auto_kg), 1),
        "metro_kg_h": round(float(trace.emisiones_metro_kg), 1),
        "metro_pct_del_total": round(100.0 * float(trace.emisiones_metro_kg) / total, 2)
        if total > 0
        else None,
        "nota": (
            "El metro emite por tren-km circulando (D-29), no por pasajero: su "
            "huella no baja si viaja menos gente, sólo si baja la frecuencia."
        ),
    }


def downs_thomson() -> list[dict]:
    """Barrido de pistas: ¿ampliar la vía mejora el sistema?"""
    filas = []
    for pistas in (1, 2, 3, 4):
        sim = base._config_web()
        car = sim.supply.car.model_copy(update={"num_pistas": pistas})
        sup = sim.supply.model_copy(update={"car": car})
        trace = _corre(sim.model_copy(update={"supply": sup}))
        snap = trace.iteraciones[-1]
        n = sum(snap.modal_split.values()) - snap.modal_split.get("Teletrabajo", 0)
        t_medio = float(
            np.sum(snap.demanda_auto * snap.t_auto) + np.sum(snap.demanda_bici * snap.t_bici)
        ) / max(n, 1)
        filas.append(
            {
                "num_pistas": pistas,
                **_resumen(trace),
                "frecuencia_metro_tph": round(float(snap.frecuencia_metro), 3),
                "t_auto_borde_min": round(float(snap.t_auto[0]), 3),
                "t_medio_auto_bici_min": round(t_medio, 3),
            }
        )
    return filas


_UMBRALES_BICI = (10.0, 20.0, 30.0, 45.0)


def _tramo(t: np.ndarray) -> np.ndarray:
    """Cuántos umbrales de la bici (10/20/30 y el corte de 45) supera cada tiempo."""
    return sum((t > u).astype(int) for u in _UMBRALES_BICI)


def bici_umbrales() -> dict:
    """D9. En el equilibrio de la app: cuánto agrega la congestión al tiempo de
    la bici; qué parte de la demanda de bici quedaría en OTRO escalón (o fuera
    del corte) si se evaluaran sobre el tiempo congestionado, como antes de D9;
    y cuánta está a < 0,5 min de un umbral de ese tiempo, la masa que el mapa
    discontinuo hacía saltar entera."""
    out = {}
    for loc in ("original", "equilibrio"):
        snap = _corre(base._config_web(), localizacion=loc).iteraciones[-1]
        db, tc, tl = snap.demanda_bici, snap.t_bici, snap.t_bici_libre
        tot = float(db.sum())
        cerca = np.zeros(db.shape, dtype=bool)
        for u in _UMBRALES_BICI:
            cerca |= np.abs(tc - u) < 0.5
        out[loc] = {
            "demora_congestion_max_min": round(float(np.max((tc - tl)[db > 0])), 3),
            "demora_congestion_media_min": round(float(np.sum(db * (tc - tl)) / tot), 3),
            "pct_bici_otro_escalon": round(
                100.0 * float(db[_tramo(tc) != _tramo(tl)].sum()) / tot, 2
            ),
            "pct_bici_a_medio_min_de_umbral": round(100.0 * float(db[cerca].sum()) / tot, 2),
        }
    return out


def todo_o_nada() -> dict:
    """D9: la asignación determinística no tiene punto fijo. Sin corte hasta
    20/40/60/80 iteraciones, el reparto y la brecha fresca de cada una; y qué
    hace la regla de parada por defecto."""
    sim = base._config_web().model_copy(update={"assignment": "todo_o_nada"})
    cortes = {}
    for n in (20, 40, 60, 80):
        tr = _corre(sim.model_copy(update={"tolerance": 0.0, "max_iter": n}))
        cortes[str(n)] = {
            "reparto_pct": _reparto(tr),
            "gap_final_min": round(float(tr.gap_final_min), 3),
        }
    repartos = [c["reparto_pct"] for c in cortes.values()]
    return {
        "sin_corte": cortes,
        "oscilacion_max_pp": round(
            max(max(r[m] for r in repartos) - min(r[m] for r in repartos) for m in repartos[0]),
            2,
        ),
        "con_regla_default": _resumen(_corre(sim)),
    }


def montecarlo() -> dict:
    """D8: con 'montecarlo' cada iteración sortea de nuevo y la brecha tiene un
    piso de ruido. Corrida con la regla por defecto, y la brecha de las últimas
    diez iteraciones."""
    tr = _corre(base._config_web().model_copy(update={"assignment": "montecarlo"}))
    return {
        **_resumen(tr),
        "brecha_ultimas_10": [round(float(s.residuo), 3) for s in tr.iteraciones[-10:]],
    }


#: Preset de política → campo de la config. Espejo de `LEE_POLITICA` en
#: `apps/web/src/lib/presets.ts`, que es quien aplica los presets en la app.
_RUTA_PRESET = {
    "num_pistas": ("supply", "car", "num_pistas"),
    "parking": ("demand", "globales", "costo_parking"),
    "bencina": ("demand", "globales", "costo_combustible_km"),
    "peaje": ("demand", "globales", "peaje_km"),
    "factor_flota": ("demand", "globales", "factor_flota_auto"),
    "num_estaciones": ("supply", "train", "num_estaciones"),
    "frec_max": ("supply", "train", "frec_max"),
    "cap_tren": ("supply", "train", "capacidad_tren"),
    "tarifa": ("demand", "globales", "costo_tarifa_metro"),
    "cap_bici": ("supply", "bike", "capacidad_pista"),
}


def presets() -> dict:
    """D8: ¿alcanza el tope de iteraciones para los presets de política?"""
    from titirilquen_core.presets import POLICY_PRESETS

    filas = {}
    for nombre, p in POLICY_PRESETS.items():
        if not p:
            continue
        d = base._config_web().model_dump()
        for campo, valor in p.items():
            a, b, c = _RUTA_PRESET[campo]
            d[a][b][c] = valor
        tr = _corre(type(base._config_web()).model_validate(d))
        filas[nombre] = {
            "iteraciones": len(tr.iteraciones),
            "convergio": bool(tr.converged),
            "gap_final_min": round(float(tr.gap_final_min), 4),
        }
    return filas


def parametros_vigentes() -> dict:
    """Los parámetros del equilibrio con los que corre la aplicación."""
    from titirilquen_core.config import SimulationConfig

    sim = base._config_web()
    return {
        "app": {
            "tolerance_min": sim.tolerance,
            "max_iter": sim.max_iter,
            "assignment": sim.assignment,
            "seed": sim.seed,
            "modos_habilitados": list(sim.modos_habilitados),
            "factor_emision_metro_tren_km": sim.demand.globales.factor_emision_metro_tren_km,
            "factor_flota_auto": sim.demand.globales.factor_flota_auto,
        },
        "nucleo": {
            "tolerance_min": SimulationConfig.model_fields["tolerance"].default,
            "max_iter": SimulationConfig.model_fields["max_iter"].default,
            "assignment": SimulationConfig.model_fields["assignment"].default,
        },
        "promediar_flujos_default": False,
        "curva_emision_auto": {
            "a_g_km": 2467.4,
            "exponente": -0.699,
            "v_min_kmh": 1.0,
            "v_max_kmh": 120.0,
        },
    }


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap05.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web`), localización "
                "«original»: 201 celdas, 20 km, 36.000 hogares, semilla 42, "
                "asignación esperada, tolerancia 0,2 min sobre la brecha no "
                "amortiguada, máximo 40 iteraciones."
            ),
        },
        "parametros_vigentes": parametros_vigentes(),
        "trayectoria": trayectoria(),
        "tolerancia": tolerancia(),
        "variantes": variantes(),
        "unicidad": unicidad(),
        "emisiones": emisiones(),
        "downs_thomson": downs_thomson(),
        "bici_umbrales": bici_umbrales(),
        "todo_o_nada": todo_o_nada(),
        "montecarlo": montecarlo(),
        "presets": presets(),
    }
    SALIDA.write_text(json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    t = datos["trayectoria"]
    print(
        f"Trayectoria: {t['iteraciones']} iter · brecha final {t['residuo_final_min']} · "
        f"gap_final {t['gap_final_min']} min · la regla vieja paraba en "
        f"{t['regla_vieja_paraba_en']} con brecha {t['brecha_donde_paraba_la_vieja']}"
    )
    print("\nTolerancia:")
    for f in datos["tolerancia"]:
        print(
            f"  tol={f['tolerancia']:<6} iter={f['iteraciones']:>3}  residuo={f['residuo_final_min']:>8.5f}  "
            f"brecha={f['gap_final_min']:>8.5f}  auto={f['reparto_pct']['Auto']:.3f}"
        )
    v = datos["variantes"]
    print(f"\nVariantes del MSA (diferencia máxima {v['diferencia_maxima_pp']} pp):")
    for k in ("promedia_tiempos_default", "promedia_flujos_boyles"):
        r = v[k]
        print(
            f"  {k:<26} iter={r['iteraciones']:>3} brecha={r['gap_final_min']:>8.5f} "
            f"auto={r['reparto_pct']['Auto']:.3f} metro={r['reparto_pct']['Metro']:.3f}"
        )
    print(
        f"\nUnicidad: dispersión máxima {datos['unicidad']['dispersion_maxima_pp']} pp entre semillas"
    )
    print("\nDowns-Thomson:")
    for f in datos["downs_thomson"]:
        print(
            f"  {f['num_pistas']} pista(s): auto={f['reparto_pct']['Auto']:>6.2f}  "
            f"metro={f['reparto_pct']['Metro']:>6.2f}  f={f['frecuencia_metro_tph']:>5.2f}  "
            f"CO₂={f['emisiones_kg_h']:>8.1f}"
        )
    print("\nBici (D9):", json.dumps(datos["bici_umbrales"], ensure_ascii=False))
    a = datos["todo_o_nada"]
    print(f"Todo-o-nada: oscila {a['oscilacion_max_pp']} pp;", a["con_regla_default"])
    print("Montecarlo:", datos["montecarlo"])
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
