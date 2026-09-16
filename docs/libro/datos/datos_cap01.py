"""Datos del capítulo 1 — La ciudad lineal.

Produce `cap01.json`, del que el capítulo transcribe todos sus números. Desde
sep-2026 la ciudad son tres números —`n_celdas` (impar), `largo_ciudad_km` y
`pendiente_porcentaje`— y la población viene SIEMPRE del uso de suelo. La
afirmación que el capítulo sostiene es la de D-28, ahora sin la parte que no se
sostenía: `n_celdas` es resolución numérica y converge, `largo_ciudad_km` y la
población (ΣH) sí mueven el resultado.

Cinco bloques:

1. `geometria` — la ciudad por defecto de la aplicación, celda a celda.
2. `paridad` — las dos convenciones de distancia coinciden con `n` impar, y
   `n` par se rechaza en el schema y en la dataclass (D-45, corregido).
3. `grilla` — refinar la grilla a ciudad física fija: población, reparto modal
   y tiempos, y cómo converge.
4. `poblacion` y `largo` — los dos diales que sí deben mover el resultado.
5. `convenciones` — dónde usa el núcleo la distancia al CBD.

Correr desde `packages/titirilquen_core` (~2 min):

    uv run python ../../docs/libro/datos/datos_cap01.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import numpy as np
from pydantic import ValidationError

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "packages" / "titirilquen_core" / "tests"))

import test_linea_base as base
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import CityConfig, SimulationConfig
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.config import LandUseConfig

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


def _corre(sim: SimulationConfig, lu: LandUseConfig | None = None) -> dict:
    """Una corrida de transporte; devuelve lo que el capítulo compara."""
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, lu or base._land_use_web(), trace, localizacion="original"
    ):
        pass
    split = trace.iteraciones[-1].modal_split
    total = sum(split.values())
    return {
        "agentes": len(trace.agentes),
        "reparto_pct": {m: round(100.0 * v / total, 3) for m, v in split.items()},
        "iteraciones": len(trace.iteraciones),
        "convergio": bool(trace.converged),
        "gap_final_min": round(float(trace.gap_final_min), 4),
        "emisiones_kg_h": round(float(trace.emisiones_total_kg), 1),
    }


def geometria() -> dict:
    """La ciudad por defecto de la aplicación, mirada de cerca."""
    cfg = base._config_web().city
    lu = base._land_use_web()
    c = CiudadLineal(n_celdas=cfg.n_celdas, largo_total_km=cfg.largo_ciudad_km)
    d = np.abs(np.arange(c.n_celdas) - c.cbd_index) * c.ancho_celda_km
    poblacion = int(sum(lu.H_por_estrato))
    return {
        "n_celdas": c.n_celdas,
        "largo_km": c.largo_total_km,
        "pendiente_porcentaje": cfg.pendiente_porcentaje,
        "ancho_celda_km": round(c.ancho_celda_km, 6),
        "ancho_celda_m": round(c.ancho_celda_km * 1000, 2),
        "cbd_index": c.cbd_index,
        "cbd_km": c.cbd_km,
        "centroide_cbd_km": round((c.cbd_index + 0.5) * c.ancho_celda_km, 6),
        "distancia_max_km": round(float(d.max()), 4),
        "poblacion_suelo": poblacion,
        "H_por_estrato": list(lu.H_por_estrato),
        "densidad_media_derivada_hab_km": round(poblacion / c.largo_total_km, 1),
        "core_n_celdas": CityConfig().n_celdas,
        "campos_de_CityConfig": sorted(CityConfig.model_fields),
    }


def paridad() -> dict:
    """Con `n` impar las dos convenciones coinciden; `n` par se rechaza.

    La convención por posición (`|centroide_i − L/2|`) ya no vive en el código
    —se borró con D-45—; acá se reconstruye para medirla contra la del núcleo
    (`|i − n//2|·Δx`) y mostrar por qué el impar es una condición y no un gusto.
    """
    filas = []
    for n in (1001, 401, 201, 101, 51):
        c = CiudadLineal(n_celdas=n, largo_total_km=20.0)
        centroides = (np.arange(n) + 0.5) * c.ancho_celda_km
        por_centroide = np.abs(centroides - c.cbd_km)
        por_indice = np.abs(np.arange(n) - c.cbd_index) * c.ancho_celda_km
        filas.append(
            {
                "n_celdas": n,
                "cbd_index": c.cbd_index,
                "centroide_cbd_km": round(float(centroides[c.cbd_index]), 4),
                "cbd_km": c.cbd_km,
                "desfase_km": round(float(centroides[c.cbd_index] - c.cbd_km), 4),
                "convenciones_coinciden": bool(np.allclose(por_centroide, por_indice)),
            }
        )
    rechazos = []
    for n in (200, 100, 50):
        dx = 20.0 / n
        desfase = (n // 2 + 0.5) * dx - 10.0
        try:
            CityConfig(n_celdas=n)
            schema = "aceptado"
        except ValidationError as e:
            schema = str(e.errors()[0]["msg"])
        try:
            CiudadLineal(n_celdas=n, largo_total_km=20.0)
            clase = "aceptado"
        except ValueError as e:
            clase = str(e)
        rechazos.append(
            {
                "n_celdas": n,
                "desfase_que_tendria_km": round(desfase, 4),
                "desfase_en_celdas": round(desfase / dx, 3),
                "CityConfig": schema,
                "CiudadLineal": clase,
            }
        )
    return {
        "impares": filas,
        "pares": rechazos,
        "schema_exige_impar": True,
        "clase_exige_impar": True,
    }


def barrido_ciudad(dial: str, valores: list) -> list[dict]:
    """Mueve UN dial de la ciudad y deja los otros quietos (población fija)."""
    filas = []
    for v in valores:
        sim = base._config_web()
        ciudad = sim.city.model_copy(update={dial: v})
        filas.append({dial: v, **_corre(sim.model_copy(update={"city": ciudad}))})
    return filas


def barrido_poblacion(totales: list[int]) -> list[dict]:
    """El dial que reemplazó a `densidad_hab_km`: ΣH del uso de suelo, con la
    misma mezcla 20/50/30 y la misma forma de oferta."""
    lu = base._land_use_web()
    H = np.asarray(lu.H_por_estrato, dtype=float)
    shares = H / H.sum()
    filas = []
    for total in totales:
        h = [round(total * s) for s in shares]
        h[1] += total - sum(h)
        lu_t = lu.model_copy(update={"H_por_estrato": (h[0], h[1], h[2])})
        filas.append(
            {
                "poblacion": total,
                "densidad_media_hab_km": round(
                    total / base._config_web().city.largo_ciudad_km
                ),
                **_corre(base._config_web(), lu_t),
            }
        )
    return filas


def main() -> None:
    grilla = barrido_ciudad("n_celdas", [51, 101, 201, 401, 801])
    # Convergencia: cuánto se mueve el reparto entre grillas consecutivas.
    saltos = []
    for a, b in pairwise(grilla):
        saltos.append(
            {
                "de": a["n_celdas"],
                "a": b["n_celdas"],
                "max_delta_pp": round(
                    max(
                        abs(a["reparto_pct"][m] - b["reparto_pct"][m])
                        for m in a["reparto_pct"]
                    ),
                    3,
                ),
            }
        )
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap01.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web` y `_land_use_web`): "
                "201 celdas, 20 km, 36.000 hogares 20/50/30 sobre oferta normal, semilla "
                "42, asignación esperada, tolerancia 0,1. Localización «original» (mezcla "
                "uniforme): el capítulo 1 mira la geometría, no la subasta de suelo."
            ),
        },
        "geometria": geometria(),
        "paridad": paridad(),
        "grilla": grilla,
        "grilla_saltos": saltos,
        "poblacion": barrido_poblacion([18_000, 36_000, 54_000, 72_000]),
        "largo": barrido_ciudad("largo_ciudad_km", [10, 20, 30, 40]),
        "convenciones": {
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
                "estado": "eliminada de `city.py` el 2026-09-10 (D-45); coincide con la "
                "otra si y sólo si n es impar, que ahora es obligatorio",
            },
        },
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    g = datos["geometria"]
    print(
        f"Ciudad por defecto: {g['n_celdas']} celdas · {g['largo_km']} km · "
        f"Δx = {g['ancho_celda_m']} m · CBD en {g['cbd_index']} ({g['cbd_km']} km) · "
        f"{g['poblacion_suelo']} hogares ({g['densidad_media_derivada_hab_km']} hab/km)"
    )
    print("\nGrilla (ciudad física fija):")
    for f in grilla:
        r = f["reparto_pct"]
        print(
            f"  n={f['n_celdas']:>4}  agentes={f['agentes']:>6}  auto={r['Auto']:>6.3f}  "
            f"metro={r['Metro']:>6.3f}  caminata={r['Caminata']:>6.3f}  CO₂={f['emisiones_kg_h']:>8.1f}"
        )
    print("  saltos:", [(s["de"], s["a"], s["max_delta_pp"]) for s in saltos])
    print("\nPoblación:")
    for f in datos["poblacion"]:
        r = f["reparto_pct"]
        print(
            f"  ΣH={f['poblacion']:>6}  auto={r['Auto']:>6.3f}  metro={r['Metro']:>6.3f}  CO₂={f['emisiones_kg_h']:>8.1f}"
        )
    print(
        "\nParidad:",
        [(p["n_celdas"], p["CityConfig"][:40]) for p in datos["paridad"]["pares"]],
    )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
