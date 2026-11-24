# Análisis pedagógico del frontend — Iteración 2 (agosto 2026)

> **⚠ ARCHIVADO — agosto 2026.** Diagnóstico y propuesta de la iteración 2; la
> implementación ya ocurrió y la cirugía de arquitectura movió o renombró buena
> parte de los archivos que cita. **Vigente:**
> [`docs/CONTINUAR.md`](../CONTINUAR.md).

Registro de fricciones `F-xx` y propuesta de rediseño. **Este documento es
diagnóstico + propuesta: nada de lo aquí descrito se implementa en la iteración 2.**
La implementación (iteración 3) se prioriza tras revisión de Leandro.

La premisa del análisis: la herramienta es **pedagógica** — el usuario objetivo es
un estudiante que entra por primera vez, y el éxito se mide en cuán rápido pasa de
«pantalla llena de sliders» a «entiendo qué palanca mueve qué resultado y por qué».

| ID | Fricción | Estado |
|---|---|---|
| F-01 | Presets invisibles (existen en código, sin UI) | **RESUELTO** (it. 3: PresetGallery en el Sandbox) |
| F-02 | Tutorial desconectado de los módulos | **RESUELTO** (it. 3: `<LoadScenario>` en las actividades) |
| F-03 | Boot de Pyodide sin precarga ni progreso | **RESUELTO** (it. 3: preboot + etapas + cancel cooperativo) |
| F-04 | Sidebar colapsado, sin CTA de simulación | P1 |
| F-05 | Errores crudos sin traducir | P2 |
| F-06 | Sin persistencia de sesión; share sin comprimir | P1/P2 |
| F-07 | Parámetros de demanda no editables en UI | P2 |

## 1. El flujo de uso actual

- Nav deliberado: Tutorial → Uso de suelo → Transporte → Ciudad en equilibrio →
  Comparar (el suelo define la ciudad que alimenta al transporte — «Opción A»).
- La ruta `/` cae en el tutorial: el aterrizaje de un estudiante nuevo es bueno.
- `StratumDistribution` (la silueta de la ciudad por estrato) aparece en las 4
  páginas y funciona como hilo visual de «la misma ciudad».
- El Sandbox corre siempre el motor Pyodide y recibe la ciudad del módulo de
  suelo (localización de equilibrio si el bid-rent corrió; mezcla π_h si no).
- Staleness bien resuelto en Sandbox/LandUse: banner + «volver a simular», las
  figuras leen `configUsed` (no la config viva).

## 2. Fricciones detectadas

### F-01 — Presets invisibles [P0]

`lib/presets.ts` (espejo de `presets.py`) define 3 ciudades (Compacta/Base/
Dispersa) y **8 políticas** (TP Gratis, Tarificación Vial, Pro-Auto, Pro-Bici,
Híbridos, Máx Metro, Ciclorrecreovía) — material pedagógico listo. **Ningún
selector los expone**: solo CoupledPage usa 4 combinaciones vía `joint-presets`.
El estudiante del Sandbox arranca de defaults y mueve sliders a ciegas, sin
escenarios con nombre que anclen la discusión («¿qué pasa con tarificación?»).
Queda además un `.preset-row` huérfano en `index.css` de una versión anterior.

**Propuesta**: galería de presets en el Sandbox (chips ciudad × política), con
descripción de una línea y el diff de parámetros vs default visible. Nota: dos
políticas tocan un parámetro inerte (`frec_max` — ver ANALISIS_SENSIBILIDAD S-05)
y deben recalibrarse al exponerlas.

### F-02 — Tutorial desconectado de los módulos [P0]

Los capítulos 1–6 no linkean a ningún módulo; el cap. 7 trae **5 actividades
guiadas** (parking, artefacto λ del logit, capacidad de ciclovía, α de Alonso,
convergencia del MSA) escritas como prosa numerada **sin mecanismo de carga**: el
estudiante debe reproducir a mano cada configuración. En sentido inverso hay un
único link módulo→tutorial en LandUsePage.

**Propuesta**: botones «Cargar este escenario» en las actividades (serializar la
config de cada actividad como `?s=` — la infraestructura ya existe) y links
contextuales «¿cómo se lee esta figura?» desde los paneles hacia el capítulo
correspondiente.

### F-03 — Boot de Pyodide sin precarga ni progreso [P0]

El worker descarga Pyodide + numpy/scipy/pydantic + el wheel (~10–20 s, CDN) al
primer «Simular»: el costo cae **dentro de la primera corrida**, el momento de
mayor abandono. Solo se muestra un texto genérico («Inicializando Pyodide…»);
existe la clave i18n `equilibrium.booting_pyodide` con la advertencia temporal
pero ningún componente la referencia. **Cancelar mata el worker** (`terminate()`)
y la siguiente corrida vuelve a pagar el boot completo. Sin red → error crudo.

**Propuesta**: precargar el worker al montar el layout (o al entrar al tutorial),
indicador de progreso por etapa (runtime/paquetes/wheel), y cancelación que
aborte la corrida sin matar el worker.

### F-04 — Sidebar colapsado, sin CTA [P1]

Todas las secciones del sidebar nacen colapsadas salvo Economía; el botón
Simular queda al fondo, tras 6 títulos. En el área principal pre-corrida no hay
ningún CTA hacia la simulación (hay KPIs en «—» y 3 hints que desaparecen con el
primer resultado).

**Propuesta**: CTA primario en el hero pre-corrida; revisar qué secciones nacen
abiertas según la actividad en curso; los hints pedagógicos no deberían
desaparecer para siempre tras la primera corrida.

### F-05 — Errores crudos [P2]

Todos los paths de error muestran `e.message` de Python/fetch sin traducir en un
callout. El import fallido de `.ttrq.json` se degrada a un «⚠» cuyo detalle solo
existe en `title` (inaccesible en teclado/móvil). Un `?s=` malformado se ignora
en silencio (catch vacío en RootLayout).

**Propuesta**: catálogo corto de errores traducidos (red/CDN, wheel, config
inválida, cancelado) con acción de recuperación; toast para import/share.

### F-06 — Sin persistencia; share pesado [P1/P2]

F5 pierde config y resultados (solo tema/idioma persisten). El único guardado es
manual (`.ttrq.json` / `?s=`). El link `?s=` serializa TODA la config (~60
parámetros, betas incluidos) sin comprimir: URLs enormes.

**Propuesta**: persistir la config (no los resultados) en localStorage con
versión de schema [P1]; comprimir el `?s=` o serializar solo el diff vs default
[P2].

### F-07 — Parámetros no editables en UI [P2]

Los ~24 coeficientes de demanda por estrato, `prob_teletrabajo`, `prob_auto` y
las velocidades globales solo entran por import/URL. Para docencia avanzada
(¿qué pasa si el estrato bajo valora más el tiempo?) hoy hay que editar JSON.

**Propuesta**: editor avanzado colapsado («modo docente») con los betas por
estrato, marcando cuáles son casi-muertos (`v_*` globales — solo iteración 0).

### Observación de rendimiento (post S-03)

Con la escala nueva (36.000 agentes) las corridas suben a ~20 s post-boot y las
figuras agente-nivel (`UtilityScatter`, con submuestreo a 2.500 pts, y los dot
plots por estrato) renderizan más puntos. No bloquea, pero si la iteración 3
sube más la escala conviene muestrear también en `ModeShareBars`.

## 3. Qué NO cambiar

- La convergencia **en vivo** del MSA (streaming por iteración) — es el corazón
  pedagógico del simulador y funciona.
- El orden del nav (suelo antes que transporte) y el feed unidireccional
  «Opción A» — coherentes con el modelo del apunte (§10).
- `StratumDistribution` como hilo visual entre módulos.
- El patrón staleness banner + `configUsed` del Sandbox.
- El contrato de espejos TS↔Pydantic vigilado por `contract.spec.ts`.

## 4. Criterios de aceptación (iteración 3)

- F-01: un estudiante puede cargar «Base + Tarificación Vial» en ≤2 clics desde
  el Sandbox, y el panel muestra qué parámetros cambió el preset.
- F-02: cada actividad del cap. 7 tiene botón que deja la app en el estado
  inicial de la actividad (verificable por e2e con `?s=`).
- F-03: al primer «Simular» tras entrar directo a `/sandbox`, el tiempo hasta la
  primera iteración visible es <5 s (worker precargado); cancelar y relanzar no
  re-descarga Pyodide.
- F-04: el CTA de simulación es visible sin scroll en viewport 1280×720.
- F-05: desconectar la red y simular produce un mensaje traducido con acción.
- F-06: F5 tras configurar conserva la config exacta (deep-equal del JSON).
