# Dónde retomar — Titirilquen

Estado al 2026-08-16. Rama: **`ciudad-equilibrio-mejoras`**, muy por delante de
`main` y **sin divergencia**: `main` es ancestro directo, así que el merge sería
un fast-forward. Para ver cuánto:
`git rev-list --left-right --count origin/main...HEAD`.

> **Hay commits locales sin pushear** (la auditoría del método de asignación y la
> cirugía de arquitectura `F0`–`F9`). Verificar con
> `git log --oneline origin/ciudad-equilibrio-mejoras..HEAD` antes de asumir que
> el remoto está al día. Lo que cambió la cirugía está en §9.

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
cd packages/titirilquen_core && uv run --extra dev pytest   # 105 tests
cd apps/web && npm run typecheck && npm run test:e2e:fast   # 58 e2e
npm run format:check                                        # desde la raíz
```

**Si tocaste `titirilquen_core`, sincroniza** o Pyodide sigue corriendo código
viejo. Un solo comando recompila el wheel, regenera el contrato TypeScript
(`apps/web/src/lib/gen/`) y los fixtures golden:

```bash
npm run sync:core --workspace @titirilquen/web
```

El CI lo corre y falla si el diff no queda vacío, así que olvidarlo se nota —
pero recién en el CI, no en el navegador, donde simplemente verás resultados
viejos sin ningún aviso.

> **Windows**: `uv` se instaló por winget y **no queda en el PATH**. Está en
> `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`. En PowerShell:
> `$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"`

### 1.1 Qué NO viaja en el repo

Al clonar en otra máquina, esto hay que reponerlo — está todo en `.gitignore`:

| Falta | Consecuencia |
|---|---|
| `.venv/` | Recrear el entorno de Python (`uv sync` o `uv run` lo crea al vuelo) |
| `uv.lock` | **No hay lock**: las versiones no son idénticas entre máquinas. Es deliberado y está justificado en el propio `.gitignore` (el core es librería con cotas abiertas y ningún deploy lo consume) |
| `reference/` | El Overleaf/repo original. Sin él **`comparar_original.py` no corre**; es el único script no reproducible del otro lado |
| `.claude/` | Config local del preview (`launch.json`). Trivial de recrear |

El **wheel de Pyodide sí está versionado**, así que el frontend arranca sin
compilar nada de Python.

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
| `capacidad_tren` | **1.000 pax** | Antes 300. Capacidad realista, y pone al metro en la zona EMPINADA de su economía de escala (f_op ~6, espera ~5 min): sus palancas y Downs-Thomson responden. Es una **elección de régimen**, no solo realismo — ver §4.1c |
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

**auto 16,95 · metro 32,79 · bici 22,84 · caminata 7,98 · tele 19,44 ·
v/c 1,38 · t_auto 24,6 min · f_op 5,9 tph · CO₂ 6.178 kg/h · 7 iter**
(expected, seed 42, tol 0,1). Medido el 2026-08-10.

Reproducir: `uv run python scripts/auditoria_transporte.py`

> El metro baja de 36,99 a 32,79 respecto de la medición anterior por el arreglo
> de `84913c0`: dejó de contarse como viaje en metro el caso sin tramo en tren
> (ver §4.5). El teletrabajo no se mueve, como corresponde: se decide antes de
> la elección de modo.

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
| `auditoria_wardrop.py` | **¿El método `todo_o_nada` produce equilibrio de Wardrop?** Mide el gap de costo generalizado entre grupos |
| `informe_wardrop.py` | Genera los datos de `docs/informe-wardrop.html` |
| `buscar_downs_thomson.py` | Busca la región de parámetros donde la paradoja se observa |
| `comparar_original.py` | Contraste numérico con el simulador original. **Necesita `reference/`**, que no viaja en el repo |
| `datos_informe.py` | Datos de los informes HTML de `docs/` |

Todos comparten `scripts/_comun.py` (construcción de configs, corrida, resumen y
el guard `_valida()`); no copies el andamiaje de un script a otro.

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

### 4.1b Necesita fuente: costo de operación del metro

Dos parámetros nuevos en `supply.train`, ambos con default **PROVISORIO**, que
habilitan el costo del operador, el subsidio y el autofinanciamiento en la tabla
de resultados:

| Parámetro | Default | Qué es |
|---|---|---|
| `costo_operacion_tren_km` | $12.000 | Costo por tren-km (orden de magnitud de metro pesado real) |
| `factor_dia_punta` | 2,0 | Lleva el costo de la punta a base comparable con el ingreso |

**Por qué hace falta el factor.** El autofinanciamiento compara costo DIARIO
contra ingreso DIARIO, y el modelo entrega solo la hora punta:

```
autofinancia  <=>  costo_punta · (R_costo / R_ingreso) <= ingreso_punta
```

con `R_costo` = tren-km del día / tren-km de la punta y `R_ingreso` = viajes del
día / viajes de la punta. Fuera de punta el servicio circula más vacío, así que
`R_costo > R_ingreso` y el factor es > 1. En una frase: **cuánto más caro sale
operar el día completo, por viaje, que si todo el día tuviera la carga de la
punta.** 2,0 es razonable (la punta concentra ~10–12% de los viajes mientras el
servicio corre ~18 h).

**Lo que hay que saber al leer el indicador:** con los defaults el metro sale
superavitario y haría falta un factor de **~3,7** para que requiera subsidio —
fuera del rango físico del parámetro. Eso hizo sospechar de una mala
calibración, pero **medido no lo es**: el signo depende de la FORMA URBANA. El
costo escala con `f · largo · 2` (tren-km) mientras una tarifa plana no escala
con la distancia.

| ciudad | metro % | tren-km/h | costo operación | tarifa | subsidio |
|---|---|---|---|---|---|
| Compacta 8 km | 15,0 | 32 | $0,77 M | $4,31 M | **−$3,54 M** superávit |
| Base 20 km | 34,7 | 235 | $5,63 M | $10,01 M | **−$4,38 M** superávit |
| Dispersa 40 km | 49,6 | 700 | $16,81 M | $14,29 M | **+$2,52 M** requiere subsidio |

El metro *gana* participación al dispersarse (caminata y bici se vuelven
infactibles) y **aun así** deja de financiarse: los tren-km crecen más rápido
que los pasajeros. Ésa es la economía de la dispersión urbana, y emerge del
modelo sin imponerla.

**No cambiar el default para «mostrar el subsidio».** El signo de la base está a
solo **1,8×** de darse vuelta (factor 3,6 o $21.400/tren-km), o sea dentro de la
incertidumbre de dos parámetros provisorios; mientras que la dependencia de la
forma urbana es un factor **22×** en tren-km que ninguna incertidumbre revierte.
Fijar el default por decreto congelaría el resultado incierto y descartaría el
robusto. El contraste entre presets es el que enseña. Ambos parámetros son
sliders en «Oferta · Metro».

### 4.1c Escala de la ciudad vs. `capacidad_tren`: el trade-off con Downs-Thomson

**Procedencia del default original.** El `main.tex` original **no imprime** el
bloque numérico de oferta de tren (solo `CONFIG_DEMANDA`); `K` aparece como
argumento de `oferta_tren` sin valor. El **K = 1200** está atestiguado en
nuestra propia nota de revisión **R-6** del `overleaf_modificado`, que lo cita
como la capacidad original: «con la capacidad original ($K=1200$) la frecuencia
quedaba fija en $f_{min}$ para toda demanda alcanzable y el efecto era
inobservable». Para certeza sobre el 1200 hay que mirar el código original, no
el paper.

Bajamos K a 300 por eso, y después lo subimos a 1000 — casi de vuelta en el
original. **Lo que evitó repetir la falla no fue K sino bajar `frec_min` de 6 a
2:** la frecuencia teórica del default es 5,9 tph, así que con el piso viejo
habría quedado recortada, exactamente el problema del original.

**El metro tiene dos canales de deterioro y solo uno está operativo:**

| canal | fórmula | estado en el default |
|---|---|---|
| **Mohring** (frecuencia) | `f = L_max/K`, `espera = 30/f` | **vivo** — f interior, espera 4,1→6,0 min según pistas |
| **Andén** (hacinamiento) | `ρ = L_max/(f_max·K)`, `×(1+α·ρ^β)` | **muerto** — ρ = 0,15 ⇒ factor 1,0002 (+0,03%) |

Con `f_max·K = 40.000 pax/h/sentido` y carga máxima 5.865, el sistema opera al
15% de su capacidad: la BPR de andén es decorativa.

**Cuánta población haría falta** (largo 20 km, σ 0,50, resto del default):

| densidad | población | metro % | L_max | f teórica | f_op | intervalo | ρ andén | espera |
|---|---|---|---|---|---|---|---|---|
| 1.800 | 36.000 | 34,7 | 5.865 | 5,9 | 5,9 | 10,2 min | 0,15 | 4,7 min |
| 3.600 | 72.000 | 43,6 | 14.894 | 14,9 | 14,9 | 4,0 min | 0,37 | 1,9 min |
| **7.200** | **144.000** | 49,9 | 34.244 | 34,2 | 34,2 | 1,8 min | **0,86** | 0,9 min |
| 14.400 | 288.000 | 52,5 | 72.038 | 72,0 | 40,0 ⚠ | 1,5 min | 1,80 | 1,9 min |
| 57.600 | 1.152.000 | 39,0 | 207.307 | 207,3 | 40,0 ⚠ | 1,5 min | 5,18 | 129,8 min |

~144.000 (4× la actual) es donde K=1000 es un metro de verdad: 34 tph y el
andén aportando +27% a la espera. Sobre eso `f_op` topa en `f_max`.

**Pero subir la población MATA Downs-Thomson** (`todo_o_nada`, barrido de pistas):

| pistas | 36.000 hab: metro % | espera | 144.000 hab: metro % | espera |
|---|---|---|---|---|
| 1 | 39,3 | 4,1 min | 59,2 | 1,1 min |
| 2 | 33,0 | 5,0 min | 57,3 | 1,1 min |
| 3 | 28,1 | 5,6 min | 54,8 | 1,2 min |
| 4 | 26,1 | **6,0 min** | 53,1 | **1,2 min** |

Tres pistas le cuestan **+1,9 min** de espera al usuario de metro en la ciudad
chica y **+0,1 min** en la grande. La razón es la identidad ya derivada,
**`espera = 30K/L_max`**: más demanda ⇒ menos espera ⇒ **nada que degradar**. La
pendiente del Mohring, `∂t_e/∂f = −30/f²`, vale 0,86 min/tph a f = 5,9 y 0,026 a
f = 34,2 — **33× más plana**.

**Consecuencia de diseño.** Los dos regímenes son mutuamente excluyentes y K=1000
no es solo «realismo del tren», es **una elección de régimen**: un tren de 1.000
pax en una ciudad de 36.000 personas está deliberadamente sobredimensionado
respecto de su demanda, y eso es lo que produce la espera larga de la que vive
el fenómeno. Bajar K a 300 lo mataría por el otro lado (`30·300/5.865 ≈ 1,5 min`).
Por eso **no se sube la población del default**; el régimen opuesto se expone
como preset.

**Preset «Metrópolis»** (`CITY_PRESETS`): misma geometría que Base (20 km,
σ 0,50) con 144.000 habitantes. Es el **único preset que rompe la
iso-población**, y a propósito: los otros tres aíslan *forma* manteniendo fija
la escala, y éste aísla *escala* manteniendo fija la forma. Detalle de
implementación en `PresetGallery.tsx::applyCity`: los presets que declaran
`poblacion` (Base y Metrópolis) fijan ΣH escalando los estratos; Compacta y
Dispersa NO la declaran, así comparan forma a la población que el usuario tenga.
Base la declara para que el viaje de vuelta funcione — sin eso, volver de
Metrópolis dejaba la geometría de Base con 144.000 habitantes.

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

### 4.3 Hecho: el todo-o-nada como tercer método de asignación

> Se llamó `wardrop` hasta agosto de 2026. La auditoría (§5 y
> `docs/informe-wardrop.html`) mostró que **no produce un equilibrio de Wardrop**,
> así que el valor del schema pasó a `todo_o_nada`, que es lo que el algoritmo
> hace de verdad. Abajo se conserva la redacción original con el nombre nuevo.

Implementado (`321bd07`): `assignment ∈ {montecarlo, expected, todo_o_nada}`.
`probabilidades_todo_o_nada` en `demand/choice.py` (todo el grupo al modo de mayor
utilidad, empates repartidos en partes iguales), carga fraccional como
`expected`, selector en la UI con hint sobre equilibrios múltiples. Converge en
12–15 iteraciones; 6 tests unitarios, incluido «es el límite del logit al
escalar las utilidades».

Follow-up de UI pendiente: bajo Wardrop la medida emparejada de bienestar es la
utilidad máxima media, no el logsum — la tabla de resultados sigue mostrando el
excedente logsum. El costo generalizado percibido sí muestra el fenómeno (ver
§5), así que no es urgente.

### 4.4 Deuda de documentación

Buena parte se pagó el 2026-08-16 (fase `F9`): los nueve documentos caducos se
movieron a **`docs/archivo/`**, cada uno con una nota al inicio que dice por qué
caducó y qué lo reemplaza. Entre ellos `archivo/AUDITORIA_TRANSPORTE.md`, cuyas
magnitudes ya no se reproducen.

`COMPARACION_ORIGINAL.md` **se regeneró**: §4.1 tenía repartos anteriores al
arreglo del metro sin tramo en tren y ahora está re-medido (la §6.4 del bid-rent
reproducía ya al decimal). Ojo: el script **necesita `reference/`** — ese
directorio está en `.gitignore`, así que no viaja entre máquinas y hay que
reponerlo a mano desde el repo original.

**Lo que sigue debiendo:** `ANALISIS_SENSIBILIDAD.md` se actualizó parcialmente
el 2026-08-10 (barrido de `sensibilidad.py`, línea base y fila `assignment`), y
sus tablas de `frec_max` y `cap_bici` **siguen sin re-medir**.

---

### 4.5 Frontend del módulo de transporte — dónde quedó

Sesión del 2026-08-10, commits `3e32bbe`, `2b07d85`, `2b803d9`, `84913c0`,
`6d70b00`. Lo hecho está en esos mensajes; acá va **lo que falta**.

**Cambió el modelo, no solo la presentación.** `84913c0` marca el metro
infeasible cuando `tren_viaje <= 0` (la estación más cercana es la del CBD, o
sea el destino: caminar hasta el destino sin subirse a nada). Antes eso era
factible y además esquivaba el corte de 30 min de la caminata. Efecto: metro de
36,99 a 32,79 en la línea base; con 3 estaciones, las celdas a 12/14/15 km
pasaban de 16,9/15,6/10,9% de metro a 0%.

Pendientes, en orden de valor. **Los cuatro primeros están cerrados**: los dos
últimos se hicieron, y los dos primeros nunca fueron pendientes — se escribieron
desde los mensajes de commit sin volver a correr la app, y la app ya los tenía.
La lección se generaliza: **esta lista se verifica en pantalla antes de
escribirla**, porque un pendiente falso cuesta una sesión entera.

1. ~~**Figuras que faltan.**~~ **Las dos ya existían**; este punto se escribió
   desde los mensajes de commit sin volver a abrir la app. Medido el 2026-08-15:

   - **Evolución del reparto modal por iteración**: `ConvergenceTrace` dibuja un
     `AreaChart` apilado con los cinco modos al lado del residuo, rotulado
     «modal split por iteración». No es reciente — entró en `95944d3`. Era falso
     que «la traza solo grafica el residuo».
   - **Tiempos por modo y ubicación**: la cinta del hero (`CityStrip`) ya va
     envuelta en `ExportableFigure` (`SandboxPage.tsx`, el botón «Exportar
     figura: Ciudad — Todos» está en el DOM), con selector
     Todos/Auto/Metro/Bici/Caminata/Espera tren, tooltip de los cuatro modos a
     la vez, línea de corte de factibilidad y marcadores de estación.

   Lo único que sigue en pie es que esa cinta **no tiene número de figura** ni
   lugar en la secuencia FIG. 00-06: vive en el hero. Promoverla es decisión de
   diseño, no un hueco del modelo — o el hero se queda sin figura, o queda
   repetida.

2. ~~**La animación de FIG. 01 nunca se vio correr.**~~ **Corre.** Verificada el
   2026-08-15 con el panel del navegador visible, instrumentando la suma de
   alturas de las barras: 316 → 603 → 1.149 → 2.143 → 3.711 → 5.973 → 8.897 px
   en 1,75 s (`DURACION_MS = 1800`), cierra en el valor final exacto (9.368) y
   el botón queda deshabilitado durante el barrido. `requestAnimationFrame`
   entrega frames sin problema; los 0 frames de la nota anterior eran el panel
   oculto, no un defecto del componente.

3. ~~**`SidebarSection` se usa fuera del sidebar.**~~ **Hecho** (`f924c07`):
   renombrado a `CollapsibleSection`. Las clases CSS siguen siendo
   `sidebar-section*` a propósito — cambiarlas es tocar estilos, no nombres.

4. ~~**Formato.**~~ **Hecho** (`3797dee`): `.prettierrc` con las opciones
   explícitas (el drift venía de no tener config y depender de la versión del
   binario) y prettier pasado sobre 55 archivos del web. El alcance lo manda
   `.prettierignore`, no el glob del script, así vale también para el editor.
   **Queda afuera `*.md`**: prettier expande cada tabla al ancho de su columna
   más larga — 184 líneas cambiadas solo en este documento, con filas de 200+
   caracteres. Y también `apps/web/e2e/fixtures` y `docs/_datos_informe`, que
   los escribe Python con `json.dumps(..., indent=1)`: reformatearlos los deja
   sucios hasta que el generador los revierte.

5. **`main` quedó muy atrás.** Sin divergencia; es fast-forward cuando se decida
   (ver la cabecera de este documento).

---

## 5. Downs-Thomson: RESUELTO — se observa, y se sabe exactamente cuándo

Búsqueda sistemática en `scripts/buscar_downs_thomson.py` (10 escenarios × 3
equilibrios × barrido de capacidad, mecanismo verificado en cada tramo, y los
hallazgos reverificados con `max_iter=120` y `tol=0.02`). El paper original
(`reference/overleaf_original/main.tex`) es logit puro y no menciona la
paradoja: era un objetivo nuestro, no una promesa de los autores.

> **Nota de nombre.** En esta sección «Wardrop» es el nombre que tenía entonces
> el método hoy llamado `todo_o_nada`. La medición está más abajo («¿es Wardrop?
> No»): el método NO produce un equilibrio de Wardrop, y por eso se renombró. Las
> mediciones de la paradoja valen igual — dependen de que el grupo salte entero
> de modo, no de que el equilibrio sea el de Wardrop.

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

#### Auditoría del 2026-08-15: el mecanismo no es arbitraje

La intuición de arriba sobrevive, pero **el nombre del mecanismo estaba mal**, y
el docstring del core llegaba a afirmar que el punto fijo era un equilibrio de
Wardrop con «todo modo usado al mismo costo generalizado». Es falso. Medido con
`scripts/auditoria_wardrop.py` sobre la base default (942 grupos, 29.002
agentes, converge en 16 iteraciones):

| corte | resultado |
|---|---|
| costo generalizado del modo elegido, entre grupos | media 34,6 min, **desv. est. 15,3** (sería ~0 con arbitraje poblacional) |
| ídem, bajo `expected` | desv. est. 15,7 — pasar a determinístico **casi no la mueve** |
| costo por modo usado | caminata 12,1 · auto 25,0 · bici 37,6 · metro 44,3 — **32 min de diferencia** entre modos usados a la vez |
| distancia a la indiferencia | **91% de los agentes** a más de 0,5 min; sólo 2,8% a menos de 0,1 |

La razón es estructural: con todo-o-nada cada grupo pone el 100% de su masa en
**un** modo, y un par origen-destino con una sola alternativa usada satisface la
condición **al vacío**. El principio, en su enunciado formal, es por par OD:

> *Every used route connecting an origin and destination has equal and minimal
> travel time.* — Boyles, Lownes & Unnikrishnan, «Transportation Network
> Analysis», Corollary 4.1, p. 89

con la aclaración explícita de que rutas usadas de pares OD **distintos** pueden
tener tiempos distintos. Acá cada celda es un origen y cada estrato una clase,
así que el reparto agregado es **composición entre 942 grupos**, no arbitraje.

**Reformulación del mecanismo**: al agregar pistas, los grupos que estaban cerca
de su umbral de indiferencia saltan ENTEROS de modo, en vez de trasvasar una
fracción como haría el logit. El 8,6% de agentes a menos de 0,5 min de la
indiferencia es la reserva que puede saltar. La paradoja aparece cuando ese
salto degrada al metro (Mohring) más de lo que la pista mejora al auto. La
etiqueta de la UI pasó a «determinístico (todo-o-nada)», y en la fase `F3` de la
cirugía el valor del schema pasó de `"wardrop"` a `"todo_o_nada"`. La
compatibilidad con escenarios guardados se rompió **a propósito** (decisión
tomada al planificar la cirugía): un `.ttrq.json` anterior falla con un error
explícito en vez de migrarse en silencio.

**Y la multiplicidad de equilibrios tiene explicación teórica**, no es una
rareza empírica del todo-o-nada: la unicidad del equilibrio de usuario exige
funciones de costo **estrictamente crecientes** en el flujo (Proposición 5.2,
p. 120 — la prueba necesita el Hessiano de Beckmann definido positivo). El metro
tiene `espera = 30·K / carga`, **decreciente** en su propia demanda. Viola la
hipótesis, así que la unicidad no está garantizada. La existencia sí (Prop. 5.1,
p. 120, sólo pide continuidad). No es un defecto a corregir: **es la condición
que hace posible Downs-Thomson**. El libro lo advierte en general (p. 104): los
distintos enunciados del principio «agree in the standard case of continuous,
increasing […] separable» link performance functions, «but the equilibria can
differ if these assumptions are violated».

#### El MSA promedia la variable equivocada — medido, y casi no importa

El MSA promedia **tiempos** (`msa.py`, `t_auto_ac = f·t_nuevo + (1−f)·t_ac`),
mientras que el algoritmo estándar promedia **flujos** y recalcula los tiempos
desde el flujo promediado (§6.2, p. 159). La justificación de convergencia —que
`x*−x` es dirección de descenso de la función de Beckmann (p. 160)— se apoya en
promediar la variable primal, así que no cubre nuestro esquema.

Está implementado detrás de `promediar_flujos` en `_iter_loop` /
`iter_msa_desde_suelo`. **No es un campo del schema a propósito**, pero la razón
cambió: antes era que había que tocar a mano los espejos TS y el golden; hoy el
contrato se genera solo (`sync:core`), así que exponerlo sería barato. Se deja
fuera porque es una **decisión numérica interna**, no una palanca pedagógica:
ponerla en la UI invita a comparar dos esquemas de promediado que deberían
converger al mismo equilibrio. Ninguna ruta de producción lo activa; el default
es el comportamiento histórico y reproduce la línea base al segundo decimal.

Reparto en % sobre los cuatro modos (sin teletrabajo en el denominador):

| método · esquema | auto | metro | bici | caminata | v/c | iter |
|---|---|---|---|---|---|---|
| expected · tiempos | 21,04 | 40,71 | 28,35 | 9,90 | 1,38 | 7 |
| expected · flujos | 21,46 | 40,27 | 28,42 | 9,86 | 1,41 | 7 |
| todo_o_nada · tiempos | 28,91 | 41,22 | 21,78 | 8,08 | 1,89 | **16** |
| todo_o_nada · flujos | 29,27 | 39,57 | 21,97 | 9,19 | 1,92 | **11** |
| montecarlo · tiempos | 21,29 | 40,33 | 28,29 | 10,09 | 1,40 | 7 |
| montecarlo · flujos | 21,33 | 40,53 | 28,39 | 9,75 | 1,40 | 11 |

**Máxima diferencia de reparto: 0,44 pp bajo logit, 1,66 pp bajo determinístico.**
O sea: el punto fijo es esencialmente el mismo y el esquema actual no está
produciendo un equilibrio distinto, sólo una trayectoria distinta. **La
calibración de agosto no está comprometida.** Sí conviene tener presente que
1,66 pp es del mismo orden que los efectos finos de §5 (el metro cae ~5 pp entre
2 y 3 pistas), así que para lecturas al límite el esquema importa.

Dato a favor del estándar: bajo determinístico converge en **11 iteraciones en
vez de 16**, como predice la teoría. No se cambió el default — es decisión de
Leandro, y mover los tres métodos por 0,4 pp no se justifica solo.

#### Por qué no se igualan costos dentro de cada par OD (corte D)

La igualación necesita que el reparto de un par OD mueva **los costos que ese
par OD enfrenta** — el término que en el ejemplo del libro (p. 91) hace que
`t1(h1) = t2(7000−h1)` tenga solución interior. Medido: se muda el grupo ENTERO
a su segundo mejor modo y se compara cuánto encarece ese modo (Δcosto) contra la
brecha que habría que cerrar. `razon = Δcosto / brecha`; el reparto interior
existe si `razon >= 1`.

Sobre los 822 grupos con destino congestionable (24.572 agentes):

| franja | razón media |
|---|---|
| **marginales** (brecha < 1 min) | **1,168** |
| todos | 0,218 (mediana **0,004**) |
| **lejanos** (brecha ≥ 5 min) | **0,019** |

Sólo el 5,4% de los agentes tiene `razon >= 1`; el 11,9% pasa de 0,5.

La lectura correcta tiene dos mitades, y la primera **contradice la intuición de
que los grupos son demasiado chicos**:

1. **Para la franja marginal la igualación SÍ es alcanzable** (razón 1,17): un
   grupo de ~98 agentes mueve el costo de la bici en su celda ~0,5 min, que es
   justo su brecha. Ahí existe un reparto interior que iguala, y el todo-o-nada
   lo pasa por alto: manda el grupo entero a una esquina que oscila. **Eso es el
   hueco real**, y explica las 16 iteraciones contra 11.
2. **Para el resto no existe reparto interior**, y no por el algoritmo: un grupo
   a 15 km del CBD tiene una brecha de 8-15 min y poder para mover 0,02 de eso.
   Ningún reparto lo iguala. Eso **es correcto y deseable** — es lo que hace un
   modelo espacial con estratos: la heterogeneidad es real, no ruido a suavizar.

**Y la limitación de fondo, que es la misma de siempre:** no se puede igualar par
por par, porque el problema **no es separable**. El costo del auto en la celda 73
depende del flujo ACUMULADO que pasa por ella, que incluye a todas las celdas
entre ella y el CBD. Igualar dentro de cada par OD exige resolver los 822
simultáneamente — que es exactamente lo que hace un algoritmo de equilibrio de
verdad (Frank-Wolfe, gradient projection; §6.2-6.3) sobre la formulación de
Beckmann. Y no se puede aplicar acá porque **el metro viola la monotonía**
(`espera = 30K/carga`, decreciente) y sin eso el problema de Beckmann no es
convexo (Prop. 5.2, p. 120).

O sea: la razón última por la que no igualamos costos por par OD es la misma que
hace posible Downs-Thomson. El efecto Mohring rompe la convexidad, y sin
convexidad no hay algoritmo de equilibrio con garantías. **Se puede tener el
fenómeno o el algoritmo con garantías, no los dos.**

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

- ~~**El contrato NO cubre los 42 betas.**~~ **Resuelto en `F4`**: los tipos, los
  defaults, los presets y las constantes se **generan** desde Pydantic a
  `apps/web/src/lib/gen/`. Ya no hay dos listas de betas que puedan divergir,
  hay una. Lo que sí hay que respetar: **no editar `src/lib/gen/`** (se
  sobreescribe) y correr `sync:core` tras tocar el núcleo.
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
- ~~**El trace tiene DOS espejos.**~~ **Resuelto en `F2`**: la forma JSON vive
  una sola vez, en `titirilquen_core/serializacion.py`, y la usan tanto FastAPI
  como el worker. Era el espejo más peligroso —uno de los dos vivía dentro de un
  string de Python embebido en TypeScript, que ninguna herramienta revisa— y
  estaba **desincronizado**: con `engine: "api"` los KPIs de bienestar salían
  todos en 0, sin error.
- **El espejo que queda es `utility.ts`.** Reimplementa el cálculo de utilidad
  para el inspector didáctico, que necesita ser síncrono. Está pineado con
  `e2e/fixtures/utility-golden.json` (27 casos): si diverge del núcleo, el test
  falla. Lo mismo `citySupply.ts` con su golden de oferta.
- **`extra="forbid"`**: quitar un campo del schema rompe la importación de
  escenarios guardados. Agregar uno nuevo con default es seguro. Desde `F3` **no
  hay migraciones**: un `.ttrq.json` de un schema anterior falla con un error
  explícito, a propósito.
- **No escribir archivos con acentos desde PowerShell.** `Get-Content` +
  `Set-Content` los codifica dos veces y deja el archivo en mojibake. Usar las
  herramientas de edición o Python con `encoding='utf-8'` explícito.

---

## 8. Recorrido de esta sesión

De más reciente a más antigua:

| Commit | Qué |
|---|---|
| `6d70b00` | El umbral de sensibilidad se indexa por v/c, no por densidad |
| `84913c0` | Sin tramo en tren no hay viaje en metro + cinta de tiempos interactiva |
| `2b803d9` | El v/c del metro se llamaba «Frecuencia metro» y no es una frecuencia |
| `2b07d85` | Cada cifra del resultado en un solo lugar (deduplicación) |
| `3e32bbe` | FIG. 02 mostraba la magnitud equivocada; la convergencia no se validaba |
| `4598f1d` | Traducir las cadenas de interfaz que seguían escritas en el código |
| `4a3a578` | Inspector de utilidad en sync con el core; vista de ciudad unificada |
| `49872c8` | Comparación reproducible contra el simulador original |
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

---

## 9. La cirugía de arquitectura (agosto 2026)

Diez fases, `F0`–`F9`, sobre una auditoría que encontró: 2 bugs activos, 7
espejos Python↔TS mantenidos a mano (5 sin ninguna red), ~800 líneas de código
muerto, 5 campos de schema que nadie leía, 9 de 19 documentos caducos, y el
build del wheel roto en Mac.

| Fase | Commit | Qué cambió |
|---|---|---|
| `F0` | `2ec6a7e` | **Red de seguridad primero**: test de línea base, fixtures compartidas, bug de `demanda_estrato`, build por `uv` |
| `F1` | `68f8f0a` | Borrar el código muerto **verificado** (componentes, funciones del núcleo, rutas de la API) |
| `F2` | `6f97f9b` | Un solo serializador, en el núcleo (`serializacion.py`) |
| `F3` | `104e33e` | Cirugía del schema: campos muertos fuera, `wardrop` → `todo_o_nada`, `$schema` a v3 |
| `F4` | `fa3cadc` | **El contrato TypeScript se genera desde Python** (`tools/genera_contrato.py` → `src/lib/gen/`) |
| `F5` | `0a5740a` | El bienestar se calcula en el núcleo (`bienestar.py`); `utility.ts` pineado con golden |
| `F6` | `2000e7c` | Saneo del núcleo y de los scripts (`resolver_oferta`, `scripts/_comun.py`) |
| `F7` | `217c59d` | Tests de los huecos que quedaban (16 sobre el equilibrio) |
| `F8` | `ec2228e` | Una sola puerta al motor (`lib/api.ts`) y los modos en un solo lugar (`lib/modos.ts`) |
| `F9` | este commit | Documentación: archivar lo caduco, arreglar enlaces, `CLAUDE.md` canónico |

### Los invariantes que quedaron, y cómo no romperlos

1. **La línea base no se mueve.** Auto 16,95 · metro 32,79 · bici 22,84 ·
   caminata 7,98, seed 42, tol 0,1, en `tests/test_linea_base.py`. Un refactor
   que la mueva más de 0,1 pp no era refactor.
2. **El contrato se genera, no se escribe.** `sync:core` tras tocar el núcleo; el
   CI lo verifica con `git diff --exit-code`. Las divergencias intencionales
   web↔núcleo están declaradas y comentadas en `src/lib/overrides.ts`, no
   escondidas en una lista dentro de un test.
3. **Una sola puerta al motor.** `lib/api.ts`. Ninguna página decide si corre
   local o contra la API, ni llama al worker directo.
4. **La matemática vive solo en Python.** Si la UI necesita un número nuevo, se
   calcula en el núcleo y se expone por `serializacion.py`.

### Lo que se rompió a propósito

Los `.ttrq.json` y los links `?s=` guardados **antes** de agosto 2026 ya no
cargan: fallan con un error explícito. Fue una decisión al planificar (romper sin
migración) y es lo que permitió borrar los campos muertos y renombrar el método
sin arrastrar cinco funciones de migración.

### Lo que deliberadamente NO se hizo

No se unificaron las tres máquinas de estado de los stores, ni las dos semánticas
de aplicar-preset, ni se reorganizó `viz/` en subcarpetas, ni se purgaron las
~85 claves i18n huérfanas una a una, ni se optimizó el triple recorrido de grupos
del MSA. Son rediseños o micro-optimizaciones, no espejos rompibles: el criterio
fue tocar lo que puede desincronizarse en silencio y dejar quieto lo demás.

### Dos lecciones que costaron caro

- **Un grep de una clave i18n literal miente.** Varias se construyen por
  interpolación (`` t(`equilibrium.modo_${m.toLowerCase()}`) ``). Borrar una
  familia «huérfana» dejó los botones mostrando claves crudas, y lo detectó el
  navegador, no la suite.
- **Ningún test corre en Pyodide.** Alinear `pydantic>=2.8` en el núcleo dejó el
  motor por defecto sin arrancar (Pyodide 0.26.4 trae 2.7.0 precompilado y
  `micropip` aborta) con los 105 tests en verde. Lo que corre en el navegador se
  verifica en el navegador.

---
