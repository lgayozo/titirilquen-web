"""Los punteros del «saber más» de la tabla de agregados apuntan a algo real.

Cada métrica de `ReferenceComparison.tsx` declara dónde se calcula, como
`{ archivo, simbolo }`. Es la misma idea que los punteros del libro, pero sin
número de línea: `tools/verifica_mapa.py` sólo recorre `docs/libro/*.html`, así
que una línea escrita en el frontend se correría en silencio con la primera
edición del núcleo. El nombre del símbolo no se corre — pero sí puede
desaparecer en un refactor, y entonces la interfaz mandaría al lector a buscar
algo que ya no existe. Eso es lo que este test impide.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
TABLA = RAIZ / "apps" / "web" / "src" / "components" / "viz" / "ReferenceComparison.tsx"
NUCLEO = Path(__file__).resolve().parents[1] / "src" / "titirilquen_core"

#: `fuente: { archivo: "bienestar.py", simbolo: "cg_percibido" }`. La coma
#: final es opcional: prettier parte en varias líneas los punteros largos y
#: entonces la agrega. Sin contemplarla, dos punteros quedaban fuera del test
#: SIN QUE NADA LO DIJERA — el modo de falla más caro de un verificador.
PUNTERO = re.compile(
    r'fuente:\s*\{\s*archivo:\s*"([^"]+)"\s*,\s*simbolo:\s*"([^"]+)"\s*,?\s*\}',
)
#: Cuántos hay que encontrar, contados de forma independiente del regex.
DECLARADOS = re.compile(r"fuente:\s*\{")


def _fuente() -> str:
    if not TABLA.exists():  # pragma: no cover - sólo si alguien mueve el archivo
        pytest.skip(f"no está {TABLA}")
    return TABLA.read_text(encoding="utf-8")


def punteros() -> list[tuple[str, str]]:
    return PUNTERO.findall(_fuente())


def test_se_verifican_todos_los_punteros_declarados() -> None:
    """El regex tiene que capturar TODOS, no «suficientes».

    Un umbral suelto («al menos diez») deja pasar que el formateador cambie la
    forma del literal y el verificador empiece a revisar de menos, en verde.
    """
    texto = _fuente()
    assert len(punteros()) == len(DECLARADOS.findall(texto)), (
        "hay punteros declarados que el regex no está capturando: se estarían "
        "verificando de menos sin que ningún test falle"
    )
    assert len(punteros()) >= 10, "esperaba un puntero por métrica de la tabla"


@pytest.mark.parametrize("archivo,simbolo", punteros())
def test_el_simbolo_existe_en_el_archivo(archivo: str, simbolo: str) -> None:
    ruta = NUCLEO / archivo
    assert ruta.exists(), f"{archivo} no existe en el núcleo"
    texto = ruta.read_text(encoding="utf-8")
    # Como asignación, como def, o como clave del dict de salida.
    patron = re.compile(
        rf'(^\s*(def\s+)?{re.escape(simbolo)}\b)|(^\s*"{re.escape(simbolo)}"\s*:)',
        re.MULTILINE,
    )
    assert patron.search(texto), (
        f"la tabla manda a «{archivo} · {simbolo}» y ahí no hay ningún "
        f"símbolo con ese nombre. Si lo renombraste, actualizá el puntero en "
        f"ReferenceComparison.tsx."
    )
