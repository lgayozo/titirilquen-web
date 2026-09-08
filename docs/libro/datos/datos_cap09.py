"""Datos del capítulo 9 — Calibración: de dónde sale cada número.

Produce `cap09.json`. Los capítulos 1 a 8 etiquetaron los parámetros de cada
módulo; éste los junta todos y pregunta lo que ningún módulo puede contestar
solo: ¿qué fracción del modelo tiene fuente, cuánto sobrevive del simulador
original, y cuáles de esos números mueven de verdad el resultado?

Cinco bloques:

1. `inventario` — cada parámetro del modelo con su etiqueta de origen
   (norma · estimado · heredado · decisión) y su fuente. La etiqueta es una
   clasificación de esta auditoría, declarada en `ORIGEN`, no un dato del
   código: si un parámetro no tiene entrada ahí, el bloque lo dice.
2. `herencia` — los 42 betas contra los del simulador original: qué se
   conservó, qué se reescaló por el factor homoscedástico y qué se reemplazó.
3. `cadena_vot` — la aritmética que une VoT, `b_costo`, `λ` y la norma del SNI.
4. `sensibilidad` — cuánto mueve la línea base cada parámetro al perturbarlo
   un 10 %: el mapa de qué importa y qué es inerte.
5. `presets` — qué toca cada política respecto de la base, y en qué razón.

Necesita el simulador original en `reference/Titirilquen/` (no versionado):

    git clone https://github.com/lehyt2163/Titirilquen.git reference/Titirilquen

Correr desde `packages/titirilquen_core` (~1 min):

    uv run python ../../docs/libro/datos/datos_cap09.py
"""

from __future__ import annotations

import ast
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
from titirilquen_core import constantes
from titirilquen_core.config import SimulationConfig
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import CITY_PRESETS, DEFAULT_STRATA, POLICY_PRESETS

SALIDA = Path(__file__).parent / "cap09.json"
ORIGINAL = RAIZ / "reference" / "Titirilquen" / "app.py"
NOMBRES = {1: "alto", 2: "medio", 3: "bajo"}

#: Las cuatro etiquetas de la plantilla, y una quinta que no es etiqueta sino
#: una advertencia: «sin fuente» marca lo que el propio código declara
#: provisorio o sin origen conocido.
NORMA, ESTIMADO, HEREDADO, DECISION = "norma", "estimado", "heredado", "decisión"

#: Clasificación de esta auditoría (2026-09-08). Clave = ruta del parámetro.
ORIGEN: dict[str, tuple[str, str, bool]] = {
    # ruta: (etiqueta, fuente, sin_fuente)
    "city.n_celdas": (
        DECISION,
        "resolución numérica; 1001 en el núcleo, 201 en la app (cap. 1)",
        False,
    ),
    "city.largo_ciudad_km": (HEREDADO, "original: 20 km", False),
    "city.densidad_hab_km": (
        DECISION,
        "S-03: 1.800 hab/km para que el corredor se congestione",
        False,
    ),
    "city.pendiente_porcentaje": (HEREDADO, "original: 0", False),
    "city.teletrabajo_factor": (HEREDADO, "original: slider 0–2, default 1", False),
    "city.share_estratos": (DECISION, "ago-2026: 20/50/30 (antes 10/40/50)", False),
    "supply.bike.v_media_kmh": (HEREDADO, "original: 14 km/h", False),
    "supply.bike.capacidad_pista": (
        DECISION,
        "2.500 bici/h; S-10 lo marca como calibración de primer orden",
        False,
    ),
    "supply.bike.alpha_bpr": (HEREDADO, "original", False),
    "supply.bike.beta_bpr": (HEREDADO, "original", False),
    "supply.car.v_max_kmh": (HEREDADO, "original: 31 km/h", False),
    "supply.car.ancho_pista_m": (HEREDADO, "Overleaf §oferta", False),
    "supply.car.largo_vehiculo_m": (HEREDADO, "Overleaf §oferta", False),
    "supply.car.gap_m": (HEREDADO, "Overleaf §oferta", False),
    "supply.car.num_pistas": (
        DECISION,
        "2: la rodilla de la BPR en la ciudad base",
        False,
    ),
    "supply.car.alpha_bpr": (HEREDADO, "original: 0,8 (BPR)", False),
    "supply.car.beta_bpr": (HEREDADO, "original: 2 (BPR)", False),
    "supply.car.capacidad_pista": (DECISION, "None ⇒ Greenshields (S-04)", False),
    "supply.train.v_tren_kmh": (HEREDADO, "original: 35 km/h", False),
    "supply.train.capacidad_tren": (
        DECISION,
        "1.000 (original 1.200): zona empinada del Mohring",
        False,
    ),
    "supply.train.num_estaciones": (HEREDADO, "original: 10", False),
    "supply.train.v_caminata_kmh": (HEREDADO, "original: 4,8 km/h", False),
    "supply.train.costo_operacion_tren_km": (
        HEREDADO,
        "PROVISORIO según el propio código",
        True,
    ),
    "supply.train.factor_dia_punta": (
        HEREDADO,
        "PROVISORIO según el propio código",
        True,
    ),
    "supply.train.tiempo_detencion_min": (
        DECISION,
        "30 s por parada; el original no cobraba por detenerse",
        False,
    ),
    "supply.train.frec_min": (DECISION, "D-18: 2 (original 10, hardcodeado)", False),
    "supply.train.frec_max": (DECISION, "D-18: 40 (original 20)", False),
    "supply.train.anden_alpha": (
        HEREDADO,
        "D-16: 0,5 contra 10 del Overleaf; S-09 lo declara abierto",
        True,
    ),
    "supply.train.anden_beta": (
        HEREDADO,
        "D-16: 4 contra 10 del Overleaf; S-09 lo declara abierto",
        True,
    ),
    "demand.globales.v_auto": (HEREDADO, "original: 31", False),
    "demand.globales.v_metro": (HEREDADO, "original: 35", False),
    "demand.globales.v_bici": (HEREDADO, "original: 14", False),
    "demand.globales.v_caminata": (HEREDADO, "original: 4,8", False),
    "demand.globales.corte_caminata_min": (
        DECISION,
        "supuesto del conjunto de elección (constantes.py)",
        False,
    ),
    "demand.globales.corte_bici_min": (
        DECISION,
        "supuesto del conjunto de elección (constantes.py)",
        False,
    ),
    "demand.globales.costo_combustible_km": (HEREDADO, "original: $120/km", False),
    "demand.globales.costo_tarifa_metro": (HEREDADO, "original: $800", False),
    "demand.globales.costo_parking": (
        DECISION,
        "$2.000 (original 6.000): costo ESPERADO, ajustado al VoT",
        False,
    ),
    "demand.globales.factor_flota_auto": (
        DECISION,
        "1,0 = flota de referencia sobre la curva COPERT",
        False,
    ),
    "demand.globales.factor_emision_metro_tren_km": (
        DECISION,
        "2,5 kg/tren-km: continuidad con 0,040 kg/pax·km (D-29)",
        False,
    ),
    "demand.estratos.*.prob_teletrabajo": (
        HEREDADO,
        "original: 0,40 / 0,20 / 0,05",
        False,
    ),
    "demand.estratos.*.prob_auto": (HEREDADO, "original: 0,90 / 0,60 / 0,25", False),
    "demand.estratos.*.betas.asc_auto": (
        DECISION,
        "+20 min sobre el metro, común; NO estimada (ago-2026)",
        False,
    ),
    "demand.estratos.*.betas.asc_metro": (
        DECISION,
        "referencia de las ASC (0 min)",
        False,
    ),
    "demand.estratos.*.betas.asc_bici": (
        DECISION,
        "−18 min, común; NO estimada",
        False,
    ),
    "demand.estratos.*.betas.asc_caminata": (
        DECISION,
        "0 min, común; NO estimada",
        False,
    ),
    "demand.estratos.*.betas.b_tiempo_viaje": (
        DECISION,
        "D-33: 0,0331 común (la escala del medio, heredada)",
        False,
    ),
    "demand.estratos.*.betas.b_costo": (
        DECISION,
        "= b_t·60/VoT con VoT 6.200/3.100/1.600 pedidos; el VoT no tiene fuente escrita",
        True,
    ),
    "demand.estratos.*.betas.b_tiempo_espera": (
        DECISION,
        "2,0 × viaje: centro del rango 1,5–2,5 de la literatura",
        False,
    ),
    "demand.estratos.*.betas.b_tiempo_acceso": (
        NORMA,
        "SNI Precios Sociales 2026, tabla 2.1, ponderador 2",
        False,
    ),
    "demand.estratos.*.betas.b_tiempo_caminata": (
        DECISION,
        "1,7 × viaje: «un juicio, no una norma»",
        False,
    ),
    "demand.estratos.*.betas.penalizaciones_fisicas.*": (
        HEREDADO,
        "original, reescaladas por k; bici_30 del bajo reemplazada",
        False,
    ),
    "max_iter": (DECISION, "20, numérico", False),
    "tolerance": (DECISION, "0,1 min, numérico", False),
    "seed": (DECISION, "42 en la app; None en el núcleo", False),
    "assignment": (DECISION, "expected en la app; montecarlo en el núcleo", False),
    "modos_habilitados": (DECISION, "los cuatro", False),
    "land_use.H_por_estrato": (DECISION, "36.000 × 20/50/30 en la app", False),
    "land_use.estratos.*.y": (
        DECISION,
        "deciles chilenos estilizados (D-27); no mueve la asignación",
        False,
    ),
    "land_use.estratos.*.lambda": (
        NORMA,
        "= |b_costo| de transporte, literal (D-34)",
        False,
    ),
    "land_use.estratos.*.alpha": (
        DECISION,
        "1: el ancla del original recuperada (D-34)",
        False,
    ),
    "land_use.estratos.*.rho": (
        DECISION,
        "50 % del rango de α·T; el propio código: «SIN FUENTE»",
        True,
    ),
    "land_use.beta": (DECISION, "1/√44, aproximación de segundo momento (D-41)", False),
    "land_use.tol": (DECISION, "numérico", False),
    "land_use.max_iter": (DECISION, "numérico", False),
    "land_use.forma": (DECISION, "D-13: oferta determinista por formas", False),
    "land_use.oferta_sigma_frac": (DECISION, "D-13", False),
    "land_use.forma_param": (DECISION, "D-13", False),
    "constantes.CORTE_CAMINATA_MIN": (DECISION, "supuesto del modelo", False),
    "constantes.CORTE_BICI_MIN": (DECISION, "supuesto del modelo", False),
    "constantes.VOT_SOCIAL_CLP_HORA": (
        NORMA,
        "SNI Precios Sociales 2026, tabla 2.1",
        False,
    ),
    "constantes.VIAJES_MES": (DECISION, "2 × 22 días (D-27)", False),
}


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


def _hojas(d, prefijo: str = "") -> list[tuple[str, object]]:
    out = []
    items = d.items() if isinstance(d, dict) else enumerate(d)
    for k, v in items:
        ruta = f"{prefijo}{k}"
        es_rama = isinstance(v, dict) or (
            isinstance(v, (list, tuple)) and v and isinstance(v[0], dict)
        )
        if es_rama:
            out += _hojas(v, ruta + ".")
        else:
            out.append((ruta, v))
    return out


def _etiqueta(ruta: str):
    if ruta in ORIGEN:
        return ORIGEN[ruta]
    # `demand.estratos.1.betas.asc_auto` → `demand.estratos.*.betas.asc_auto`
    generica = re.sub(r"\.\d+\.", ".*.", ruta)
    if generica in ORIGEN:
        return ORIGEN[generica]
    # `…penalizaciones_fisicas.bici_10` → `…penalizaciones_fisicas.*`
    generica2 = re.sub(r"(penalizaciones_fisicas)\.\w+$", r"\1.*", generica)
    if generica2 in ORIGEN:
        return ORIGEN[generica2]
    return None


# ---------------------------------------------------------------------------
# 1. Inventario
# ---------------------------------------------------------------------------


def inventario() -> dict:
    sim = base._config_web()
    lu = base._land_use_web()
    hojas = _hojas(sim.model_dump()) + _hojas(lu.model_dump(by_alias=True), "land_use.")
    hojas += [
        (f"constantes.{n}", getattr(constantes, n))
        for n in (
            "CORTE_CAMINATA_MIN",
            "CORTE_BICI_MIN",
            "VOT_SOCIAL_CLP_HORA",
            "VIAJES_MES",
        )
    ]
    filas, sin_etiqueta = [], []
    for ruta, valor in hojas:
        e = _etiqueta(ruta)
        if e is None:
            sin_etiqueta.append(ruta)
            continue
        etiqueta, fuente, sin_fuente = e
        filas.append(
            {
                "parametro": ruta,
                "valor": valor
                if isinstance(valor, (int, float, str, bool)) or valor is None
                else str(valor),
                "etiqueta": etiqueta,
                "sin_fuente": sin_fuente,
                "fuente": fuente,
            }
        )
    conteo = {
        k: sum(1 for f in filas if f["etiqueta"] == k)
        for k in (NORMA, ESTIMADO, HEREDADO, DECISION)
    }
    # Sin repetir los tres estratos: cada beta cuenta UNA vez como decisión de calibración.
    unicos = {re.sub(r"\.\d+\.", ".*.", f["parametro"]): f["etiqueta"] for f in filas}
    conteo_unicos = {
        k: sum(1 for v in unicos.values() if v == k)
        for k in (NORMA, ESTIMADO, HEREDADO, DECISION)
    }
    return {
        "parametros": len(filas),
        "sin_etiqueta": sin_etiqueta,
        "conteo": conteo,
        "conteo_sin_repetir_estratos": conteo_unicos,
        "parametros_unicos": len(unicos),
        "sin_fuente_declarada": sorted(
            {
                re.sub(r"\.\d+\.", ".*.", f["parametro"])
                for f in filas
                if f["sin_fuente"]
            }
        ),
        "filas": filas,
    }


# ---------------------------------------------------------------------------
# 2. Herencia
# ---------------------------------------------------------------------------


def _betas_originales() -> dict[int, dict]:
    if not ORIGINAL.exists():
        raise SystemExit(
            f"Falta el simulador original en {ORIGINAL.parent}: "
            "git clone https://github.com/lehyt2163/Titirilquen.git reference/Titirilquen"
        )
    src = ORIGINAL.read_text(encoding="utf-8")
    out = {}
    for h in (1, 2, 3):
        m = re.search(
            rf"^\s*{h}:\s*\{{.*?\"betas\":\s*(\{{.*?\}}\s*\}})",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert m, f"estrato {h} no encontrado en el original"
        out[h] = ast.literal_eval(m.group(1))
    return out


def _globales_originales() -> dict:
    src = ORIGINAL.read_text(encoding="utf-8")
    m = re.search(r"\"globales\":\s*(\{.*?\})", src, re.DOTALL)
    assert m
    return ast.literal_eval(m.group(1))


def _politicas_originales() -> dict:
    src = ORIGINAL.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
        r"^\s*\"([^\"]+)\":\s*(\{\"(?:tarifa|num_pistas)\".*?\})\s*,?\s*$",
        src,
        re.MULTILINE,
    ):
        out[m.group(1)] = ast.literal_eval(m.group(2))
    return out


def herencia() -> dict:
    orig = _betas_originales()
    filas = []
    resumen = {"conservado": 0, "reescalado_por_k": 0, "reemplazado": 0}
    for h in (1, 2, 3):
        act = DEFAULT_STRATA[h]["betas"]
        k = 0.0331 / abs(orig[h]["b_tiempo_viaje"])
        # `b_tiempo_acceso` no existía: se desdobló de `b_tiempo_caminata` en
        # ago-2026, así que su antecesor es ese coeficiente.
        pares = [
            (n, orig[h].get(n, orig[h]["b_tiempo_caminata"]), act[n])
            for n in act
            if n != "penalizaciones_fisicas"
        ] + [
            (
                f"pen.{n}",
                orig[h]["penalizaciones_fisicas"][n],
                act["penalizaciones_fisicas"][n],
            )
            for n in act["penalizaciones_fisicas"]
        ]
        for nombre, o, a in pares:
            razon = a / o if o else float("inf")
            if abs(razon - 1.0) < 1e-6:
                clase = "conservado"
            elif abs(razon - k) < 1e-3:
                clase = "reescalado_por_k"
            else:
                clase = "reemplazado"
            resumen[clase] += 1
            filas.append(
                {
                    "estrato": NOMBRES[h],
                    "beta": nombre,
                    "original": o,
                    "actual": a,
                    "razon": round(razon, 4),
                    "clase": clase,
                }
            )
    vot_orig = {
        NOMBRES[h]: round(orig[h]["b_tiempo_viaje"] / orig[h]["b_costo"] * 60, 1)
        for h in (1, 2, 3)
    }
    g = _globales_originales()
    return {
        "k_por_estrato": {
            NOMBRES[h]: round(0.0331 / abs(orig[h]["b_tiempo_viaje"]), 4)
            for h in (1, 2, 3)
        },
        "vot_original_clp_hora": vot_orig,
        "dispersion_vot_original": round(
            max(vot_orig.values()) / min(vot_orig.values()), 2
        ),
        "resumen": resumen,
        "betas_totales": len(filas),
        "reemplazados": [f for f in filas if f["clase"] == "reemplazado"],
        "globales_originales": g,
        "filas": filas,
    }


# ---------------------------------------------------------------------------
# 3. La cadena del VoT
# ---------------------------------------------------------------------------


def cadena_vot() -> dict:
    out = {}
    for h in (1, 2, 3):
        b = DEFAULT_STRATA[h]["betas"]
        bt = abs(b["b_tiempo_viaje"])
        vot = b["b_tiempo_viaje"] / b["b_costo"] * 60
        out[NOMBRES[h]] = {
            "b_tiempo_viaje": b["b_tiempo_viaje"],
            "b_costo": b["b_costo"],
            "vot_clp_hora": round(vot, 2),
            "b_costo_reconstruido": round(bt * 60 / round(vot), 9),
            "lambda_suelo": LandUseConfig().estratos[h - 1].lambda_,
            "lambda_igual_a_b_costo": abs(
                LandUseConfig().estratos[h - 1].lambda_ - abs(b["b_costo"])
            )
            < 1e-12,
            "espera_sobre_viaje": round(abs(b["b_tiempo_espera"]) / bt, 3),
            "acceso_sobre_viaje": round(abs(b["b_tiempo_acceso"]) / bt, 3),
            "caminata_sobre_viaje": round(abs(b["b_tiempo_caminata"]) / bt, 3),
            "asc_auto_min": round(
                -(b["asc_auto"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2
            ),
            "asc_bici_min": round(
                -(b["asc_bici"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2
            ),
            "asc_caminata_min": round(
                -(b["asc_caminata"] - b["asc_metro"]) / b["b_tiempo_viaje"], 2
            ),
        }
    vots = [out[n]["vot_clp_hora"] for n in ("alto", "medio", "bajo")]
    return {
        "por_estrato": out,
        "dispersion_vot": round(max(vots) / min(vots), 4),
        "vot_social_clp_hora": constantes.VOT_SOCIAL_CLP_HORA,
        "vot_social_sobre_medio": round(
            constantes.VOT_SOCIAL_CLP_HORA / out["medio"]["vot_clp_hora"], 4
        ),
    }


# ---------------------------------------------------------------------------
# 4. Sensibilidad
# ---------------------------------------------------------------------------


def _corre(
    sim: SimulationConfig, lu: LandUseConfig, localizacion: str = "original"
) -> dict:
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu, tr, localizacion=localizacion):
        pass
    s = tr.iteraciones[-1].modal_split
    t = sum(s.values())
    n = sum(v for k, v in s.items() if k != "Teletrabajo")
    snap = tr.iteraciones[-1]
    t_medio = float(
        np.sum(snap.demanda_auto * snap.t_auto)
        + np.sum(snap.demanda_bici * snap.t_bici)
    ) / max(n, 1)
    return {
        "reparto": {k: 100.0 * v / t for k, v in s.items()},
        "t_medio_auto_bici": t_medio,
        "emisiones": float(tr.emisiones_total_kg),
    }


def _clave(d: dict, p: str):
    # Tras un viaje por JSON las claves de `estratos` son strings; en el dump
    # de Pydantic son enteros. Se acepta lo que haya.
    return p if p in d else int(p)


def _set(d: dict, ruta: str, valor) -> None:
    partes = ruta.split(".")
    for p in partes[:-1]:
        d = d[_clave(d, p)]
    d[_clave(d, partes[-1]) if partes[-1].isdigit() else partes[-1]] = valor


def _get(d: dict, ruta: str):
    for p in ruta.split("."):
        d = d[_clave(d, p)]
    return d


def sensibilidad() -> dict:
    """Cada parámetro numérico +10 % (enteros: +1; ceros: +1 absoluto), uno a la
    vez, sobre la corrida por defecto de la app. Se reporta el mayor cambio del
    reparto modal en puntos porcentuales, del tiempo medio y de las emisiones."""
    sim = base._config_web()
    lu = base._land_use_web()
    ref = _corre(sim, lu)
    d0 = sim.model_dump()
    saltar = {
        "seed",
        "assignment",
        "modos_habilitados",
        "max_iter",
        "tolerance",
        "city.n_celdas",
        "city.share_estratos",
    }
    filas = []
    for ruta, valor in _hojas(d0):
        if (
            ruta in saltar
            or not isinstance(valor, (int, float))
            or isinstance(valor, bool)
        ):
            continue
        if ruta.startswith("demand.estratos.") and not ruta.startswith(
            "demand.estratos.2."
        ):
            continue  # un solo estrato: las razones internas son las mismas en los tres
        # +10 %; un entero que es un CONTEO (pistas, estaciones) sube 1, y un
        # entero que es una magnitud (tarifa 800, capacidad 2.500) sube 10 %.
        if isinstance(valor, int) and valor <= 20:
            nuevo = valor + 1
        elif isinstance(valor, int):
            nuevo = round(valor * 1.1)
        elif valor == 0:
            nuevo = 1.0
        else:
            nuevo = valor * 1.1
        d = json.loads(json.dumps(d0))
        _set(d, ruta, nuevo)
        try:
            r = _corre(SimulationConfig.model_validate(d), lu)
        except Exception as exc:  # noqa: BLE001
            filas.append(
                {
                    "parametro": ruta,
                    "valor": valor,
                    "perturbado": nuevo,
                    "error": str(exc)[:80],
                }
            )
            continue
        dpp = max(abs(r["reparto"][m] - ref["reparto"][m]) for m in ref["reparto"])
        filas.append(
            {
                "parametro": ruta,
                "valor": valor,
                "perturbado": nuevo,
                "max_delta_pp": round(dpp, 4),
                "delta_t_medio_min": round(
                    r["t_medio_auto_bici"] - ref["t_medio_auto_bici"], 4
                ),
                "delta_emisiones_kg": round(r["emisiones"] - ref["emisiones"], 3),
                "inerte": dpp < 0.005
                and abs(r["t_medio_auto_bici"] - ref["t_medio_auto_bici"]) < 0.005
                and abs(r["emisiones"] - ref["emisiones"]) < 0.05,
            }
        )
    ok = [f for f in filas if "error" not in f]
    ok.sort(key=lambda f: -f["max_delta_pp"])
    # Los parámetros del suelo, sobre la rama que sí los usa.
    ref_eq = _corre(sim, lu, "equilibrio")
    lu0 = lu.model_dump(by_alias=True)
    filas_lu = []
    for ruta in (
        "estratos.1.alpha",
        "estratos.1.rho",
        "estratos.1.lambda",
        "estratos.1.y",
        "beta",
        "oferta_sigma_frac",
        "forma_param",
    ):
        v = _get(lu0, ruta)
        d = json.loads(json.dumps(lu0))
        _set(d, ruta, v * 1.1)
        r = _corre(sim, LandUseConfig.model_validate(d), "equilibrio")
        dpp = max(
            abs(r["reparto"][m] - ref_eq["reparto"][m]) for m in ref_eq["reparto"]
        )
        filas_lu.append(
            {
                "parametro": "land_use." + ruta,
                "valor": v,
                "perturbado": v * 1.1,
                "max_delta_pp": round(dpp, 4),
            }
        )
    return {
        "referencia": {k: round(v, 3) for k, v in ref["reparto"].items()},
        "parametros_probados": len(ok),
        "ranking": ok,
        "inertes": [f["parametro"] for f in ok if f["inerte"]],
        "errores": [f for f in filas if "error" in f],
        "suelo_sobre_rama_equilibrio": filas_lu,
        "nota": (
            "Los betas se perturban sólo en el estrato medio: multiplicar todo un "
            "bloque por k no cambia razones internas (D-33), así que la sensibilidad "
            "a un beta es la sensibilidad a su razón, y ésa es común a los tres."
        ),
    }


# ---------------------------------------------------------------------------
# 5. Presets
# ---------------------------------------------------------------------------


def presets() -> dict:
    basep = POLICY_PRESETS["Base"]
    politicas = {}
    for nombre, p in POLICY_PRESETS.items():
        if nombre in ("Personalizado", "Base"):
            continue
        politicas[nombre] = {
            k: {
                "base": basep[k],
                "valor": v,
                "razon": round(v / basep[k], 3) if basep[k] else None,
            }
            for k, v in p.items()
            if v != basep[k]
        }
    orig = _politicas_originales()
    src = ORIGINAL.read_text(encoding="utf-8")
    m = re.search(r"\{[^{}]*\"largo_ciudad\"[^{}]*\"cap_bici\"[^{}]*\}", src, re.DOTALL)
    defaults_orig = ast.literal_eval(m.group(0)) if m else None
    return {
        "base": dict(basep),
        "politicas": politicas,
        "claves_por_politica": {n: len(v) for n, v in politicas.items()},
        "ciudades": {n: dict(v) for n, v in CITY_PRESETS.items()},
        "original": {"politicas": list(orig), "defaults": defaults_orig},
    }


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap09.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web` y `_land_use_web`), "
                "rama «original» para la sensibilidad de transporte y «equilibrio» "
                "para la del suelo. El original se lee de `reference/Titirilquen/app.py`."
            ),
        },
        "inventario": inventario(),
        "herencia": herencia(),
        "cadena_vot": cadena_vot(),
        "sensibilidad": sensibilidad(),
        "presets": presets(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    i = datos["inventario"]
    print(
        f"Inventario: {i['parametros']} parámetros ({i['parametros_unicos']} sin repetir estratos)"
    )
    print(
        f"  conteo: {i['conteo']}  ·  sin repetir: {i['conteo_sin_repetir_estratos']}"
    )
    print(f"  sin etiqueta: {i['sin_etiqueta']}")
    print(f"  sin fuente declarada: {i['sin_fuente_declarada']}")
    h = datos["herencia"]
    print(
        f"\nHerencia: {h['resumen']} de {h['betas_totales']} betas · k = {h['k_por_estrato']}"
    )
    print(
        f"  VoT original {h['vot_original_clp_hora']} (dispersión {h['dispersion_vot_original']}×)"
    )
    for f in h["reemplazados"]:
        print(
            f"  reemplazado: {f['estrato']:<6} {f['beta']:<18} {f['original']:>10} → {f['actual']:>12} (×{f['razon']})"
        )
    c = datos["cadena_vot"]
    print(
        f"\nVoT: {[c['por_estrato'][n]['vot_clp_hora'] for n in ('alto', 'medio', 'bajo')]} · social {c['vot_social_clp_hora']}"
    )
    s = datos["sensibilidad"]
    print(f"\nSensibilidad ({s['parametros_probados']} parámetros):")
    for f in s["ranking"][:12]:
        print(
            f"  {f['parametro']:<45} {f['valor']:>10} → {f['perturbado']:<12} Δmax {f['max_delta_pp']:>7.3f} pp"
        )
    print(f"  inertes: {s['inertes']}")
    if s["errores"]:
        print(f"  errores: {s['errores']}")
    print(
        "  suelo:",
        [(f["parametro"], f["max_delta_pp"]) for f in s["suelo_sobre_rama_equilibrio"]],
    )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
