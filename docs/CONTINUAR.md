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

Y **si cambiaste un default del core, regenera el fixture golden**:

```bash
cd packages/titirilquen_core && uv run python tests/test_contract_frontend.py
```

> **Windows**: `uv` se instaló por winget y **no queda en el PATH**. Está en
> `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`. En PowerShell:
> `$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"`

---

## 2. Calibración vigente

Toda la sesión de agosto 2026 fue recalibración. Reproducir con:

```bash
cd packages/titirilquen_core && uv run python scripts/diagnostico_calibracion.py
```

### 2.1 Demanda — las razones que definen el comportamiento

| Parámetro | Valor | Por qué |
|---|---|---|
| Valor del tiempo conductual | 6.200 / 3.100 / 1.600 $/h | Fijado por Leandro. Antes 41.250 / 9.930 / 1.500: la dispersión bajó de 27,5× a 3,9× |
| espera / viaje | **2,0** en los tres | Antes 0,91 / 0,73 / 1,00 — el modelo decía que esperar molesta MENOS que ir sentado. **Respaldado por el SNI** (ponderador 2) |
| caminata / viaje | **1,7** en los tres | Antes 2,73 / 1,33 / 1,67, sin patrón y por encima de la espera. **El SNI dice 2,0** — ver §4.1 |
| ASC (min de ventaja sobre el metro) | auto **+20** · metro 0 · bici **−18** · caminata **0** | Iguales en los tres estratos: el gradiente de ingreso entra por el VoT y la disponibilidad de auto, no dos veces |
| `prob_auto` | 0,90 / 0,60 / 0,25 | Fijado por Leandro. Techo del reparto del auto: 52,1% de los viajes |
| `prob_teletrabajo` | 0,40 / 0,20 / 0,05 | La política es el multiplicador `city.teletrabajo_factor` |

`b_costo` se despeja del VoT: `b_costo = b_tiempo_viaje · 60 / VoT`. Se ajusta el
coeficiente de COSTO y no el de tiempo a propósito — `b_tiempo_viaje` es el
denominador de los minutos-equivalentes, así que dejarlo fijo preserva el
significado de las ASC y de las penalizaciones.

### 2.2 Ciudad y oferta

| Parámetro | Valor | Por qué |
|---|---|---|
| `share_estratos` | 0,20 / 0,50 / 0,30 | Antes 0,10/0,40/0,50. Con media ciudad en el estrato bajo el auto no podía competir POR CONSTRUCCIÓN |
| `costo_parking` | $2.000 | **No es precio de lista**: costo ESPERADO = precio × probabilidad de pagarlo (el modelo se lo cobra a todos) |
| `tiempo_detencion_min` | 0,5 (30 s) | Nuevo. Sin él, agregar estaciones acortaba el acceso sin costo alguno |
| `num_pistas` | 2 | Deja el corredor en v/c 0,97, la rodilla de la BPR |
| `capacidad_pista` bici | 2.500 bici/h | Flujo de saturación realista |
| `frec_max` | 40 tph | Con 30 la frecuencia quedaba topada y el Mohring agotado |
| `tolerance` | 0,1 | Igual en core y frontend |

### 2.3 Valores de norma (no calibración)

| | Valor | Fuente |
|---|---|---|
| Valor social del tiempo | **3.338 $/h-pax** | Precios Sociales 2026 SNI, Tabla 2.1, «Viaje en vehículo» |

El PDF está en `reference/Precios-Sociales-2026.pdf`. **Hay que actualizarlo cada
año.** La misma tabla trae valores que el simulador todavía NO usa: precio social
del carbono 71.801 $/t CO₂eq (el simulador calcula CO₂ pero no lo valora) y
precio social del combustible 760 $/l para automóvil.

### 2.4 Línea base

**auto 11,87 · metro 41,62 · bici 23,92 · caminata 8,12 · tele 14,47 ·
v/c 0,97 · t_auto 21,7 min · f_op 23,4 tph**

Participación del auto por estrato: **46,3 / 19,2 / 6,4**.

Reproducir: `uv run python scripts/auditoria_transporte.py`

---

## 3. Scripts de medición

Todos desde `packages/titirilquen_core`, con `uv run python scripts/<x>.py`:

| Script | Qué responde |
|---|---|
| `diagnostico_calibracion.py` | **Los betas en minutos-equivalentes**: razones, VoT, penalizaciones, ASC. Es el que hace legibles los 42 coeficientes |
| `auditoria_transporte.py` | Barrido de todos los parámetros de transporte: dirección y magnitud |
| `auditoria_suelo.py` | Ídem para uso de suelo |
| `diagnostico_elasticidades.py` | Elasticidades arco, techo de la bici, capacidad de tren vs frecuencia |
| `paradojas.py` | Downs-Thomson y Braess por número de pistas |
| `sensibilidad.py` | Barrido densidad × pistas |

---

## 4. Lo que quedó pendiente

### 4.1 Decisión, con la fuente ya en mano

**`b_tiempo_caminata`: 1,7× o 2,0×.** La Tabla 2.1 del SNI asigna ponderador **2**
tanto a la espera como a la caminata. Nuestro 1,7× salió de razonamiento general,
no de la norma. Pero hay una complicación estructural: `b_tiempo_caminata` pesa
**dos cosas a la vez** — el acceso al metro Y el modo caminata completo
(`demand/utility.py`, líneas 103 y 137). El SNI acota su ponderador 2 a los
usuarios de transporte público, y en viajes combinados «solo el tramo de
transporte público está afecto a ellos». O sea:

- El acceso al metro **debería** ir a 2,0 según la norma.
- El modo caminata completo no está cubierto por la norma.

Arreglo limpio: **separar el coeficiente en dos** (`b_tiempo_acceso` para el
acceso al metro, `b_tiempo_caminata` para el modo). Es cambio de schema + los
cuatro espejos, pero resuelve un defecto ya documentado y permite aplicar la
norma exactamente.

### 4.2 Necesita un dato externo

**Reajuste completo de las ASC.** Las actuales (+20 / 0 / −18) se eligieron para
que el AGREGADO no se moviera, **no** por respaldo empírico. Con una EOD que dé
reparto modal por estrato, el procedimiento estándar las reemplaza por valores
estimados:

```
ASC_h  <-  ASC_h + ln(share_objetivo_h / share_modelo_h)
```

iterado recalculando el equilibrio en cada paso (el reparto realimenta la
congestión). Ya se probó con objetivos 90/60/25 y **no converge**: las ASC trepan
a +60 / +90 / +126 minutos sin alcanzar el objetivo, porque la congestión se
autolimita y el techo de `prob_auto` ata. Ese resultado importa: dice que
objetivos muy altos de auto exigen también más capacidad vial y más motorización.

### 4.3 Siguiente en la fila

**Asignación determinística (Wardrop)** como tercera opción del selector que ya
existe (`montecarlo` / `expected`). Ver §5: es lo único que hace observable
Downs-Thomson. Alcance: `assignment` pasa de dos a tres valores en `config.py` y
en el espejo TS, la elección de modo en `msa.py` usa `argmin` de costo en vez del
logit, y hay que regenerar el fixture. El MSA ya promedia iteraciones, que es
justo lo que hace converger un equilibrio de Wardrop con carga todo-o-nada.

### 4.4 Deuda de documentación

Las tablas de `AUDITORIA_TRANSPORTE.md` y `ANALISIS_SENSIBILIDAD.md` se midieron
con calibraciones anteriores. **Las direcciones y veredictos valen; las
magnitudes no.**

---

## 5. Downs-Thomson: resultado medido

**No se observa con parámetros realistas, y la razón es estructural.**

Se probó, midiendo con el **logsum** (la única medida que no se deja engañar por
efectos de composición): capacidad de tren de 300 a 5.000 · frecuencia mínima de
0,5 a 6 · estaciones de 8 a 24 · densidad de 300 a 2.500 hab/km · espera de 2,0×
a 2,5× · escala del logit igualada entre estratos · mezcla de estratos ·
motorización · parking de $0 a $6.000 · sólo auto+metro · demanda inducida
(teletrabajo endógeno) · e incrementos finos de capacidad en vez de pistas
enteras. **En todos, el excedente sube al agregar capacidad.**

Lo único que produjo la paradoja: llevar los betas a **×20**, o sea acercar el
logit a elección determinística.

**Por qué.** Derivando el equilibrio clásico `c_R(q_R,K) = c_T(Q−q_R)`:

```
dc*/dK = c_T' · (∂c_R/∂K) / (c_R' + c_T')  >  0   si c_T' < 0
```

la paradoja es **automática** cuando el transporte público tiene economías de
escala — pero el resultado depende de que los usuarios **arbitren hasta igualar
costos**. Un logit con dispersión de gustos realista no iguala: el usuario de
auto retiene una ganancia neta que el modelo clásico habría disipado.

Condición cuantitativa derivada para el MNL:

```
P_metro · w_espera · espera(min) · |β_tiempo|  >  1
```

Lo mejor alcanzado con valores defendibles fue **0,37**. Para llegar a 1 con
|β_t| = 0,055 haría falta `P_metro × espera > 7,3`, o sea el metro llevando 45%
de los viajes con una espera de 16 minutos: un headway de 32 minutos.

> **Dos falsos positivos que ya se descartaron**, por si reaparecen: el tiempo
> físico medio puede SUBIR y el costo generalizado tiempo+dinero también, sin que
> haya paradoja. Son efectos de composición — quien se cambia de modo
> voluntariamente puede tener más minutos físicos, o pagar más parking, y aun así
> estar mejor. Solo el logsum decide.

> **Ojo con una intuición equivocada**: el hacinamiento en vehículo (S-07) **no
> ayudaría**. Al perder pasajeros el metro va *menos* lleno: es una deseconomía de
> escala que juega EN CONTRA de Downs-Thomson. Lo mismo el dwell dependiente de
> la demanda.

**Braess es imposible** por topología, no por calibración: exige elección de RUTA
y este es un corredor único.

---

## 6. Para la reunión con los autores

1. **Downs-Thomson no es robusto a utilidad aleatoria.** Es una propiedad del
   equilibrio determinístico. Ver §5 — hay derivación y medición.
2. **La «congestión de andén» no modela congestión de andén.** El código usa
   `ratio = carga / (frec_max · K)`, y como `f_teórica = carga/K`, eso es
   **algebraicamente idéntico a `f_teórica / frec_max`**: mide utilización de
   frecuencia, no pasajeros por m². Subir `frec_max` lo apaga.
3. **Sin hacinamiento en vehículo** (S-07). Como `f = carga/K` por construcción,
   la carga por tren es *siempre exactamente K*.
4. **`capacidad_tren` tiene signo invertido**: es el divisor de la frecuencia, así
   que subirla BAJA la frecuencia y empeora el metro. La política «más capacidad
   Y más frecuencia» no es representable.
5. **`Suelo.tex` §2.7 (marca S-5) es falso**: afirma que el logit heteroscedástico
   «es el default de la implementación de referencia». No está implementado.
6. **λ no está identificado** (D-08): mover `λ_h` es **idénticamente** re-escalar
   `(α_h, ρ_h)` por `1/λ_h` — verificado, `max|ΔQ| = 0`.
7. **El metro no cobraba las detenciones** (corregido en `39b0a86`). Agregar
   estaciones acortaba el acceso sin costo: densificar la red era monótonamente
   bueno. Ahora hay óptimo interior (~20 estaciones en 20 km).
8. **`tasa_carga` sigue muerto.** Serviría para un dwell dependiente de los
   pasajeros que suben — deseconomía de escala, decisión de modelación aparte.
9. **La calibración original tenía la espera subvalorada** (0,91/0,73/1,00 contra
   el ponderador 2 del SNI) y gradientes de ingreso duplicados en las ASC.

---

## 7. Trampas conocidas del repo

- **El contrato NO cubre los 42 betas.** `defaults-golden.json` solo tiene `city`,
  `globales`, `land_use`, `sim` y `supply`. `presets.py::DEFAULT_STRATA` y
  `defaults.ts::baseBetas` pueden desincronizarse sin que nada avise. **Hay una
  tarea pendiente para taparlo.**
- **Había una TERCERA copia de los betas** en `sensibilidad.py::_BETAS_UI`, que
  quedó atrás en la recalibración y las auditorías midieron valores viejos sin
  avisar. Ya se eliminó (ahora construye desde `DEFAULT_STRATA`), pero es el tipo
  de cosa que vuelve.
- **Los presets declaran valores ABSOLUTOS, no diffs.** Al recalibrar un default
  hay que moverlos o aplicar cualquier política revierte ese parámetro en
  silencio. **Ya pasó cuatro veces** (`frec_max: 20`, `parking: 6000`,
  `num_pistas`, `parking: 4000`). Neutros al default; deliberados reescalados
  manteniendo su RAZÓN. Ver el comentario en `presets.py`.
- **`model_copy(update=...)` de Pydantic NO valida.** Una clave inexistente se
  cuela como atributo suelto y el barrido reporta «inerte» un parámetro que no se
  está moviendo. Los scripts de auditoría llevan un guard `_valida()`.
- **El trace tiene DOS espejos**: `apps/web/src/workers/pyodide.worker.ts`
  (`_trace_to_py`) y `apps/api/src/api/serialization.py` (`trace_to_dict`).
- **`extra="forbid"`**: quitar un campo del schema rompe la importación de
  escenarios guardados. Agregar uno nuevo con default es seguro.
- **No escribir archivos con acentos desde PowerShell.** `Get-Content` +
  `Set-Content` los codifica dos veces y deja el archivo en mojibake. Usar las
  herramientas de edición o Python con `encoding='utf-8'` explícito.

---

## 8. Recorrido de esta sesión

De más reciente a más antigua:

| Commit | Qué |
|---|---|
| `0f8c6bf` | Valor social del tiempo desde los Precios Sociales 2026 del SNI |
| `3ac28b2` | ASC sin gradiente de ingreso: auto +20, caminata 0 |
| `a796d4c` | Disponibilidad de auto a 0,90 / 0,60 / 0,25 |
| `9854f6d` | Motorización, mezcla de estratos y ASC de la bici sin gradiente |
| `39b0a86` | Metro: cobrar la detención en estaciones |
| `4b0336c` | Bajar el parking a $2.000 tras la recalibración del valor del tiempo |
| `807c78a` | Recalibrar los betas de tiempo y el valor del tiempo |
| `c2813b2` | Diagnóstico de calibración: los betas en minutos-equivalentes |
| `2a4c9f6` | Panel de calibración: los betas del logit, visibles y editables |
| `a4d3970` | Documento de continuidad |
