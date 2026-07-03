# Cambios — Uso de Suelo como entrada de la ciudad

Registro de las modificaciones para que el módulo de **Uso de Suelo** pase a ser
el punto de entrada que define las características de la ciudad (forma, estratos y
densidad) y alimente al módulo de **Transporte** (Sandbox).

Fecha de inicio: 2026-06-30. Rama: `ciudad-equilibrio-mejoras`.

> **Estado vigente (2026-07-03).** Este es un registro cronológico; algunas
> fórmulas de secciones anteriores quedaron **superadas**. La verdad actual del
> módulo:
> - **Densidad por celda** = gradiente de **Clark geométrico** en la distancia al
>   CBD (independiente del precio, de `ρ` y de la composición `Q`). NO es
>   `Σ_h Q·δ_h` ni endógena del precio: la sección «Formulación de la densidad por
>   celda» de más abajo es historia superada.
> - **Envolvente de las figuras de población por celda** (`StratumDistribution`,
>   `StrataHeatmap`) = la **oferta `S`** («forma de la ciudad», `smoothSupply`), no
>   `densidad_celda`. Esto supersede la entrada «FIG. hogares: envolvente =
>   densidad_celda» de «Figuras alineadas». Coincide con cómo el core reparte
>   hogares (`asignar_hogares_simple` usa `S`); la densidad de Clark queda solo
>   para la FIG. de densidad.
> - **Solver**: la app corre siempre **logit** (el heteroscedástico existe en el
>   core pero no se expone en la UI).

## Objetivos

1. Reordenar las pestañas del banner: **Uso de Suelo primero**, antes de Transporte.
2. En la vista de Uso de Suelo se define la **proporción de estratos** y la
   **densidad** de la ciudad.
3. La densidad queda **amarrada a la proporción de estratos por celda**.
4. Solo se ofrece el solver **logit** (el heteroscedástico no está resuelto).
5. La configuración de esta vista **alimenta al módulo de transporte**.

## Formulación de la densidad por celda

El equilibrio de uso de suelo produce `Q[h,i]` = composición de estratos en cada
celda `i` (las columnas suman 1). Se introduce una **densidad característica por
estrato** `δ_h` (hab/km), configurable en la vista. La densidad de cada celda es
el promedio de las densidades por estrato ponderado por la composición local:

```
densidad_celda(i) = Σ_h Q[h, i] · δ_h
```

Así la densidad deja de ser un escalar plano (`densidad_hab_km`) y pasa a ser un
**perfil por celda** derivado de cómo se reparten los estratos en el espacio.
Las proporciones `π_h` (suman 1) definen la mezcla y alimentan `share_estratos`
del módulo de transporte.

## Estado de los cambios

### Hecho

- **Reorden de pestañas** — `apps/web/src/components/RootLayout.tsx`: el item
  `/land-use` se mueve antes de `/sandbox`. Orden: Tutorial · Uso de Suelo ·
  Sandbox · Coupled · Compare · About.
- **Solver logit fijo** — se quita el toggle de solver de la UI:
  - `apps/web/src/components/modules/LandUseBuilder.tsx`: eliminado el selector
    `heteroscedastic`/`logit`; el slider `λ` queda siempre activo.
  - `apps/web/src/lib/defaults.ts`: `solver: "logit"` por defecto.
  - El core Python conserva `solve_heteroscedastic` (trabajo no resuelto, no se
    borra).

- **Densidad por estrato `δ_h` (core + config + UI)**:
  - `packages/.../land_use/config.py`: campo `densidad_estrato: tuple[float,
    float,float]` (default `(300,500,800)`, placeholder de calibración) + validador
    de positividad.
  - `packages/.../land_use/ciudad.py`: método `densidad_por_celda()` →
    `δ @ Q` (perfil hab/km por celda).
  - Respuesta de `solveLandUse` extendida con `densidad_celda` en **ambos** paths:
    `apps/api/src/api/main.py` y `apps/web/src/workers/pyodide.worker.ts`.
  - Espejo TS: `densidad_estrato` en `LandUseConfig` y `densidad_celda` en
    `LandUseSolveResponse` (`types-v2.ts`); default en `defaults.ts`.
  - UI: slider `δ_h` por estrato en `LandUseBuilder.tsx` + i18n
    (`param_densidad`, `densidad_hint`).
  - Validado por smoke test del core: `densidad_por_celda()` devuelve un perfil
    acotado entre las densidades por estrato según la composición local.

- **Consumo en transporte (opción A) — feed unidireccional por celda**:
  - `packages/.../population.py`: `generar_poblacion_desde_densidad(Q, δ, Δx,…)`
    → `N[h,i] = round(Q[h,i]·δ_h·Δx)` (total por celda = `densidad_celda·Δx`).
  - `packages/.../equilibrium/msa.py`: `iter_msa_desde_suelo(sim, land_use_cfg,
    trace)` resuelve el suelo una vez (misma T por defecto que la pestaña Uso de
    Suelo) y corre el MSA con esa población; reutiliza `_iter_loop`.
  - Worker Pyodide: `iter_from_json_suelo({config, land_use})` + el mensaje
    `simulateStream` lleva `land_use` opcional; `pyodide-engine.ts.simulateStream`
    acepta `landUse?`; `SandboxPage` pasa la config de suelo del store.
  - El transporte standalone ya **no** usa `densidad_hab_km` plana ni
    `share_estratos` global: la población viene del suelo.
  - Validado: smoke test del core genera 12.098 agentes desde la densidad por
    estrato (alto/medio/bajo coherente con δ y la mezcla H), 50 celdas con origen.
- **Visualización `densidad_celda`** en Uso de Suelo: componente
  `viz/DensityProfile.tsx` + panel "Densidad por celda" en `LandUsePage`.
- **Proporciones como fuente única / limpieza de Sandbox**:
  - `CityBuilder.tsx`: se quitan el slider de densidad plana y la sección de
    estratos; nota apuntando a Uso de Suelo. Presets ahora solo ajustan el largo.
  - `CityPreview.tsx`: la composición sale de las proporciones de Uso de Suelo
    (`H_por_estrato` normalizado) y la población del perfil `densidad_celda` del
    último resultado de suelo (con fallback si no hay corrida).
- **Contrato TS↔Python** (`apps/web/e2e/`): golden `defaults-golden.json` con
  `densidad_estrato`; divergencia intencional `land_use.solver` (py
  `heteroscedastic` / ts `logit`) en `contract.spec.ts`.
- **Wheel recompilado** (`npm run build:core-wheel`) para que Pyodide use el core
  nuevo.

### Verificación

- `tsc --noEmit` limpio; ESLint 0 errores (1 warning preexistente ajeno).
- Smoke tests del core (importación, `densidad_por_celda`, `iter_msa_desde_suelo`)
  OK con el python del sistema.
- **Pendiente de entorno**: no había `pytest`/`uv`/venv, así que la suite
  `pytest` completa no se corrió; el golden de contrato se editó a mano para
  igualar los defaults actuales de Pydantic (regenerable con
  `tests/test_contract_frontend.py`).
- **Pendiente manual**: click-through en el navegador (Uso de Suelo → correr →
  Sandbox → correr) para confirmar opción A end-to-end en Pyodide.

## Fix — "peineta" en la distribución de estratos

**Síntoma:** al definir la proporción de estratos y resolver el equilibrio, la
distribución espacial aparecía como una "peineta" (saltos entre celdas contiguas)
en vez de pseudocontinua.

**Causa:** el panel `StratumDistribution` pintaba la realización **discreta**:
en Uso de Suelo/Compare, el muestreo estocástico del core
(`asignar_hogares_simple`, `rng.choice` por hogar); en Coupled, el redondeo
entero por celda de `reconstructParcelas` (`round(S·Q)`). Donde hay pocos hogares
por celda (periferia, grilla fina), ambos saltan entre estratos en celdas
vecinas. El equilibrio en sí (`Q[h,i]`, composición por celda) **ya es suave**.

**Arreglo:** dibujar la ocupación **esperada** en floats `S[i]·Q[h,i]` (sin
redondear ni muestrear) — helper `expectedComposition(Q, S)` en
`lib/citySupply.ts`, nuevo prop `composition` en `StratumDistribution` (preferido
sobre `parcelas`). Aplicado en `LandUsePage`, `ComparePage` y `CoupledPage`. La
suma por celda sigue siendo `S[i]`, así que la envolvente coincide con la oferta;
solo la composición pasa a ser pseudocontinua. `reconstructParcelas` quedó sin
uso (se conserva, no se borró).

## Vista pre-equilibrio (población inicial)

Antes de resolver, la vista de Uso de Suelo muestra el **estado inicial**: todas
las celdas con la **misma proporción de estratos** (las proporciones globales
`π_h = H_h/ΣH`), sobre el perfil de oferta `S(d)`.

- `comp_inicial[i] = S_i·π_h`, con `S_i` del mirror `supplyVector` (determinista,
  sin resolver el equilibrio) — reusa `StratumDistribution`.
- Panel "Población inicial por celda" en `LandUsePage` (rama sin resultado), junto
  a la forma de la ciudad. Se actualiza en vivo al mover proporciones/forma.
- Hace visible el contraste con el post-equilibrio: el bid-rent reordena esa
  mezcla uniforme en el espacio (alto→CBD, bajo→periferia).
- Verificado en navegador: bandas proporcionales uniformes (10/40/50 % con
  H=1000/4000/5000) siguiendo la envolvente de oferta.

## Módulo de ciudad movido a Uso de Suelo

La configuración completa de la ciudad ahora se define en **Uso de Suelo** y es
input de Transporte:

- El `CityBuilder` (presets + largo, n° celdas, pendiente, factor de teletrabajo)
  se renderiza en el sidebar de `LandUsePage`, editando `SimulationConfig.city`
  del `simulationStore` (mismo store que consume Transporte).
- En `SandboxPage` se retiró `CityBuilder`; queda una **nota read-only** con la
  geometría actual apuntando a Uso de Suelo (`city_params.defined_in_land_use`).
- Junto con lo anterior, en Uso de Suelo quedan: geometría (largo, celdas,
  pendiente, teletrabajo) · forma de la ciudad · proporciones y densidad por
  estrato. Transporte solo edita oferta (pistas/metro/bici), economía y el
  criterio de equilibrio.
- Verificado en navegador: los 4 controles aparecen en el sidebar de Uso de Suelo;
  Transporte muestra solo la nota.

> Nota menor pendiente: el hint de `n_celdas` aún dice "la población la fija la
> densidad × largo", desactualizado (ahora la población sale del perfil
> `densidad_celda` del uso de suelo). Copy secundario, no bloqueante.

## Reparametrización de la ciudad: densidad como driver (H derivado)

Se resolvió la doble contabilidad de población (conteos `H_por_estrato` vs
densidad `δ_h`). Ahora la **densidad es la variable primitiva** y el total se
deriva; ver la nota de modelo en `MATHEMATICAL_MODEL.md`.

- **Panel "Población"** (reemplaza los sliders de H): **proporciones `π_h`** (la
  mezcla) + **densidad por estrato `δ_h`** (hab/km). Las proporciones se editan y
  se mapean internamente a `H = round(π·N_REF)` con `N_REF = 10 000` (referencia
  numérica; **no afecta a `Q`**, que solo depende de las razones). El solver
  queda intacto.
- **Total derivado, visible:** `Población total ≈ largo · Σ_h π_h·δ_h` (densidad
  media ponderada). Ej.: `π=(.1,.4,.5)`, `δ=(300,500,800)` ⇒ 630 hab/km ⇒ 20 km ·
  630 = **12 600**. Una sola respuesta a "cuánta gente vive acá".
- **Parcelas con dimensión:** en `CityBuilder`, "celdas" → **"parcelas"**, con
  `Δx = largo/n` mostrado ("cada parcela ≈ X m"). El hint de `n` se corrigió: la
  población la fija densidad × largo, así que **no cambia con `n`** (solo la
  resolución).
- **Paneles reordenados:** `Ciudad` (geometría) · `Población` (proporciones +
  densidad + total) · `Forma de la ciudad` (perfil de oferta) · `Parámetros de
  puja / bid-rent` (β + α/ρ/λ/y por estrato).
- Sin cambios al core → sin recompilar wheel. Verificado en navegador
  (`tsc` limpio, sin errores de consola): total 12 600 correcto, parcelas Δx=100 m.

## Fix — "escalera" en la campana de oferta

**Síntoma:** al simular una ciudad (p. ej. forma normal), la campana de la
distribución se veía como escalera (mesetas), no suave.

**Causa:** la oferta `S_i` del core (`generar_oferta`) está **cuantizada a
enteros** (mayor residuo, `Σ S = ΣH`). Con `N_REF = 10 000` sobre ~200 parcelas,
el pico es ~84 y el flanco baja `70,70,69,68…` → mesetas de enteros repetidos.
La figura usaba ese `S` entero como envolvente.

**Arreglo:** renderizar el perfil de oferta **suave** (float, sin discretizar) —
helper `smoothSupply(forma, L, CBD, σ, param, N)` en `lib/citySupply.ts`
(`cityShapeWeights` normalizado, CBD vacío, sin redondeo). Es un espejo de
presentación (igual que `CityShapePreview`); el core sigue resolviendo con la
oferta entera. En `LandUsePage`, tanto la composición post-equilibrio
(`S_suave·Q`) como la pre-equilibrio (`S_suave·π`) usan la envolvente suave.
Verificado: flanco `89.1, 88.0, 86.9, 85.7…` (float, sin mesetas).

> Pendiente: `ComparePage` y `CoupledPage` aún usan la oferta entera en
> `StratumDistribution` (misma escalera). Aplicar `smoothSupply` ahí para
> consistencia (no bloqueante; requiere la config de forma por escenario).

## Densidad endógena: gradiente de Clark (por distancia)

La densidad por celda pasó a ser **endógena, decreciente con la distancia al CBD**
(gradiente de Clark / Alonso-Muth-Mills), reemplazando la densidad por estrato.

- **Parámetros:** `densidad_max` (hab/km en el CBD) y `densidad_min` (periferia),
  reemplazan `densidad_estrato`. Forma exponencial negativa anclada a los extremos:
  `dens(d) = densidad_max·(densidad_min/densidad_max)^(d/d_max)` — `ciudad.py
  densidad_por_celda`.
- **Independiente del estrato y ROBUSTO:** depende solo de la geometría, no del
  precio ni de `ρ`, así que **siempre es centro-denso** (no se invierte). La
  composición `Q` solo reparte la población de cada celda entre estratos.
- **Intento previo (revertido):** se probó densidad `∝ precio del equilibrio`,
  pero el precio incluye la penalización de densidad `−ρ·S/Δx` (escala con
  `N_REF`), que **invierte** el gradiente (ciudad "dona") con `ρ` alto o escala
  grande. Se descartó por frágil; el diagnóstico quedó en el historial.
- **Población del transporte:** `generar_poblacion_desde_densidad(Q,
  densidad_celda, Δx)` → `N[h,i] = round(Q[h,i]·densidad_celda[i]·Δx)`.
- **UI:** sliders `densidad_max`/`densidad_min` (reemplazan los 3 de δ por
  estrato); golden + contrato actualizados; wheel recompilado.

### Figuras alineadas

- **FIG. hogares** (`StratumDistribution`): envolvente = `densidad_celda·Δx`
  (gradiente), no la oferta. Coincide con el perfil de densidad.
- **FIG. densidad** (`DensityProfile`): el gradiente de Clark.
- **FIG. heatmap** (`StrataHeatmap`, nueva): composición de estratos sobre la
  ciudad, **ANTES** (mezcla uniforme) vs **DESPUÉS** (ordenada por bid-rent). Con
  densidad fija, el equilibrio cambia *quién vive dónde*, no *cuántos* — el
  heatmap lo muestra. Colores del tema leídos por `getComputedStyle`.
- Mirror de presentación `densityGradient` en `citySupply.ts` para la vista
  pre-equilibrio (sin resultado).
- Verificado en navegador: densidad 789→197 (centro denso), invariante a `ρ` y
  escala; heatmap antes-uniforme → después-ordenado (alto centro, bajo periferia).

## Notas de diseño

- En opción A, el transporte standalone consume la **composición `Q` por celda**
  directamente, así que `share_estratos` de `CityConfig` queda vestigial (no se
  sincroniza; el path `api` no lo usa porque `SandboxPage` corre siempre local).
  `densidad_hab_km` también queda vestigial en el schema (no se borró para no
  romper serialización/escenarios guardados).

## Decisión de arquitectura: cómo alimenta Uso de Suelo a Transporte

- **Opción A (elegida):** feed unidireccional por celda — Transporte consume
  `densidad_celda[i]` + `Q[·,i]` del resultado de Uso de Suelo, reemplazando la
  densidad plana y el share global. La heterogeneidad por celda llega a Transporte.
  El loop iterativo completo sigue viviendo en la pestaña *Coupled*.
- Opción B (descartada salvo indicación): solo sincronizar `share_estratos` y una
  densidad promedio escalar; Transporte mantendría su población plana.
