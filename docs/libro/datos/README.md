# Los datos del libro

Ningún número del libro se tipea a mano. Cada capítulo tiene aquí su script y su
JSON, y el HTML transcribe desde el JSON:

```
datos_capNN.py   genera capNN.json (y las figuras del capítulo, si tiene)
capNN.json       los números que el capítulo muestra
```

El contrato, que fija `tests/test_libro.py`:

1. **Todo capítulo `capNN-*.html` tiene su `datos_capNN.py` y su `capNN.json`.**
   Si un capítulo no necesita datos calculados —es raro, pero puede pasar en los
   transversales— lo declara con un `capNN.json` que contenga `{"sin_datos":
   "por qué"}`.
2. **El JSON dice cuándo y con qué se generó.** Toda salida lleva una clave
   `_meta` con la fecha, el commit y la configuración usada.
3. **Regenerar no debe cambiar nada.** El test corre el script y compara; si el
   diff no está vacío, el capítulo quedó desfasado del código y hay que
   regenerarlo y declararlo en el commit. Es el mismo mecanismo de `sync:core` y
   los goldens.

Correr uno a mano, desde `packages/titirilquen_core`:

```bash
uv run python ../../docs/libro/datos/datos_cap05.py
```

Los scripts importan el núcleo instalado, no una copia: si el modelo cambia, el
número del libro cambia con él o el test avisa.
