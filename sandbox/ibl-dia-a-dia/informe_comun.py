"""Andamiaje compartido de los informes del sandbox IBL.

Un informe por experimento: cada uno arma su HTML con estos helpers y el
esqueleto de `pagina()`. El math se emite como `data-tex` y lo convierte a
MathML embebido el paso siguiente:

    node ../../tools/renderiza_ecuaciones.js

que toma por patron todos los `informe*.html` de esta carpeta.
"""

from __future__ import annotations

import re
from pathlib import Path

AQUI = Path(__file__).parent

# --- formato --------------------------------------------------------------------


def num(x: float, n: int = 2) -> str:
    """Coma decimal y signo menos tipografico, como el resto del libro."""
    return f"{x:.{n}f}".replace(".", ",").replace("-", "\u2212")


def pp(x: float, n: int = 1) -> str:
    """Diferencia de cuotas en puntos porcentuales, con signo."""
    v = 100 * x
    s = num(abs(v), n)
    return ("+" if v > 0.05 else "\u2212" if v < -0.05 else "") + s


def ntex(x: float, dec: int) -> str:
    """Numero con coma decimal dentro de TeX.

    KaTeX espacia la coma como puntuacion y `0,198` sale con un hueco en medio;
    `0{,}198` la trata como parte del numero.
    """
    return num(x, dec).replace(",", "{,}")


def _atributo(t: str) -> str:
    """`<` y `>` crudos rompen el atributo y la regex del renderizador."""
    return t.replace("<", r"\lt ").replace(">", r"\gt ")


def tex(t: str) -> str:
    """Matematica en linea, dentro de la prosa."""
    return f'<span class="mat" data-tex="{_atributo(t)}"></span>'


def ec(t: str, n: int | str) -> str:
    """Ecuacion numerada en bloque."""
    return f'<div class="ecuacion" data-tex="{_atributo(t)}" data-id="({n})"></div>'


def linea(archivo: str, simbolo: str) -> str:
    """`archivo:linea` de `def`/`class simbolo` (o de la primera asignacion).

    Se resuelve al armar el informe, asi que la referencia nunca envejece.
    """
    texto = (AQUI / archivo).read_text(encoding="utf-8").splitlines()
    patron = re.compile(rf"^\s*((def|class) {simbolo}\b|{simbolo}\s*=)")
    for i, linea_ in enumerate(texto, 1):
        if patron.match(linea_):
            return f"<code>{archivo}:{i}</code>"
    raise KeyError(f"{simbolo} no esta en {archivo}")


def fig(archivo: str, n: int | str, texto: str) -> str:
    return (
        f'<figure><img src="salida/{archivo}" alt="Figura {n}">'
        f'<figcaption><span class="n">Figura {n}</span>{texto}</figcaption></figure>'
    )


def tabla(n: int | str, nombre: str, cabecera: str, filas: str, explicacion: str) -> str:
    """Tabla con numero y nombre arriba y, abajo, que contiene y como leerla."""
    return (
        f'<p class="titulo-tabla"><span class="n">Tabla {n}</span>{nombre}</p>\n'
        f'<div class="envoltorio-tabla"><table>\n  <thead>{cabecera}</thead>\n'
        f"  <tbody>{filas}</tbody>\n</table></div>\n"
        f'<p class="pie-tabla">{explicacion}</p>'
    )


def sim(t: str) -> str:
    """Simbolo matematico dentro de un encabezado de tabla.

    El CSS del libro pone los `th` en mayusculas, y en matematica eso no es un
    cambio de estilo sino de simbolo: la sigma minuscula pasa a ser la
    sumatoria, y `k` o `s` cambian de identidad. Esto lo apaga.
    """
    return f'<span class="sim">{t}</span>'


def cita(texto: str) -> str:
    """Referencia bibliografica como item de lista."""
    return f"<li>{texto}</li>"


# --- esqueleto ------------------------------------------------------------------

CSS = """
  /* Lo propio de estos informes: figuras y tablas numericas. El resto es libro.css. */
  figure { margin: 22px 0 8px; }
  figure img { width: 100%; display: block; border: 1px solid var(--rule); }
  figcaption {
    font-family: "Segoe UI", system-ui, sans-serif; font-size: 12px; color: var(--muted);
    margin-top: 6px; max-width: 78ch; line-height: 1.5;
  }
  figcaption .n, .titulo-tabla .n {
    font-weight: 700; color: var(--accent); letter-spacing: .1em; text-transform: uppercase;
    margin-right: 8px; font-size: 11px;
  }
  .titulo-tabla {
    font-family: "Segoe UI", system-ui, sans-serif; font-size: 13px; font-weight: 600;
    margin: 22px 0 0; color: var(--ink);
  }
  .pie-tabla { line-height: 1.5; margin-bottom: 14px; }
  /* Ver `sim()`: en un encabezado, pasar un simbolo a mayuscula lo cambia. */
  th .sim { text-transform: none; }
  td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
  @media print { figure { break-inside: avoid; } }
"""


def pagina(*, titulo: str, h1: str, bajada: str, meta: str, indice: str, cuerpo: str) -> str:
    """El HTML completo de un informe."""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<link rel="stylesheet" href="../../docs/libro/libro.css">
<style>{CSS}</style>
</head>
<body>
<div class="pagina">

<header class="portada">
  <div class="kicker">Titirilquen &middot; Side project</div>
  <h1>{h1}</h1>
  <p class="bajada">{bajada}</p>
  <p class="meta">{meta}</p>
</header>

<nav class="indice">
  <ol>
{indice}
  </ol>
</nav>

{cuerpo}

</div>
</body>
</html>
"""
