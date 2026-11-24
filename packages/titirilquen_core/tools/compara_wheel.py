"""¿Dos wheels tienen el mismo CONTENIDO?

    python tools/compara_wheel.py viejo.whl nuevo.whl

Sale con 0 si los dos empaquetan los mismos archivos con los mismos bytes, y
con 1 —listando qué difiere— si no.

Existe para el job «Contrato generado al día» del CI, que regenera el wheel de
Pyodide y exige que sea el que está commiteado. Compararlos byte a byte no
sirve: un wheel es un zip, y el mismo código empaquetado en Windows y en Linux
difiere en los metadatos del contenedor (sistema de origen, permisos), aunque
adentro sea idéntico. Con esa comparación el job quedó en rojo cada vez que el
wheel se construyó en Windows (sep a nov de 2026), sin que hubiera nada
desactualizado.

Se ignoran dos archivos de `*.dist-info/` que dependen de la herramienta y no
del código: `WHEEL` (nombra al generador y su versión) y `RECORD` (los hashes
de los demás, que por lo mismo también cambia).
"""

from __future__ import annotations

import sys
import zipfile

IGNORADOS = ("WHEEL", "RECORD")


def contenido(ruta: str) -> dict[str, bytes]:
    with zipfile.ZipFile(ruta) as z:
        return {
            n: z.read(n)
            for n in z.namelist()
            if not (".dist-info/" in n and n.rsplit("/", 1)[-1] in IGNORADOS)
        }


def diferencias(a: dict[str, bytes], b: dict[str, bytes]) -> list[str]:
    out = [f"sólo en el commiteado: {n}" for n in sorted(a.keys() - b.keys())]
    out += [f"sólo en el regenerado: {n}" for n in sorted(b.keys() - a.keys())]
    out += [f"distinto: {n}" for n in sorted(a.keys() & b.keys()) if a[n] != b[n]]
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    difs = diferencias(contenido(sys.argv[1]), contenido(sys.argv[2]))
    for d in difs:
        print(d)
    return 1 if difs else 0


if __name__ == "__main__":
    sys.exit(main())
