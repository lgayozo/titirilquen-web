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
3. **Regenerar no debe cambiar nada, salvo `_meta`.** El test corre el script y
   compara **ignorando esa clave**: la fecha y el commit cambian por su cuenta y
   harían fallar el test en cada corrida. Si el resto difiere, el capítulo quedó
   desfasado del código y hay que regenerarlo y declararlo en el commit. Es el
   mismo mecanismo de `sync:core` y los goldens. Verificado para `cap01`: dos
   corridas seguidas dan el mismo JSON salvo `_meta`.
4. **Los JSON no pasan por prettier** (`.prettierignore`): son generados, y
   reformatearlos los deja sucios hasta la próxima corrida.

Correr uno a mano, desde `packages/titirilquen_core`:

```bash
uv run python ../../docs/libro/datos/datos_cap05.py
```

Los scripts importan el núcleo instalado, no una copia: si el modelo cambia, el
número del libro cambia con él o el test avisa.
