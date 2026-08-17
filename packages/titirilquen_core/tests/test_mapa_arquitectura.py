"""El mapa de arquitectura tiene que seguir apuntando a donde dice.

`docs/arquitectura.html` es el índice «concepto → archivo:línea» del repositorio:
sirve exactamente en la medida en que sus punteros sean ciertos. Y son el tipo de
dato que se pudre solo — basta un import nuevo arriba de un archivo para correr
veinte números— sin que nada falle.

Este test es esa alarma. Cuando salte, la corrección no es tocar el test: es
abrir el HTML y arreglar el número (el mensaje dice en qué línea quedó el
símbolo).

La verificación en sí vive en `tools/verifica_mapa.py`, que también se puede
correr a mano: `uv run python tools/verifica_mapa.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from verifica_mapa import MAPA, extrae, revisa  # noqa: E402


@pytest.fixture(scope="module")
def html() -> str:
    if not MAPA.exists():
        pytest.skip(f"no está {MAPA}")
    return MAPA.read_text(encoding="utf-8")


def test_los_punteros_del_mapa_son_ciertos(html: str) -> None:
    problemas = revisa(html)
    assert not problemas, (
        f"{len(problemas)} punteros de docs/arquitectura.html quedaron obsoletos:\n\n"
        + "\n".join(f"  {p}" for p in problemas)
        + "\n\nArregla los números en el HTML (no este test)."
    )


def test_el_mapa_verifica_una_cantidad_razonable(html: str) -> None:
    """Guard contra una regresión silenciosa del propio verificador.

    Si alguien rompe los regex de extracción, `revisa` devolvería lista vacía y
    el test de arriba pasaría sin comprobar nada. Este exige que siga habiendo
    punteros que verificar.
    """
    afirmaciones, rutas = extrae(html)
    assert len(afirmaciones) > 50, f"sólo {len(afirmaciones)} punteros: ¿se rompió la extracción?"
    assert len(set(rutas)) > 30, f"sólo {len(set(rutas))} rutas: ¿se rompió la extracción?"
