# Verificación del módulo Transporte — análisis crítico

> Experimento de verificación del núcleo `titirilquen_core` (oferta · demanda ·
> equilibrio MSA), el mismo motor que corre la página **Transporte** vía Pyodide.
> Fecha: 2026-06-04. Reproducible con `scripts/` ad-hoc (ver §Metodología).

## Metodología

Se ejercita `run_msa` directamente en Python (idéntico a lo que ejecuta el
navegador) para poder leer resultados completos y barrer parámetros de a uno.

- **Baseline**: ciudad lineal `L=20 km`, `N=101` celdas, densidad `80 hab/celda`
  (≈8.000 viajeros), estratos `10/40/50`, betas `DEFAULT_STRATA`, oferta por
  defecto. Asignación `expected` (determinista), `max_iter=20`, `tolerance=0.05`,
  `seed=1`.
- **Escenarios**: 3 presets de ciudad, 7 presets de política, y barridos
  univariados de parking, bencina, tarifa, nº de pistas, nº de estaciones,
  `frec_max`, capacidad de ciclovía, largo, densidad, pendiente, y habilitación
  de modos (10 barridos · ~45 corridas).
- **Métricas**: reparto modal %, tiempo medio por modo, frecuencia de metro,
  CO₂, y convergencia (residual / iteraciones / flag).

## Veredicto general

El modelo es **cualitativamente coherente**: 9 de 9 relaciones causales
esperadas tienen el signo correcto y son monótonas. No se observaron valores
absurdos ni NaN espurios. **Pero** hay **cuatro hallazgos** que conviene
conocer: tres parámetros/mecanismos quedan **inertes** en el rango de uso normal
(no son bugs de código, sino de calibración / régimen de operación) y un punto
de **no-convergencia** acotado.

---

## ✅ Lo que funciona y tiene sentido

| Relación esperada | Resultado | OK |
|---|---|---|
| ↑ parking ⇒ ↓ auto | auto 27,3 → 4,0 % (parking 0 → 25k) | ✓ monótono |
| ↑ tarifa metro ⇒ ↓ metro | metro 59,7 → 47,4 % (0 → 2000), pasa a bici/caminata | ✓ |
| ↑ nº estaciones ⇒ ↑ metro | acceso 29,8 → 17,8 min ⇒ metro 49 → 56 % | ✓ |
| ↑ capacidad ciclovía ⇒ ↑ bici | bici 12,5 → 28,4 % (cap 200 → 6000) | ✓ |
| ↑ largo ciudad ⇒ ↓ bici/caminata, ↑ metro | caminata 20,5 → 4,3 %; metro 40 → 65 % | ✓ |
| ↑ densidad ⇒ ↑ congestión, ↑ CO₂ | CO₂ 474 → 9.152 kg/h (d 20 → 300) | ✓ |
| ↑ pendiente ⇒ ↓ bici | bici 23,2 → 19,4 % (0 → 15 %) | ✓ |
| Sensibilidad al costo por ingreso | `b_costo`: alto −0,00008 < medio −0,0002 < bajo −0,0006 | ✓ (pobre más elástico) |
| Deshabilitar un modo redistribuye | sin Auto ⇒ metro 65,7 %, CO₂ a la mitad | ✓ |

El CO₂ escala correctamente con volumen de autos, densidad y largo; el reparto
por defecto (metro ≈ 54 %, auto ≈ 14 %) es razonable para una ciudad
monocéntrica con buen transporte público y tenencia de auto limitada por estrato.

---

## ⚠ Hallazgos críticos

### H1 — La frecuencia del metro está clavada en `f_min`; `frec_max` es un parámetro muerto

`f_op = clip(L_max / cap_tren, f_min, f_max)`. Para superar `f_min=6` hace falta
una carga pico `L_max > f_min·cap_tren = 6·1200 = 7.200 pax/h`. En la práctica:

| Escenario | carga pico | f_op |
|---|---|---|
| baseline | 1.780 | 6,0 |
| TP gratis | 1.934 | 6,0 |
| densidad 150 | 3.571 | 6,0 |
| densidad 300 | 7.926 | **6,6** |
| densidad 500 | 13.909 | 11,6 |

**Consecuencias:**
- El barrido de `frec_max` (6 → 50) da resultados **idénticos** bit a bit: el
  slider "frecuencia máxima" no hace **nada** en escenarios normales (para llegar
  a `f_max=30` haría falta carga pico 36.000).
- La espera del metro queda **constante en ~5 min** (`30/6`) sin importar política
  ni demanda. El **efecto Möhring** y la paradoja de Downs-Thomson no pueden
  emerger (consistente con la nota D-18 de `DISCREPANCIES.md`, aquí cuantificada).
- El preset **"Máx Metro"** (frec_max=50) sub-rinde: solo mejora por estaciones y
  tarifa, no por frecuencia (metro 58,8 % vs 54,5 % baseline).

**Causa raíz:** calibración. La capacidad piso (`f_min·cap_tren = 7.200`) supera
con creces la demanda de cualquier escenario realista. **No es un bug**; el modelo
hace lo que dice. Pero es engañoso para enseñanza.

### H2 — El precio de la bencina es casi inerte; el parking domina

Un 5× en bencina (50 → 250) mueve el auto solo 14,5 → 13,2 %. Motivo: la
población que maneja está dominada por el estrato alto (90 % con auto) cuyo
`b_costo=-0,00008`. La utilidad del auto se mueve así para un viaje de 5 km:

| Estrato | ΔV por bencina (50→250) | ΔV por parking (6.000, fijo) |
|---|---|---|
| 1 (alto) | −0,02 → −0,10 | **−0,48** |
| 2 (medio) | −0,05 → −0,25 | −1,20 |
| 3 (bajo) | −0,15 → −0,75 | −3,60 |

El parking (costo **fijo**, no escala con distancia) es **10–50× más potente por
peso** que la bencina. Implica que la palanca "bencina"/vehículos híbridos
(Pro-Auto bencina=100 vs Híbridos bencina=65) casi no se distingue en resultados.
Es **económicamente defendible** (quien maneja es rico e insensible al costo
marginal) pero deja un parámetro de la UI prácticamente sin efecto.

### H3 — El nº de pistas casi no afecta: el auto nunca se congestiona

En el equilibrio por defecto el auto satura poco la vía:

| Escenario | v/c pico auto |
|---|---|
| baseline (2 pistas) | 0,11 |
| 1 pista | 0,44 |
| parking=0 (2 pistas) | 0,21 |
| parking=0 & 1 pista | 0,83 |

Con auto al 14 % de reparto, 2 pistas están a 1/9 de su capacidad ⇒ pasar de 2 a
4 pistas no cambia nada. La palanca "pistas" solo importa cuando el auto es
masivo **y** las pistas son pocas (p. ej. parking=0 + 1 pista). Coherente, pero
significa que el lever de infraestructura vial es débil salvo en políticas
pro-auto extremas.

### H4 — No-convergencia en escenarios con ciclovía saturada

Con `max_iter=20`, `tolerance=0.05`, 3 escenarios **no convergen** (residual se
estanca en ~0,048–0,050):

- `cap_bici=200` (ciclovía mínima),
- `densidad=300` (demanda enorme sobre ciclovía de cap fija),
- `sin Metro` (la demanda del modo dominante se vuelca a la bici).

Todos comparten **bici saturada**: la BPR de la bici con su piso de caminata
oscila bajo carga alta y el MSA con paso `1/(it+1)` no termina de cerrar en 20
iteraciones. **Mitigación práctica:** subir `max_iter` o `tolerance`; **de fondo:**
revisar la estabilidad de la oferta de bici bajo saturación. El resto (≈42 de 45
corridas) converge sin problemas, varias en 3–9 iteraciones.

---

## 🔎 Caveat de interpretación (no es error)

Los **tiempos medios por modo** pueden moverse de forma contra-intuitiva por
**efecto de composición**: al subir la pendiente, el tiempo medio de la bici
*baja* (22,8 → 19,5 min) no porque la bici sea más rápida, sino porque solo
quedan ciclistas de viajes cortos (los largos desertan). Vale tenerlo presente al
leer los KPIs de tiempo medio en la UI.

---

## Recomendaciones

1. **Frecuencia (H1):** si se quiere que el metro tenga dinámica observable
   (frecuencia, espera, Möhring), recalibrar para bajar el umbral de activación
   — p. ej. `cap_tren` menor o `f_min` menor — de modo que la demanda típica
   caiga dentro del rango `[f_min·K, f_max·K]`. Alternativamente, marcar en la UI
   que `frec_max` solo actúa bajo alta demanda.
2. **Bencina (H2):** decisión de modelado. Si se busca que la palanca de
   combustible sea didáctica, revisar `b_costo` del estrato alto o hacer el costo
   de auto más sensible a distancia.
3. **Convergencia (H4):** considerar subir `max_iter` por defecto, o reforzar la
   estabilidad de `supply/bike.py` bajo saturación, para que escenarios extremos
   no queden marcados como "no convergió".
4. **UI:** una nota o tooltip aclarando que `frec_max` y `nº de pistas` solo
   muerden bajo alta demanda evitaría la sensación de "el slider no hace nada".

## Conclusión

El módulo Transporte **es correcto en su lógica**: las direcciones causales, los
órdenes de magnitud y las emisiones son sensatos y reproducibles. Los problemas
detectados son de **calibración/régimen** (tres palancas inertes en el rango
usable) y un punto acotado de no-convergencia, no de implementación. Ninguno
invalida los resultados; sí conviene conocerlos para no sobre-interpretar la UI.

---

## Resolución (2026-06-04)

Tras el análisis se decidió y aplicó:

- **H1 (frecuencia) — ARREGLADO en el modelo.** Se recalibró `capacidad_tren` de
  `1200` → **`300`** (default en `config.py`/`defaults.ts` y presets ×¼:
  1200→300, 1000→250), llevando el tren a la escala de demanda del modelo. Con
  ello la frecuencia es responsiva (`f≈7,6`, espera ~4 min vs. 5 fija), `frec_max`
  pasa a tener efecto, y el **efecto Mohring** es visible (tarifa 0 ⇒ +pasajeros
  ⇒ `f 6,7→8,2` ⇒ espera `4,4→3,7` min). El reparto modal apenas cambia (metro
  ~56%). 27/27 tests del core siguen verdes; wheel de Pyodide recompilado. El
  slider de `cap_tren` en la UI baja su mínimo a 100. Ver D‑18 en
  `DISCREPANCIES.md` y §2.3 de `MATHEMATICAL_MODEL.md`.
- **H2 (bencina) y H3 (pistas) — NO se tocó el modelo** (son comportamientos
  económicamente correctos: el conductor de altos ingresos es poco sensible al
  costo marginal; sin congestión las pistas no alivian nada). Se agregaron
  **notas (`hint`) bajo los sliders** de bencina (Economía) y nº de pistas
  (Oferta) aclarando cuándo cada palanca muerde.
- **H4 (convergencia) — sin cambios** (decisión de alcance): los 3 escenarios
  extremos con bici saturada se resuelven subiendo `max_iter`/`tolerance` desde
  la UI. Pendiente eventual: reforzar la estabilidad de `supply/bike.py`.
