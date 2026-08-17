"""Verifica que `docs/arquitectura.html` siga apuntando a donde dice.

El mapa de arquitectura es un índice de «concepto → archivo:línea». Su utilidad
depende por completo de que esos punteros sean ciertos, y son justo el tipo de
dato que envejece sin que nadie lo note: basta que alguien agregue un import
arriba para que veinte números queden corridos. El propio documento lo admitía
en el pie («los números de línea envejecen»), que es otra forma de decir que
nadie los estaba verificando.

Esto lo verifica. Lee el HTML, extrae cada afirmación de la forma
«el símbolo X está en el archivo A, línea N» y comprueba que sea verdad.

Dos formas de afirmación, ambas en el índice maestro (§1):

    <td class="ruta py">demand/choice.py</td><td class="n">44</td>
    <td><code>probabilidades_todo_o_nada</code> — argmax sobre …</td>
                    ↑ el primer <code> de las notas es el símbolo de esa fila

    <td><code>iter_msa</code> · <code>run_msa</code> (519)</td>
                                                     ↑ afirmación secundaria:
                                                       el símbolo anterior, en
                                                       la línea entre paréntesis

Uso directo:  uv run python tools/verifica_mapa.py
Y como test:  tests/test_mapa_arquitectura.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MAPA = RAIZ / "docs" / "arquitectura.html"

NUCLEO = RAIZ / "packages" / "titirilquen_core" / "src" / "titirilquen_core"
WEB = RAIZ / "apps" / "web" / "src"


@dataclass(frozen=True)
class Afirmacion:
    """«El símbolo vive en ruta:linea», tal como lo dice el documento."""

    ruta: str
    linea: int
    simbolo: str


def resuelve(ruta: str) -> Path:
    """Las rutas del documento son relativas a su capa, no al repo.

    El índice mezcla tres orígenes: `demand/choice.py` cuelga del núcleo,
    `lib/api.ts` de `apps/web/src`, y unas pocas (`docs/…`, `CLAUDE.md`) del
    repo. Se prueba primero la raíz porque es la única sin ambigüedad.
    """
    for base in (RAIZ, NUCLEO, WEB):
        if (base / ruta).exists():
            return base / ruta
    return (NUCLEO if ruta.endswith(".py") else WEB) / ruta


# Una fila del índice: … <td class="ruta X">RUTA</td><td class="n">LÍNEA</td><td>NOTAS</td>
_FILA = re.compile(
    r'<td class="ruta[^"]*">(?P<ruta>[^<]+)</td>'
    r'\s*<td class="n">(?P<linea>[^<]*)</td>'
    r"\s*<td>(?P<notas>.*?)</td>",
    re.DOTALL,
)
# En las notas: <code>simbolo</code>, opcionalmente seguido de «(123)».
_CODIGO = re.compile(r"<code>(?P<simbolo>[A-Za-z_][\w.]*)</code>(?:\s*\((?P<linea>\d+)\))?")

# Fuera del índice, las rutas aparecen sueltas dentro de celdas: en el flujo de
# la §7 («config.py:314 → city.py:15») y en la tabla de la frontera. Ahí no hay
# símbolo que comprobar, pero sí se puede exigir que el archivo EXISTA: es
# justamente lo que falló cuando la cirugía borró api/serialization.py.
#
# Sólo se verifican los tokens que llevan «/», es decir los que son una ruta de
# verdad. El documento también usa nombres pelados como `train.py` o
# `SandboxPage.tsx` cuando el contexto ya dice dónde viven: eso es prosa, y
# exigirle ruta completa haría ilegible la tabla de rutas.
_CELDA_RUTA = re.compile(r'<(?:td|span) class="ruta[^"]*">(?P<contenido>[^<]+)</(?:td|span)>')
_TOKEN_RUTA = re.compile(r"[\w.@/_-]*/[\w.@/_-]*\.(?:tsx|ts|py)(?![\w])|[\w.@/_-]+/(?![\w])")


def extrae(html: str) -> tuple[list[Afirmacion], list[str]]:
    """Devuelve las afirmaciones verificables y las rutas sin número de línea."""
    afirmaciones: list[Afirmacion] = []
    rutas: list[str] = []

    for fila in _FILA.finditer(html):
        ruta = fila.group("ruta").strip()
        rutas.append(ruta)
        codigos = list(_CODIGO.finditer(fila.group("notas")))
        if not codigos:
            continue

        # Afirmación principal: la columna «Lín.» se refiere al primer símbolo.
        principal = fila.group("linea").strip()
        if principal.isdigit():
            afirmaciones.append(Afirmacion(ruta, int(principal), codigos[0]["simbolo"]))

        # Secundarias: «<code>run_msa</code> (519)».
        for c in codigos:
            if c["linea"]:
                afirmaciones.append(Afirmacion(ruta, int(c["linea"]), c["simbolo"]))

    return afirmaciones, rutas


def rutas_sueltas(html: str) -> list[str]:
    """Rutas mencionadas fuera del índice, sin símbolo asociado."""
    encontradas: list[str] = []
    for celda in _CELDA_RUTA.finditer(html):
        for tok in _TOKEN_RUTA.finditer(celda.group("contenido")):
            encontradas.append(tok.group(0))
    return list(dict.fromkeys(encontradas))


def revisa(html: str) -> list[str]:
    """Lista de problemas. Vacía = el mapa dice la verdad."""
    problemas: list[str] = []
    afirmaciones, rutas = extrae(html)

    for ruta in dict.fromkeys([*rutas, *rutas_sueltas(html)]):
        destino = resuelve(ruta)
        if not destino.exists():
            problemas.append(f"{ruta} — no existe")

    for a in afirmaciones:
        destino = resuelve(a.ruta)
        if not destino.exists():
            continue  # ya reportado arriba
        lineas = destino.read_text(encoding="utf-8").splitlines()
        if a.linea > len(lineas):
            problemas.append(
                f"{a.ruta}:{a.linea} — el archivo tiene {len(lineas)} líneas "
                f"(se esperaba «{a.simbolo}»)"
            )
            continue
        if a.simbolo not in lineas[a.linea - 1]:
            donde = [
                str(n)
                for n, txt in enumerate(lineas, 1)
                if re.search(
                    rf"\b(?:def|class|const|function|interface|type)\s+{re.escape(a.simbolo)}\b",
                    txt,
                )
            ]
            pista = f" — está en {', '.join(donde)}" if donde else " — no aparece en el archivo"
            problemas.append(f"{a.ruta}:{a.linea} — no dice «{a.simbolo}»{pista}")

    return problemas


def main() -> int:
    problemas = revisa(MAPA.read_text(encoding="utf-8"))
    if not problemas:
        afirmaciones, rutas = extrae(MAPA.read_text(encoding="utf-8"))
        print(
            f"docs/arquitectura.html al día: {len(afirmaciones)} punteros "
            f"y {len(set(rutas))} rutas verificados."
        )
        return 0
    print(f"docs/arquitectura.html tiene {len(problemas)} punteros rotos:\n")
    for p in problemas:
        print(f"  {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
