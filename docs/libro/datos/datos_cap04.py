"""Datos del capítulo 4 — Equilibrio de transporte.

Produce `cap04.json`. El capítulo tiene que responder tres preguntas incómodas:
si el MSA converge de verdad, si converge al mismo punto por caminos distintos,
y qué tan lejos del punto fijo queda la corrida que la aplicación declara
convergida.

La tercera es D-39: el residuo mide el cambio del iterado **amortiguado**, y con
paso 1/n subestima el desajuste real. Desde sep-2026 el núcleo publica además
`gap_final_min`, la brecha no amortiguada, y este capítulo la usa como vara.

Seis bloques:

1. `trayectoria` — residuo y brecha iteración a iteración.
2. `tolerancia` — qué cambia al exigir más: reparto, iteraciones y brecha.
3. `variantes` — promediar tiempos (el default) contra promediar flujos (el
   algoritmo estándar de Boyles, §6.2, el único con argumento de convergencia).
4. `unicidad` — ¿el punto fijo depende del punto de partida?
5. `emisiones` — el reparto entre auto y metro (D-29, tren-km).
6. `downs_thomson` — el barrido de pistas que absorbe el informe homónimo.

Correr desde `packages/titirilquen_core` (~4 min):

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
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo

SALIDA = Path(__file__).parent / "cap04.json"


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


def trayectoria() -> dict:
    """Residuo iteración a iteración, con la brecha final como vara."""
    trace = _corre(base._config_web())
    return {
        "tolerancia": base._config_web().tolerance,
        "residuo_por_iteracion": [
            None if not np.isfinite(s.residuo) else round(float(s.residuo), 5)
            for s in trace.iteraciones
        ],
        "paso_msa_por_iteracion": [round(float(s.f_msa), 5) for s in trace.iteraciones],
        **_resumen(trace),
        "razon_gap_sobre_residuo": round(
            float(trace.gap_final_min / trace.iteraciones[-1].residuo), 2
        ),
    }


def tolerancia() -> list[dict]:
    """Qué compra exigir más precisión."""
    filas = []
    for tol, max_iter in ((0.5, 100), (0.1, 100), (0.01, 100), (0.001, 100)):
        sim = base._config_web()
        filas.append(
            {
                "tolerancia": tol,
                **_resumen(
                    _corre(
                        sim.model_copy(update={"tolerance": tol, "max_iter": max_iter})
                    )
                ),
            }
        )
    return filas


def variantes() -> dict:
    """Promediar tiempos (default) contra promediar flujos (Boyles §6.2).

    El argumento de convergencia del MSA se apoya en promediar la variable
    PRIMAL —los flujos—: con la carga todo-o-nada, `x* − x` es dirección de
    descenso de la función de Beckmann. Promediando tiempos no hay tal
    argumento. La aplicación usa la segunda.
    """
    sim = base._config_web()
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
            max(
                max(r[m] for r in repartos) - min(r[m] for r in repartos)
                for m in repartos[0]
            ),
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
            np.sum(snap.demanda_auto * snap.t_auto)
            + np.sum(snap.demanda_bici * snap.t_bici)
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


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap04.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web`), localización "
                "«original»: 201 celdas, 20 km, 36.000 hogares, semilla 42, "
                "asignación esperada, tolerancia 0,1, máximo 20 iteraciones."
            ),
        },
        "trayectoria": trayectoria(),
        "tolerancia": tolerancia(),
        "variantes": variantes(),
        "unicidad": unicidad(),
        "emisiones": emisiones(),
        "downs_thomson": downs_thomson(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    t = datos["trayectoria"]
    print(
        f"Trayectoria: {t['iteraciones']} iter · residuo final {t['residuo_final_min']} · "
        f"brecha {t['gap_final_min']} min  (×{t['razon_gap_sobre_residuo']})"
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
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
