# Auditoría del módulo de TRANSPORTE — iteración 4 (agosto 2026)

Barrido de **todos** los parámetros de `SimulationConfig` por la misma ruta que
usa la app (`iter_msa_desde_suelo`). Hallazgos con ID `AT-xx`.

Reproducir: `cd packages/titirilquen_core && uv run python scripts/auditoria_transporte.py`
Baseline: 201 celdas · 20 km · ΣH = 36.000 · `expected` · seed 42 · tol 0,1 →
**auto 11,00 · metro 55,46 · bici 11,32 · caminata 7,75 · tele 14,47 · v/c 0,89**

| ID | Hallazgo | Veredicto |
|---|---|---|
| AT-01 | Borde de `ancho_pista_m` en 3,0 m contradecía al Overleaf | 🐛 **CORREGIDO** |
| AT-02 | La oferta vial mueve el v/c fuerte y el reparto poco — estructural | ✅ conforme |
| AT-03 | El precio es la palanca del auto (20 pp), no la oferta | ✅ conforme |
| AT-04 | Invariancia a la resolución de grilla | ✅ conforme |
| AT-05 | Pendiente ±p da resultados idénticos — simetría por construcción | ⚠️ contraintuitivo |
| AT-06 | `capacidad_tren` con signo invertido y no monótono | ⚠️ S-07 confirmado |
| AT-07 | Muertos confirmados: `tasa_carga`, `factor_emision_auto`, `v_*`, `densidad_hab_km` | ⚠️ limpieza pendiente |
| AT-08 | `frec_min` inerte; `frec_max` satura sobre ~31 | ℹ️ observación |
| AT-09 | `anden_beta` inerte con defaults; `anden_alpha` sí muerde | ⚠️ para calibrar |
| AT-10 | Sin restricción dura de capacidad — BPR blanda; el techo de la bici es no estándar | ✅/⚠️ ver §3 |
| AT-11 | `tolerance = 0` nunca converge formalmente | ℹ️ menor |

## 1. Bug encontrado

### AT-01 — `ancho_pista_m = 3,0` caía en la categoría equivocada 🐛 CORREGIDO

El barrido mostró que 2,5 m y 3,0 m daban resultados **idénticos** (auto 10,54 ·
v/c 1,14 · t_auto 28,6), lo que no podía ser: son factores de penalización
distintos.

- **Overleaf §4.2**: `v_l = 0,9·v_max si 3 ≤ a < 3,5` — el 3,0 es **inclusivo**.
- **Código**: `if 3.0 < ancho_m < 3.5: return 0.9` — estricto.

Con el slider en exactamente 3,0 m (alcanzable, paso 0,1) se aplicaba 0,75 en
vez de 0,9: **20% menos de velocidad libre y de capacidad**. Los tests probaban
2,9 y 3,2, nunca el borde. Corregido a `ancho_m >= 3.0` y agregados los casos
de borde al test.

## 2. ¿Responde el modelo en la dirección correcta?

### AT-02 / AT-03 — Sí, pero la oferta y el precio actúan en planos distintos ✅

**Oferta vial** (mueve mucho el v/c, poco el reparto):

| | auto % | v/c | t_auto |
|---|---|---|---|
| 1 pista | 10,50 | **1,71** | 24,3 |
| 2 pistas (base) | 11,00 | 0,89 | 20,6 |
| 6 pistas | 11,17 | **0,30** | 19,3 |
| v_max 15 | 9,33 | 1,57 | 48,0 |
| v_max 80 | 11,63 | 0,37 | 7,5 |

**Precio** (mueve el reparto):

| parking | auto % | v/c | CO₂ |
|---|---|---|---|
| $0 | **22,26** | 1,81 | 11.320 |
| $6.000 (base) | 11,00 | 0,89 | 5.065 |
| $30.000 | **2,12** | 0,17 | 3.210 |

El estacionamiento mueve el auto **20 pp**; seis veces la capacidad vial lo
mueve **0,7 pp**. No es un defecto: es la elasticidad del modelo. La congestión
vale poco en la utilidad frente al costo fijo del auto. Consecuencia
pedagógica: **este simulador enseña que la política de precios domina a la
política de infraestructura**, que es un resultado defendible y vale la pena
enunciarlo explícitamente en el tutorial.

Todos los demás verificados en dirección correcta: tarifa de metro ↑ → metro ↓
(57,72 → 51,98), estaciones ↑ → metro ↑ (50,32 → 57,10), v_caminata ↑ →
caminata ↑ (5,01 → 12,99), teletrabajo ↑ → todo ↓ (auto 15,26 → 6,60),
capacidad de ciclovía ↑ → bici ↑ (8,95 → 24,64).

### AT-04 — Invariancia a la grilla ✅

51 / 201 / 501 celdas → auto 11,12 / 11,00 / 11,01. La resolución es resolución
y no una palanca de demanda encubierta (D-28 funciona).

### AT-05 — La pendiente es simétrica por construcción ⚠️

Pendiente −8%, 0% y +8% → **−8 y +8 dan resultados idénticos** (auto 11,04 ·
metro 56,13 · bici 10,60). El modelo aplica `+p` al lado izquierdo y `−p` al
derecho (`bike.py`), así que invertir el signo solo intercambia los lados: el
agregado no puede cambiar.

Es correcto dado el modelo, pero **contraintuitivo en la UI**: el slider va de
−10 a +10 y el estudiante espera que el signo importe. Lo que cambia es el
perfil izquierda/derecha, no el total. Recomendación: renombrar el control a
«desnivel» o mostrar el perfil asimétrico junto al slider.

## 3. ¿Tiene restricciones de capacidad? ¿Debería?

**No hay ninguna restricción dura**, y eso es lo correcto para un modelo de
equilibrio de este tipo:

| Modo | Mecanismo | Estándar |
|---|---|---|
| Auto | BPR `t = t₀(1 + α(q/C)^β)` — el flujo puede exceder C, el tiempo crece | ✅ Sheffi, Ortúzar & Willumsen |
| Metro | Frecuencia endógena `f = clip(carga/K, f_min, f_max)` + BPR de andén | ✅ Mohring; frecuencia como respuesta de oferta |
| Bici | BPR **más un techo**: `t = min(BPR, tiempo de caminar el tramo)` | ⚠️ no estándar |
| Caminata | Ninguna: nunca se congestiona | ⚠️ simplificación no declarada |

Las restricciones blandas (BPR) son la formulación estándar y no debería haber
capacidad dura: un modelo con cola requiere dinámica temporal que este no tiene.

Dos observaciones:

- **El techo de la bici (R-7/D-21) es una restricción no estándar** que vuelve
  la capacidad de ciclovía una palanca débil en el extremo: una vez saturada,
  el tiempo se pega al de caminar y α/β dejan de significar algo. Con los
  defaults la bici opera **sobre capacidad en todos los escenarios** (v/c 1,4 a
  4,0; ver S-10), o sea buena parte del uso ocurre en esa zona degenerada.
- **La caminata no tiene función de oferta**: es el piso del choice set y el
  techo de la bici, pero nunca se congestiona. Razonable para caminata, pero no
  está declarado como supuesto en §3 del Overleaf.

### AT-06 — `capacidad_tren`: signo invertido y no monótono ⚠️

| cap_tren | metro % | f_op | v/c auto |
|---|---|---|---|
| 100 | 51,27 | 30,0 | 1,02 |
| 300 (base) | **55,46** | 30,0 | 0,89 |
| 1.000 | 55,20 | **9,4** | 0,91 |

No es una restricción de confort sino el **divisor de la frecuencia**
(`f = carga/K`): trenes más grandes ⇒ menos frecuencia ⇒ más espera. El efecto
además **no es monótono** (51,27 → 55,46 → 55,20), porque a K bajo se activa la
BPR de andén y a K alto cae la frecuencia. Un usuario que sube «capacidad del
tren» esperando mejorar el metro obtiene lo contrario o nada.

**No hay penalización por hacinamiento en vehículo en todo el core** (S-07). Es
la brecha de modelo más clara del módulo.

### AT-08 / AT-09 — Frecuencia y andén ⚠️

- `frec_min` 2 / 6 / 15 → **idéntico**: con f_op = 30 (en el techo) el piso
  nunca muerde. Inerte con los defaults actuales.
- `frec_max` 10 / 30 / 60 → 13,95 / 11,00 / 10,97 de auto. Muerde fuerte por
  abajo y **satura sobre ~31** (f_op = 31,5 con frec_max = 60).
- `anden_alpha` 0 / 0,5 / 3 → auto 10,97 / 11,00 / 11,14: efecto pequeño con los
  defaults, pero **grande cuando la frecuencia está topada** (ver S-09: hasta
  34,6 min de espera). Su calibración importa.
- `anden_beta` 1 / 4 / 8 → prácticamente idéntico (metro 55,45 / 55,46 / 55,45).
  Inerte en el rango de operación normal.

### AT-07 — Parámetros muertos, confirmados por medición ⚠️

| Parámetro | Prueba | Resultado |
|---|---|---|
| `tasa_carga` | 6 vs 100 | idéntico — no implementado |
| `factor_emision_auto` | 0,18 vs 5,0 | CO₂ idéntico (5.065) — huérfano |
| `v_auto` global | 31 vs 80 | idéntico — solo semilla de iteración 0 |
| `densidad_hab_km` | 500 / 1.800 / 5.000 | idéntico — la población viene de ΣH |

(`factor_emision_metro_tren_km` sí funciona: 2,5 → 10 lleva el CO₂ de 5.065 a
14.065.)

## 4. ¿Está calibrada la ciudad para observar el efecto esperado?

**Para forma urbana: sí, tras la recalibración de la iteración 3.**

| | auto | metro | bici | caminata | t_auto |
|---|---|---|---|---|---|
| 8 km | 9,29 | 35,46 | 17,51 | **23,25** | 8,2 |
| 20 km | 11,00 | 55,46 | 11,32 | 7,75 | 20,6 |
| 40 km | 12,52 | **62,28** | 7,73 | 3,02 | 41,6 |

**Para congestión: parcialmente.** El baseline opera a v/c 0,89 — justo bajo
saturación, que es el punto donde la BPR es más informativa. Bien elegido. Pero:

- La **bici** parte saturada (v/c > 1 siempre): su BPR opera fuera de rango.
- El **metro** parte con la frecuencia topada (f_op = 30 = frec_max), así que el
  efecto Mohring está agotado en el default.

O sea: de los tres modos con oferta congestionable, **solo el auto está
calibrado en una zona donde su función de congestión es informativa**.

### AT-11 — `tolerance = 0` ℹ️

Con tolerancia 0 el criterio nunca se cumple y la corrida agota las 20
iteraciones marcada como «sin converger», aunque el residuo sea despreciable.
Es el default del core (no el de la app, que usa 0,1). Menor, pero confunde si
alguien lo pone en 0 desde la UI.

## 5. Resumen ejecutivo

**El módulo responde correctamente en dirección para todos los parámetros
vivos.** Se encontró **un bug real** (AT-01, corregido) y se confirmaron por
medición las brechas ya conocidas.

Lo que un usuario del simulador debe saber, y hoy no está dicho:

1. **El precio domina a la infraestructura** (AT-03): $30.000 de parking mueven
   20 pp; seis veces la capacidad vial mueve 0,7. Es un resultado del modelo,
   no un error, y merece estar en el tutorial.
2. **De los tres modos congestionables, solo el auto está bien calibrado**
   (§4): la bici parte saturada y el metro parte topado.
3. **La pendiente es simétrica** (AT-05): el signo no cambia el agregado.
4. **`capacidad_tren` hace lo contrario de lo que sugiere su nombre** (AT-06).

Pendientes para los autores: hacinamiento en vehículo (S-07/AT-06),
normalización de unidades y recalibración conjunta de las tres capacidades
(S-06/S-10/§4), y calibración de la BPR de andén (S-09/AT-09).
