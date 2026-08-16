"""Genera el contrato TypeScript desde el núcleo Python.

    uv run python tools/genera_contrato.py

Emite `apps/web/src/lib/gen/*.gen.ts` a partir de los modelos Pydantic, los
`TypedDict` de `serializacion.py` y los datos de `presets.py` / `constantes.py`.
Esos archivos NO se editan a mano.

Por qué existe
--------------
El frontend necesita conocer la forma de la configuración, sus valores por
defecto y los presets. Hasta agosto de 2026 todo eso estaba transcrito a mano
en `types.ts`, `defaults.ts` y `presets.ts` — unos 130 valores y 14 interfaces
copiadas de Python. Un test de contrato cubría una parte (city, supply,
globales, sim, land_use) y dejaba fuera la más grande: los 42 coeficientes del
logit, que determinan la elección modal y podían desincronizarse sin que nada
avisara.

Generarlo elimina la clase entera de bug: no hay dos fuentes que puedan
divergir, hay una que se proyecta.

Lo que NO resuelve
------------------
Sólo mueve DATOS y FORMAS. La lógica duplicada en TypeScript —`utility.ts`
(la función de utilidad) y `citySupply.ts` (la oferta de vivienda)— sigue
siendo una reimplementación a mano, y se protege con fixtures golden, no con
esto.

Divergencias intencionales
--------------------------
El frontend usa a propósito algunos valores distintos del core (una grilla más
liviana, semilla fija, `expected` en vez de `montecarlo`). Antes vivían como
una lista de excepciones dentro del test de contrato; ahora viven en
`apps/web/src/lib/overrides.ts`, escrito a mano y con el porqué de cada una.
Este generador emite los defaults del CORE tal cual; el override se aplica
encima, a la vista.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from titirilquen_core import constantes
from titirilquen_core.bienestar import AgregadosDict
from titirilquen_core.config import SimulationConfig
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import (
    CITY_PRESETS,
    DEFAULT_STRATA,
    POLICY_PRESETS,
    CityPreset,
    PolicyPreset,
)
from titirilquen_core.serializacion import (
    AgenteDict,
    CoupledResultDict,
    LandUseResultDict,
    LandUseSolveDict,
    OuterIterationDict,
    SnapshotDict,
    TraceDict,
)

RAIZ = Path(__file__).resolve().parents[3]
DESTINO = RAIZ / "apps" / "web" / "src" / "lib" / "gen"

CABECERA = """// GENERADO por packages/titirilquen_core/tools/genera_contrato.py — NO EDITAR.
// Para cambiar algo de acá, cambiá el núcleo Python y corré `npm run sync:core`.
"""

#: Campos cuyo tipo de clave no sobrevive a JSON Schema (`dict[int, X]` pierde
#: que la clave es un `StratumId`). Se restituye a mano, por nombre de campo.
CLAVES_TIPADAS: dict[str, str] = {"estratos": "StratumId"}


# ---------------------------------------------------------------------------
# JSON Schema -> TypeScript
# ---------------------------------------------------------------------------


def _jsdoc(descripcion: str | None, sangria: str = "  ") -> str:
    if not descripcion:
        return ""
    limpio = " ".join(descripcion.split())
    if len(limpio) <= 76:
        return f"{sangria}/** {limpio} */\n"
    palabras, lineas, actual = limpio.split(" "), [], ""
    for w in palabras:
        if len(actual) + len(w) + 1 > 74:
            lineas.append(actual)
            actual = w
        else:
            actual = f"{actual} {w}".strip()
    lineas.append(actual)
    cuerpo = "\n".join(f"{sangria} *  {ln}" for ln in lineas)
    return f"{sangria}/**\n{cuerpo}\n{sangria} */\n"


def _tipo_ts(esquema: dict[str, Any], campo: str = "") -> str:
    """Traduce un nodo de JSON Schema al tipo TypeScript equivalente."""
    if "$ref" in esquema:
        return esquema["$ref"].rsplit("/", 1)[-1]

    if "anyOf" in esquema:  # `X | None` y uniones en general
        partes = [_tipo_ts(v, campo) for v in esquema["anyOf"]]
        return " | ".join(dict.fromkeys(partes))

    if "enum" in esquema:  # Literal[...]
        return " | ".join(json.dumps(v) for v in esquema["enum"])

    tipo = esquema.get("type")
    if tipo == "array":
        if "prefixItems" in esquema:  # tuple[...] de largo fijo
            return "[" + ", ".join(_tipo_ts(v, campo) for v in esquema["prefixItems"]) + "]"
        interno = _tipo_ts(esquema.get("items", {}), campo)
        # Una unión seguida de `[]` necesita paréntesis: sin ellos TypeScript
        # lee `"A" | "B"[]` como `"A" | ("B"[])`, que no es lo mismo.
        if " | " in interno:
            interno = f"({interno})"
        return f"{interno}[]"
    if tipo == "object":
        extra = esquema.get("additionalProperties")
        if isinstance(extra, dict):
            clave = CLAVES_TIPADAS.get(campo, "string")
            return f"Record<{clave}, {_tipo_ts(extra, campo)}>"
        return "Record<string, unknown>"
    return {
        "string": "string",
        "number": "number",
        "integer": "number",
        "boolean": "boolean",
        "null": "null",
    }.get(tipo, "unknown")


def _interfaz(nombre: str, esquema: dict[str, Any]) -> str:
    """Emite la interfaz con TODOS los campos requeridos.

    No es un descuido. En Pydantic un campo con default es opcional *al
    construir*, pero del lado TypeScript estos tipos describen una
    configuración YA COMPLETA: la que vive en el store, la que se serializa a
    `.ttrq.json` y la que se le manda al núcleo, siempre armada a partir de
    `DEFAULTS_CORE`, que es un `model_dump()` con todos los campos presentes.

    Marcarlos opcionales obligaría a los consumidores a chequear `undefined` en
    valores que nunca faltan, y taparía un caso real de dato ausente si alguna
    vez ocurriera. Lo que sí se propaga es `null` — ahí el tipo sale `X | null`,
    porque eso sí puede llegar (`seed`, `capacidad_pista`).
    """
    lineas = [_jsdoc(esquema.get("description"), ""), f"export interface {nombre} {{\n"]
    for campo, sub in esquema.get("properties", {}).items():
        lineas.append(_jsdoc(sub.get("description")))
        lineas.append(f"  {campo}: {_tipo_ts(sub, campo)};\n")
    lineas.append("}\n")
    return "".join(lineas)


def emite_tipos() -> str:
    partes = [
        CABECERA,
        "\n/** Los tres estratos socioeconómicos. */\n",
        "export type StratumId = 1 | 2 | 3;\n",
    ]
    vistos: set[str] = set()
    for modelo in (SimulationConfig, LandUseConfig):
        esquema = modelo.model_json_schema(by_alias=True)
        for nombre, sub in esquema.get("$defs", {}).items():
            if nombre not in vistos:
                vistos.add(nombre)
                partes.append("\n" + _interfaz(nombre, sub))
        raiz = {k: v for k, v in esquema.items() if k != "$defs"}
        partes.append("\n" + _interfaz(modelo.__name__, raiz))
    return "".join(partes)


# ---------------------------------------------------------------------------
# TypedDict -> TypeScript (la forma de SALIDA; los dataclasses no son Pydantic)
# ---------------------------------------------------------------------------

_PRIMITIVAS = {int: "number", float: "number", str: "string", bool: "boolean", type(None): "null"}


def _tipo_desde_anotacion(anot: Any) -> str:
    """Anotación de Python a tipo TypeScript.

    Usa `typing.get_origin`/`get_args` y no `__origin__` a mano: la
    representación de `X | Y` cambió entre versiones de Python (en 3.14 es
    `typing.Union`, antes `types.UnionType`) y sólo la API pública es estable
    en las dos.
    """
    if anot is Any:
        return "unknown"
    if anot in _PRIMITIVAS:
        return _PRIMITIVAS[anot]

    origen, args = get_origin(anot), get_args(anot)
    if origen is Literal:
        return " | ".join(json.dumps(a) for a in args)
    if origen is Union or origen is UnionType:
        return " | ".join(dict.fromkeys(_tipo_desde_anotacion(a) for a in args))
    if origen in (list, tuple):
        interno = _tipo_desde_anotacion(args[0])
        return f"({interno})[]" if " | " in interno else f"{interno}[]"
    if origen is dict:
        return f"Record<{_tipo_desde_anotacion(args[0])}, {_tipo_desde_anotacion(args[1])}>"
    if hasattr(anot, "__annotations__"):  # otro TypedDict
        return anot.__name__
    return "unknown"


def emite_trace() -> str:
    partes = [
        CABECERA,
        "\n// La forma de los resultados que el núcleo entrega al frontend, sea por\n"
        "// HTTP (FastAPI) o por postMessage (worker de Pyodide). Fuente: los\n"
        "// TypedDict de titirilquen_core/serializacion.py.\n",
    ]
    for td in (
        AgenteDict,
        AgregadosDict,
        SnapshotDict,
        TraceDict,
        LandUseResultDict,
        LandUseSolveDict,
        OuterIterationDict,
        CoupledResultDict,
    ):
        doc = (td.__doc__ or "").strip().split("\n")[0]
        partes.append("\n" + _jsdoc(doc, ""))
        partes.append(f"export interface {td.__name__} {{\n")
        for campo, anot in get_type_hints(td).items():
            partes.append(f"  {campo}: {_tipo_desde_anotacion(anot)};\n")
        partes.append("}\n")
    return "".join(partes)


# ---------------------------------------------------------------------------
# Datos: defaults, presets, constantes
# ---------------------------------------------------------------------------


def _literal(valor: Any, sangria: int = 0) -> str:
    return json.dumps(valor, ensure_ascii=False, indent=2)


def emite_defaults() -> str:
    # `SimulationConfig` no es construible sin `demand`: la calibración de los
    # estratos no vive en el schema sino en `presets.py::DEFAULT_STRATA`. Se
    # arma con ella, que es exactamente lo que corre la aplicación.
    base = SimulationConfig(demand={"estratos": DEFAULT_STRATA})  # type: ignore[arg-type]
    return (
        CABECERA
        + "\nimport type { SimulationConfig, LandUseConfig } from './tipos.gen';\n"
        + "\n/** Defaults del NÚCLEO. El frontend aplica encima sus divergencias\n"
        + " *  intencionales — ver `lib/overrides.ts`. */\n"
        + f"export const DEFAULTS_CORE: SimulationConfig = {_literal(base.model_dump(by_alias=True))} as const;\n"
        + f"\nexport const DEFAULTS_LAND_USE_CORE: LandUseConfig = {_literal(LandUseConfig().model_dump(by_alias=True))} as const;\n"
        + "\n/** Calibración vigente de los tres estratos (los 42 coeficientes del\n"
        + " *  logit). Era la mayor duplicación a mano del repo y la única sin test\n"
        + " *  de contrato. */\n"
        + f"export const ESTRATOS_CALIBRADOS = {_literal(DEFAULT_STRATA)} as const;\n"
    )


def _interfaz_typeddict(td: Any, nombre: str, doc: str) -> str:
    """Un `TypedDict` como interfaz TS. Las claves de un `total=False` salen
    opcionales, que es justo lo que son los presets: cada uno declara sólo los
    parámetros que toca."""
    opcionales = getattr(td, "__optional_keys__", frozenset())
    partes = [_jsdoc(doc, ""), f"export interface {nombre} {{\n"]
    for campo, anot in get_type_hints(td).items():
        marca = "?" if campo in opcionales else ""
        partes.append(f"  {campo}{marca}: {_tipo_desde_anotacion(anot)};\n")
    partes.append("}\n")
    return "".join(partes)


def emite_presets() -> str:
    return (
        CABECERA
        + "\n/** Presets de ciudad y de política. Declaran valores ABSOLUTOS, no\n"
        + " *  diferencias contra el default: al recalibrar hay que moverlos, o\n"
        + " *  aplicar una política revierte ese parámetro en silencio. */\n"
        + "\n"
        + _interfaz_typeddict(CityPreset, "CityPresetValues", "Parámetros de forma urbana.")
        + "\n"
        + _interfaz_typeddict(PolicyPreset, "PolicyPresetValues", "Parámetros de política.")
        + f"\nexport const CITY_PRESETS: Record<string, CityPresetValues> = {_literal(CITY_PRESETS)};\n"
        + f"\nexport const POLICY_PRESETS: Record<string, PolicyPresetValues> = {_literal(POLICY_PRESETS)};\n"
        + "\nexport type CityPresetName = keyof typeof CITY_PRESETS;\n"
        + "export type PolicyPresetName = keyof typeof POLICY_PRESETS;\n"
    )


def emite_constantes() -> str:
    version = _version_del_core()
    return (
        CABECERA
        + "\n/** Orden canónico de los modos: define el orden de las series en toda\n"
        + " *  figura y el layout del cubo `demanda_estrato`. */\n"
        + f"export const MODOS = {_literal(list(constantes.MODOS))} as const;\n"
        + f"\nexport const MODOS_CON_TELETRABAJO = {_literal(list(constantes.MODOS_CON_TELETRABAJO))} as const;\n"
        + "\n/** Sobre estos tiempos el modo deja de ser una alternativa considerada\n"
        + " *  (min). Son supuestos del modelo de elección, no parámetros. */\n"
        + f"export const CORTE_CAMINATA_MIN = {constantes.CORTE_CAMINATA_MIN};\n"
        + f"export const CORTE_BICI_MIN = {constantes.CORTE_BICI_MIN};\n"
        + "\n/** Valor social del tiempo ($/hora-pasajero), Precios Sociales del SNI.\n"
        + " *  Se actualiza cada año. */\n"
        + f"export const VOT_SOCIAL_CLP_HORA = {constantes.VOT_SOCIAL_CLP_HORA};\n"
        + "\n/** Nombre del wheel que el worker de Pyodide instala. Cambia con la\n"
        + " *  versión del core; tenerlo acá evita que quede hardcodeado y viejo. */\n"
        + f'export const WHEEL_FILENAME = "titirilquen_core-{version}-py3-none-any.whl";\n'
    )


def _version_del_core() -> str:
    texto = (RAIZ / "packages" / "titirilquen_core" / "pyproject.toml").read_text(encoding="utf-8")
    for linea in texto.splitlines():
        if linea.startswith("version = "):
            return linea.split('"')[1]
    raise RuntimeError("no se encontró `version` en pyproject.toml del core")


# ---------------------------------------------------------------------------


ARCHIVOS = {
    "tipos.gen.ts": emite_tipos,
    "trace.gen.ts": emite_trace,
    "defaults.gen.ts": emite_defaults,
    "presets.gen.ts": emite_presets,
    "constantes.gen.ts": emite_constantes,
}


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, generador in ARCHIVOS.items():
        (DESTINO / nombre).write_text(generador(), encoding="utf-8")
        print(f"  {nombre}")
    # Prettier deja los generados con el mismo estilo que el resto del repo, así
    # que un `git diff` sobre ellos muestra cambios de contenido y no de formato.
    try:
        subprocess.run(
            ["npx", "prettier", "--write", str(DESTINO)],
            cwd=RAIZ,
            check=True,
            capture_output=True,
        )
        print("  (formateados con prettier)")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  AVISO: no se pudo correr prettier ({e}); los archivos quedan sin formatear")
    print(f"\nContrato generado en {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
