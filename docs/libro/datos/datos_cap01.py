"""Datos del capítulo 1 — La ciudad lineal.

Produce `cap01.json`, del que el capítulo transcribe todos sus números. La
afirmación que el capítulo tiene que sostener es la de D-28: los tres diales de
la ciudad son **ortogonales**, o sea que `n_celdas` es resolución pura y no
mueve nada económico, mientras `densidad_hab_km` y `largo_ciudad_km` sí.

Cinco bloques:

1. `geometria` — la ciudad por defecto de la aplicación, celda a celda.
2. `paridad` — qué pasa con `n_celdas` par: el CBD deja de estar en el centro de
   su celda y las dos convenciones de distancia del repositorio se separan.
3. `grilla` — refinar la grilla a ciudad física fija: población, reparto modal y
   tiempos. Es la invariancia que D-26/D-28 prometen.
4. `densidad` y `largo` — los otros dos diales, que sí deben mover el resultado.
5. `convenciones` — dónde usa el núcleo cada forma de medir la distancia al CBD.

Correr desde `packages/titirilquen_core` (~2 min):

    uv run python ../../docs/libro/datos/datos_cap01.py
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
from titirilquen_core.config import CityConfig, SimulationConfig
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    iter_msa_desde_suelo,
)

SALIDA = Path(__file__).parent / "cap01.json"


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 — el JSON se genera igual sin git
        return "desconocido"


def _corre(sim: SimulationConfig, localizacion: str = "original") -> dict:
    """Una corrida de transporte; devuelve lo que el capítulo compara."""
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, base._land_use_web(), trace, localizacion=localizacion
    ):
        pass
    split = trace.iteraciones[-1].modal_split
    total = sum(split.values())
    agg = trace.agentes
    return {
        "agentes": len(agg),
        "reparto_pct": {m: round(100.0 * v / total, 3) for m, v in split.items()},
        "iteraciones": len(trace.iteraciones),
        "convergio": bool(trace.converged),
        "gap_final_min": round(float(trace.gap_final_min), 4),
        "emisiones_kg_h": round(float(trace.emisiones_total_kg), 1),
    }


def geometria() -> dict:
    """La ciudad por defecto de la aplicación, mirada de cerca."""
    cfg = base._config_web().city
    c = CiudadLineal(n_celdas=cfg.n_celdas, largo_total_km=cfg.largo_ciudad_km)
    d = c.distancia_al_cbd_km()
    return {
        "n_celdas": c.n_celdas,
        "largo_km": c.largo_total_km,
        "ancho_celda_km": round(c.ancho_celda_km, 6),
        "ancho_celda_m": round(c.ancho_celda_km * 1000, 2),
        "cbd_index": c.cbd_index,
        "cbd_km": c.cbd_km,
        "centroide_cbd_km": round(float(c.centroides_km()[c.cbd_index]), 6),
        "distancia_max_km": round(float(d.max()), 4),
        "densidad_hab_km": cfg.densidad_hab_km,
        "poblacion": round(cfg.densidad_hab_km * cfg.largo_ciudad_km),
        "share_estratos": list(cfg.share_estratos),
        "core_n_celdas": CityConfig().n_celdas,
        "core_densidad_hab_km": CityConfig().densidad_hab_km,
    }


def paridad() -> dict:
    """`n_celdas` par: el CBD deja de estar donde el modelo cree que está.

    `city.py` mide la distancia entre centroides (`|centroide_i − L/2|`); el
    resto del núcleo la mide entre índices (`|i − n//2|·Δx`). Con `n` impar son
    idénticas; con `n` par se separan medio `Δx`.
    """
    filas = []
    for n in (1001, 401, 201, 101, 51, 200, 100, 50):
        c = CiudadLineal(n_celdas=n, largo_total_km=20.0)
        por_centroide = c.distancia_al_cbd_km()
        por_indice = np.abs(np.arange(n) - c.cbd_index) * c.ancho_celda_km
        filas.append(
            {
                "n_celdas": n,
                "impar": n % 2 == 1,
                "cbd_index": c.cbd_index,
                "centroide_cbd_km": round(float(c.centroides_km()[c.cbd_index]), 4),
                "cbd_km": c.cbd_km,
                "desfase_km": round(
                    float(c.centroides_km()[c.cbd_index] - c.cbd_km), 4
                ),
                "desfase_en_celdas": round(
                    float(c.centroides_km()[c.cbd_index] - c.cbd_km) / c.ancho_celda_km,
                    3,
                ),
                "convenciones_coinciden": bool(np.allclose(por_centroide, por_indice)),
                "distancia_del_cbd_a_si_mismo_km": round(
                    float(por_centroide[c.cbd_index]), 4
                ),
            }
        )
    return {
        "filas": filas,
        "schema_exige_impar": False,  # CityConfig sólo pide ge=11 (ver §6 del capítulo)
        "ui_fuerza_impar": True,  # CityBuilder.tsx: v % 2 === 0 ? v + 1 : v
    }


def barrido(dial: str, valores: list) -> list[dict]:
    """Mueve UN dial de la ciudad y deja los otros dos quietos."""
    filas = []
    for v in valores:
        sim = base._config_web()
        ciudad = sim.city.model_copy(update={dial: v})
        filas.append({dial: v, **_corre(sim.model_copy(update={"city": ciudad}))})
    return filas


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap01.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web`): 201 celdas, "
                "20 km, 1.800 hab/km, semilla 42, asignación esperada, tolerancia 0,1. "
                "Localización «original» (mezcla uniforme): el capítulo 1 mira la "
                "geometría, no la subasta de suelo."
            ),
        },
        "geometria": geometria(),
        "paridad": paridad(),
        "grilla": barrido("n_celdas", [51, 101, 201, 401, 801]),
        "densidad": barrido("densidad_hab_km", [900, 1800, 2700, 3600]),
        "largo": barrido("largo_ciudad_km", [10, 20, 30, 40]),
        "convenciones": {
            # Corregido 2026-09-07 (auditoría del cap. 2): `supply/` recibe
            # `cbd_km` pero lo reconvierte a índice con int(cbd_km/L·n), que es
            # ⌊n/2⌋ para todo n. No es una convención aparte.
            "por_indice": {
                "formula": "|i − n//2| · Δx",
                "usos": [
                    "demand/utility.py",
                    "equilibrium/msa.py",
                    "land_use/accesibilidad.py",
                    "supply/car.py (tras reconvertir cbd_km a índice)",
                ],
            },
            "por_posicion": {
                "formula": "|x_i − L/2|, con x_i el centroide",
                "usos": [],
                "expuesta_en": [
                    "CiudadLineal.centroides_km",
                    "CiudadLineal.distancia_al_cbd_km",
                ],
            },
        },
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    g = datos["geometria"]
    print(
        f"Ciudad por defecto: {g['n_celdas']} celdas · {g['largo_km']} km · "
        f"Δx = {g['ancho_celda_m']} m · CBD en {g['cbd_index']} ({g['cbd_km']} km)"
    )
    print("\nGrilla (ciudad física fija — debería no mover nada):")
    for f in datos["grilla"]:
        r = f["reparto_pct"]
        print(
            f"  L={f['n_celdas']:>4}  agentes={f['agentes']:>6}  "
            f"auto={r['Auto']:>6.3f}  metro={r['Metro']:>6.3f}  CO₂={f['emisiones_kg_h']:>8.1f}"
        )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
