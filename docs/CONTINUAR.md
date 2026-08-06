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
| `capacidad_tren` | **1.000 pax** | Antes 300. Capacidad realista, y pone al metro en la zona EMPINADA de su economía de escala (f_op ~6, espera ~5 min): sus palancas y Downs-Thomson responden |
| `frec_min` | **2 tph** | Antes 6. Con K=1.000 la frecuencia demandada es ~5–7: un piso de 6 la recortaría justo donde vive el Mohring |
| `frec_max` | 40 tph | No muerde con K=1.000 (f_teórica ~6) |
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

**auto 15,38 · metro 36,99 · bici 21,43 · caminata 6,75 · tele 19,44 ·
v/c 1,25 · t_auto 23,7 min · f_op 20,9 tph** (expected, seed 42, tol 0,1)

Reproducir: `uv run python scripts/auditoria_transporte.py`

> **Errata**: las líneas base reportadas en los commits `9854f6d..ea4a05b`
> (auto 15,41 → 12,16 → 11,87 → 12,10) se midieron con la `H` de la auditoría
> desactualizada en la mezcla ANTIGUA (10/40/50) — quinta mordida de la trampa
> de los espejos. La app siempre usó 20/50/30 (`defaults.ts`); la cifra de
> arriba es la de la app. Direcciones y comparaciones de esos commits valen;
> los niveles no.

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

### 4.3 Hecho: Wardrop como tercer método de asignación

Implementado (`321bd07`): `assignment ∈ {montecarlo, expected, wardrop}`.
`probabilidades_wardrop` en `demand/choice.py` (todo el grupo al modo de mayor
utilidad, empates repartidos en partes iguales), carga fraccional como
`expected`, selector en la UI con hint sobre equilibrios múltiples. Converge en
12–15 iteraciones; 6 tests unitarios, incluido «es el límite del logit al
escalar las utilidades».

Follow-up de UI pendiente: bajo Wardrop la medida emparejada de bienestar es la
utilidad máxima media, no el logsum — la tabla de resultados sigue mostrando el
excedente logsum. El costo generalizado percibido sí muestra el fenómeno (ver
§5), así que no es urgente.

### 4.4 Deuda de documentación

Las tablas de `AUDITORIA_TRANSPORTE.md` y `ANALISIS_SENSIBILIDAD.md` se midieron
con calibraciones anteriores. **Las direcciones y veredictos valen; las
magnitudes no.**

---

## 5. Downs-Thomson: RESUELTO — se observa, y se sabe exactamente cuándo

Búsqueda sistemática en `scripts/buscar_downs_thomson.py` (10 escenarios × 3
equilibrios × barrido de capacidad, mecanismo verificado en cada tramo, y los
hallazgos reverificados con `max_iter=120` y `tol=0.02`). El paper original
(`reference/overleaf_original/main.tex`) es logit puro y no menciona la
paradoja: era un objetivo nuestro, no una promesa de los autores.

### Las condiciones, medidas una a una

| Condición | Evidencia |
|---|---|
| **C2 — arbitraje (Wardrop), la decisiva** | 0 paradojas bajo logit en los 10 escenarios; 8 con mecanismo verificado bajo Wardrop. El logit deja al usuario del modo mejorado una ganancia sin arbitrar (condición MNL: `P_metro·w_esp·espera·β_t > 1`; con valores defendibles llega a 0,37) |
| **C4 — metro en la zona empinada** | Con K=300 (f_op ~23, espera 1,3 min) no aparece ni bajo Wardrop: la curva de escala es plana. Con K=1.000 (f_op 4–7, espera 4–8 min) aparece. `frec_min` alto la mata (el piso impide que la frecuencia caiga) |
| **C3 — homogeneidad amplifica** | En la ciudad real (3 estratos) la caída es −0,6 min; con población homogénea y ciudad bimodal concentrada (todos a la misma distancia), −2 a −10 min; es la diferencia entre arbitraje del decisor y arbitraje poblacional |
| **C1 — terceros modos diluyen** | Sólo auto+metro la refuerza; con 4 modos igual aparece si C2+C4 se cumplen (E02) |
| **C5 — dinero y ASC desplazan la frontera** | dinero=0 y ASC=0 la refuerzan, pero no son necesarios |

### La receta de aula (módulo de transporte)

Desde el cambio de default (K=1.000, frec_min=2) el metro ya viene listo:
**solo elegir método Wardrop** y barrer pistas 1→4:

```
pistas   auto%  metro%   f_op  espera  cg percibido
     1   15.5    39.3    7.1    4.5       $39.5
     2   23.3    33.3    6.0    5.3       $41.5
     3   27.3    28.7    5.2    6.1       $42.4
     4   29.7    26.2    4.7    6.6       $42.7
```

El **costo generalizado percibido de la tabla de resultados sube** al agregar
pistas — el alumno lo ve en pantalla. El bienestar emparejado (utilidad máxima
media) cae de 1 a 3 pistas y recién con ~6 pistas recupera el punto de partida
(verificado con tol=0.02). El tiempo físico medio BAJA mientras tanto:
composición, no mejora — es parte de la lección.

En los escenarios estilizados homogéneos la paradoja toma su forma fuerte, la
**espiral de muerte del metro** (Mogridge): al agregar pistas la participación
del metro cae hasta 0, la espera se va a `30/frec_min`, y el bienestar cae
−10 a −33 min antes de recuperarse recién cuando el metro ya murió y la vía es
enorme. `buscar_downs_thomson.py` E06–E09 lo reproducen.

**Caveat de multiplicidad**: bajo Wardrop dos configuraciones con topes NO
activos pueden aterrizar en equilibrios levemente distintos (sensibilidad de
trayectoria de la carga todo-o-nada). Está advertido en el hint de la UI; para
comparaciones usar siempre el mismo barrido con la misma configuración inicial.

### Por qué el logit no la produce (se mantiene)

Derivando el equilibrio clásico `c_R(q_R,K) = c_T(Q−q_R)`:

```
dc*/dK = c_T' · (∂c_R/∂K) / (c_R' + c_T')  >  0   si c_T' < 0
```

la paradoja exige **arbitrar hasta igualar costos**. La dispersión de gustos
del logit deja ganancias sin arbitrar, y la heterogeneidad (estratos,
distancias) impide el arbitraje poblacional incluso bajo Wardrop — por eso la
versión realista muestra una caída modesta y las homogéneas la espiral
completa.

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

1. **Downs-Thomson no es robusto a utilidad aleatoria — y ahora es demostrable
   en vivo.** Cero paradojas bajo logit en 10 escenarios; bajo Wardrop aparece
   incluso en la ciudad realista si el metro opera en la zona empinada de su
   economía de escala, y en escenarios homogéneos toma la forma de espiral de
   muerte del metro. Ver §5: derivación, medición y receta de aula.
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
