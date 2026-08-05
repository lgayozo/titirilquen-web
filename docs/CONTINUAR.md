# Dónde retomar — Titirilquen

Estado al cierre de la sesión de agosto 2026. Rama: **`ciudad-equilibrio-mejoras`**.

```bash
git clone https://github.com/lgayozo/titirilquen-web.git
cd titirilquen-web && git checkout ciudad-equilibrio-mejoras
npm install
```

---

## 1. Cómo levantar y verificar

```bash
npm run dev --workspace @titirilquen/web        # frontend (Pyodide, sin backend)
```

Verificación completa antes de cualquier commit:

```bash
cd packages/titirilquen_core && uv run pytest -q          # 54 tests
cd apps/web && npm run typecheck && npm run test:e2e:fast # 33 e2e
```

**Si tocaste `titirilquen_core`, recompila el wheel** o Pyodide sigue corriendo
código viejo:

```bash
cd apps/web && npm run build:core-wheel
```

> **Windows**: `uv` se instaló por winget y **no queda en el PATH**. Está en
> `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`. En PowerShell:
> `$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"`

---

## 2. Calibración vigente

| Parámetro | Valor | Por qué |
|---|---|---|
| `costo_parking` | $4.000 | Elasticidad-parking −0,45. Con $6.000 era −0,59 y el parking pesaba ~91% del costo monetario del auto |
| `num_pistas` | 2 | Deja el corredor en **v/c 1,05**, la rodilla de la BPR. Con 3 (v/c 0,71) la oferta vial deja de ser palanca: de 3 a 6 pistas el reparto se mueve 0,11 pp |
| `capacidad_pista` bici | 2.500 bici/h | Flujo de saturación realista. Con 800 el modo operaba a v/c 2,4, **sobre** el techo de caminata (1,96), donde su BPR no significa nada |
| `frec_max` | 40 tph | Con 30 la frecuencia quedaba topada y el efecto Mohring agotado. Ahora f_op ≈ 26, interior |
| `tolerance` | 0,1 | Igual en core y frontend (se eliminó la divergencia del contrato) |
| `factor_flota_auto` | 1,0 | Multiplicador de la curva COPERT. Reemplaza al huérfano `factor_emision_auto` |

**Línea base**: auto 12,96 · metro 46,43 · bici 19,01 · caminata 7,13 · tele 14,47 · v/c 1,05.

Reproducir: `cd packages/titirilquen_core && uv run python scripts/auditoria_transporte.py`

---

## 3. Scripts de medición

Todos desde `packages/titirilquen_core`, con `uv run python scripts/<x>.py`:

| Script | Qué responde |
|---|---|
| `auditoria_transporte.py` | Barrido de todos los parámetros de transporte: dirección y magnitud |
| `auditoria_suelo.py` | Ídem para uso de suelo |
| `diagnostico_elasticidades.py` | Elasticidades arco, umbral del techo de la bici, capacidad de tren vs frecuencia |
| `paradojas.py` | Downs-Thomson y Braess: agregados de ciudad completa por número de pistas |
| `sensibilidad.py` | Barrido densidad × pistas (el original) |

---

## 4. Lo que quedó pendiente

### 4.1 Decisión tuya, bloqueante

- **Valor del tiempo social**: hoy es un **placeholder** = promedio ponderado de
  los conductuales ($8.847/h). Hay que reemplazarlo por el valor de norma.
  Está en `apps/web/src/lib/agregados.ts::votSocialPorDefecto`.
  Los conductuales (β_t/β_c) son $41.250 / $9.930 / $1.500 por hora.

### 4.2 Implementable

- ~~**Panel de calibración**~~ — **hecho** (`2a4c9f6`). Está en el sidebar de
  transporte, después de las palancas, con pestañas por estrato y tres cifras
  derivadas arriba: valor del tiempo, razón espera/viaje y razón
  caminata/viaje. Los campos confirman al salir o con Enter, no en cada tecla.

- **Demanda inducida** — es lo que falta para que Downs-Thomson pueda
  aparecer, ver §5.

### 4.3 Deuda de documentación

Las tablas de `AUDITORIA_TRANSPORTE.md` y `ANALISIS_SENSIBILIDAD.md` se midieron
con calibraciones anteriores. **Las direcciones y veredictos valen; las
magnitudes no** — hay que releerlas corriendo los scripts. Ya está la
advertencia en el encabezado de la auditoría.

---

## 5. Downs-Thomson: dónde quedó la conversación

**Braess es imposible** por topología, no por calibración: exige elección de
RUTA y este es un corredor único donde todos van al CBD por el mismo eje.

**Downs-Thomson no se observa** en ninguna región de parámetros probada. Se
barrió 1→10 pistas en ocho calibraciones, incluida la más favorable posible:
estilizado auto-vs-metro (sin bici ni caminata), parking gratis, K=3000, sin
piso de frecuencia y con la espera valorada 4× el tiempo en vehículo. Agregar
pistas **siempre** baja el tiempo medio.

La razón es un acoplamiento estructural: **el desplazamiento modal y la
ganancia vial son la misma cosa**. Para que el metro pierda pasajeros hace falta
que el auto mejore mucho, pero esa mejora *es* el beneficio. No se puede tener
un desplazamiento grande con una ganancia chica.

**Qué habría que cambiar**, en orden de retorno:

1. **Demanda inducida** (recomendado). Hoy el total de viajes es FIJO: el
   teletrabajo es exógeno (`prob_teletrabajo` por estrato) y por eso `tele` sale
   14,47 en las ~40 filas de la auditoría. Meter «no viajar» como alternativa
   del logit hace que mejorar el auto **genere viajes nuevos** que vuelven a
   congestionar. Es la ley fundamental de la congestión. Es **extensión de
   modelo, no calibración**, y habría que implementarla y medir — no está
   garantizado que la paradoja emerja.
2. Reparto determinista (Wardrop) en vez de logit: el logit suaviza el
   equilibrio y amortigua la paradoja.

> **Ojo con una intuición equivocada**: el hacinamiento en vehículo (S-07) **no
> ayudaría**. Al perder pasajeros el metro va *menos* lleno, o sea es una
> deseconomía de escala que juega EN CONTRA de Downs-Thomson.

---

## 6. Para la reunión con los autores

1. **La «congestión de andén» no modela congestión de andén.** El código usa
   `ratio = carga / (frec_max · K)`, y como `f_teórica = carga/K`, eso es
   **algebraicamente idéntico a `f_teórica / frec_max`**: mide utilización de
   frecuencia, no pasajeros por m² de andén. Consecuencias: duplica el efecto
   del tope, solo puede morder cuando la frecuencia está topada, y **subir
   `frec_max` lo apaga**. La corrección natural sería usar `f_op` en el
   denominador, pero cambia el significado del parámetro.
2. **Sin hacinamiento en vehículo** (S-07). Como `f = carga/K` por
   construcción, la carga por tren es *siempre exactamente K*: no hay ningún
   término que castigue ir apretado.
3. **`capacidad_tren` tiene signo invertido**: es el divisor de la frecuencia,
   así que subirla BAJA la frecuencia y empeora el metro. La política «más
   capacidad Y más frecuencia» **no es representable**: medido, K=900 con
   frec_max=90 da peor resultado que la base.
4. **`Suelo.tex` §2.7 (marca S-5) es falso**: afirma que el logit
   heteroscedástico «es el default de la implementación de referencia». No está
   implementado. Se eliminó del proyecto toda referencia (había un
   `solve_utility_logit` que decía corregir el λ y solo lo dejaba inerte).
5. **λ no está identificado** (D-08): mover `λ_h` es **idénticamente**
   re-escalar `(α_h, ρ_h)` por `1/λ_h` — verificado, `max|ΔQ| = 0`. No es un
   parámetro económico independiente.
6. **La espera está subvalorada**: `b_tiempo_espera / b_tiempo_viaje` da
   0,91 / 0,73 / 1,00 por estrato. La evidencia apunta a que la espera pesa
   MÁS que el tiempo en vehículo (~1,5–2,5×), no menos. Desde `2a4c9f6` la
   razón se muestra en pantalla, en el panel de calibración, así que se puede
   mostrar en vivo en la reunión.

---

## 7. Trampas conocidas del repo

- **Los presets declaran valores ABSOLUTOS, no diffs.** Cada vez que se
  recalibra un default hay que moverlos o aplicar cualquier política revierte
  ese parámetro en silencio. **Ya pasó tres veces** (`frec_max: 20`,
  `parking: 6000`, `num_pistas`). Los neutros van al default; los deliberados
  se reescalan manteniendo su RAZÓN contra la base. Ver el comentario en
  `presets.py`.
- **`model_copy(update=...)` de Pydantic NO valida.** Una clave inexistente se
  cuela como atributo suelto y el barrido reporta «inerte» un parámetro que en
  realidad no se está moviendo. Pasó dos veces. Los scripts de auditoría ahora
  llevan un guard `_valida()`.
- **El trace tiene DOS espejos**: `apps/web/src/workers/pyodide.worker.ts`
  (`_trace_to_py`) y `apps/api/src/api/serialization.py` (`trace_to_dict`).
  Olvidar el segundo deja el campo en null solo en modo servidor.
- **`extra="forbid"`**: quitar un campo del schema rompe la importación de
  escenarios guardados. Hay que agregar la migración en
  `apps/web/src/lib/serialization.ts`.
- **Golden fixture**: al cambiar defaults del core hay que regenerarlo con
  `uv run python tests/test_contract_frontend.py`.

---

## 8. Recorrido de esta sesión

De más reciente a más antigua:

| Commit | Qué |
|---|---|
| `2a4c9f6` | Panel de calibración: los betas del logit, visibles y editables |
| `a4d3970` | Este documento |
| `7fdb77b` | Sandbox de 16 figuras a 8 |
| `1a9af0b` | Comparar dentro de transporte + agregados + logsum |
| `3ee6773` | Presets de ciudad al módulo de uso de suelo |
| `301cdbd` | Política «Base» + medición de las paradojas |
| `0873773` | Comparar: presets en la tarjeta, diff de inputs, base elegible, persistencia |
| `37b1a77` | Volver a 2 pistas |
| `5c71f9e` | Guard contra parámetros inexistentes en la auditoría |
| `4c546f1` | Recalibración + factor de flota |
| `bfa987d` | Exploración de la elasticidad del parking |
| `86d7096` | Pendiente en ambos lados de la ciudad |
| `d0100fe` | Aviso de tope de frecuencia + reorden de figuras |
| `91b8cf9` | Eliminar toda referencia al logit heteroscedástico |
