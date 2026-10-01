"""El libro tiene que seguir apuntando a donde dice, y no perder documentos.

`docs/libro/` coteja teoría contra código, y ese cotejo se escribe como punteros
«concepto → archivo:línea». Sirve exactamente en la medida en que sean ciertos, y
son el tipo de dato que se pudre solo: basta un import nuevo arriba de un archivo
para correr veinte números sin que nada falle.

Este test es esa alarma, para TODO el libro y no sólo para el mapa de
arquitectura. Cuando salte, la corrección no es tocar el test: es abrir el HTML y
arreglar el número (el mensaje dice en qué línea quedó el símbolo).

La verificación en sí vive en `tools/verifica_mapa.py`, que también se puede
correr a mano: `uv run python tools/verifica_mapa.py`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from verifica_mapa import LIBRO, documentos, extrae, revisa_libro  # noqa: E402

#: Enlaces del libro que apuntan fuera del repo o a un ancla; no se comprueban.
_EXTERNO = ("http://", "https://", "mailto:", "data:", "#")


@pytest.fixture(scope="module")
def docs() -> list[Path]:
    if not LIBRO.exists():
        pytest.skip(f"no está {LIBRO}")
    encontrados = documentos()
    if not encontrados:
        pytest.skip("el libro todavía no tiene documentos")
    return encontrados


def test_los_punteros_del_libro_son_ciertos(docs: list[Path]) -> None:
    fallos = revisa_libro()
    if not fallos:
        return
    detalle = "\n".join(
        f"  {nombre}:\n" + "\n".join(f"    {p}" for p in problemas)
        for nombre, problemas in fallos.items()
    )
    n = sum(len(v) for v in fallos.values())
    pytest.fail(
        f"{n} punteros de docs/libro/ quedaron obsoletos:\n\n{detalle}\n\n"
        "Arregla los números en el HTML (no este test)."
    )


def test_el_libro_verifica_una_cantidad_razonable(docs: list[Path]) -> None:
    """Guard contra una regresión silenciosa del propio verificador.

    Si alguien rompe los regex de extracción, `revisa` devolvería lista vacía y
    el test de arriba pasaría sin comprobar nada. Este exige que siga habiendo
    punteros que verificar.
    """
    total = 0
    rutas: set[str] = set()
    for doc in docs:
        afirmaciones, rs = extrae(doc.read_text(encoding="utf-8"))
        total += len(afirmaciones)
        rutas |= set(rs)
    assert total > 50, f"sólo {total} punteros en todo el libro: ¿se rompió la extracción?"
    assert len(rutas) > 30, f"sólo {len(rutas)} rutas: ¿se rompió la extracción?"


def test_ningun_enlace_interno_del_libro_esta_roto(docs: list[Path]) -> None:
    """Mover un documento y olvidar un `href` es la forma más fácil de romper el
    libro, y no la detecta el verificador de punteros: eso mira código, esto
    mira navegación."""
    rotos: list[str] = []
    for doc in [*docs, *(LIBRO / n for n in ("index.html",) if (LIBRO / n).exists())]:
        for m in re.finditer(r'(?:href|src)="([^"]+)"', doc.read_text(encoding="utf-8")):
            destino = m.group(1)
            if destino.startswith(_EXTERNO) or not destino:
                continue
            ruta = destino.split("#", 1)[0]
            if ruta and not (doc.parent / ruta).resolve().exists():
                rotos.append(f"{doc.name} → {destino}")
    assert not rotos, "enlaces rotos en el libro:\n" + "\n".join(f"  {r}" for r in rotos)


def test_el_indice_no_deja_documentos_huerfanos(docs: list[Path]) -> None:
    """Todo documento del libro se llega desde el índice.

    Un capítulo que nadie enlaza es un capítulo que nadie lee y que nadie
    actualiza; es como se acumuló el material suelto que el libro vino a
    ordenar.
    """
    indice = LIBRO / "index.html"
    if not indice.exists():
        pytest.skip("todavía no hay índice")
    html = indice.read_text(encoding="utf-8")
    faltan = [d.name for d in docs if f'href="{d.name}"' not in html]
    assert not faltan, (
        "documentos del libro que el índice no enlaza: " + ", ".join(faltan) + "\n"
        "Agrégalos a docs/libro/index.html o explica ahí por qué no van."
    )


# ---------------------------------------------------------------------------
# El pipeline de datos: ningún número del libro se tipea a mano
# ---------------------------------------------------------------------------
#
# Todavía no hay capítulos, así que estos tests no verifican nada; existen
# armados para que el primer capítulo nazca con el contrato puesto en vez de
# agregarlo después, que es cuando ya hay números tipeados que nadie revisa.


def _capitulos() -> list[Path]:
    """Los capítulos propiamente dichos: `capNN-nombre.html`. Los ocho informes
    migrados en sep-2026 no lo son todavía (ver §4 del índice)."""
    return sorted(LIBRO.glob("cap[0-9][0-9]-*.html"))


def test_cada_capitulo_tiene_su_script_y_su_json() -> None:
    """Contrato de `datos/README.md`: capítulo ⇒ `datos_capNN.py` + `capNN.json`."""
    faltan: list[str] = []
    for cap in _capitulos():
        nn = cap.name[3:5]
        for esperado in (f"datos_cap{nn}.py", f"cap{nn}.json"):
            if not (LIBRO / "datos" / esperado).exists():
                faltan.append(f"{cap.name} → falta datos/{esperado}")
    assert not faltan, "capítulos sin su pipeline de datos:\n" + "\n".join(f"  {f}" for f in faltan)


def test_los_datos_declaran_como_se_generaron() -> None:
    """Todo JSON del libro lleva `_meta` con fecha y configuración: un número sin
    procedencia no se puede auditar ni reproducir."""
    import json

    sin_meta = [
        j.name
        for j in sorted((LIBRO / "datos").glob("cap[0-9][0-9].json"))
        if "_meta" not in json.loads(j.read_text(encoding="utf-8"))
    ]
    assert not sin_meta, "JSON del libro sin clave `_meta`: " + ", ".join(sin_meta)
