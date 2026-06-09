# Registro de Discrepancias — Código ↔ Overleaf

Este documento registra las divergencias entre el código fuente (`titirilquen-repo/`) y la documentación matemática en el Overleaf (`Titirilquen_overleaf/`). La política del proyecto es **tratar el código como fuente de verdad** y corregir la documentación matemática; este archivo preserva la trazabilidad de las decisiones.

> **Nota (auditoría 2026-06):** el Overleaf original (`main.tex`, `Suelo.tex`) se
> copió a `reference/overleaf/` (no versionado) y se auditó contra el core de esta
> web. Hallazgos: la **config de demanda** (betas, costos, velocidades,
> penalizaciones) y el flujo MSA (`f=1/(it+1)`, flujo‑libre iter 0 con
> `t_acceso=10`, `t_espera=5`) son **fieles**. Se confirmaron D‑01/D‑02/D‑03/D‑05
> y D‑08, y se detectó D‑16. Además, el Overleaf es **internamente inconsistente**
> en varios puntos (sus ecuaciones contradicen sus propios listados de código): la
> constante de pendiente (D‑01), la utilidad de bici aditiva vs multiplicativa
> (D‑02) y los umbrales/β de caminata (D‑03/D‑05). El **loop acoplado** (D‑14) no
> aparece en el Overleaf, y el **criterio de convergencia por tolerancia** (D‑10)
> no existe en el original (solo `MAX_ITER`).

Convenciones:
- **Veredicto**: `Overleaf incorrecto` | `Código incorrecto` | `Equivalentes` | `Ambos describen distinto alcance`.
- Las referencias a ecuaciones usan la numeración del Overleaf original.

---

## D-01 · Factor de ajuste por pendiente (bici, subida)

- **Overleaf** — `main.tex:166`, ecuación para `p > 0`:
  ```
  f_p = -0.0579·p + 0.09992
  ```
- **Código** — `app.py:153`:
  ```python
  factor = -0.0579 * pendiente + 0.9992
  ```
- **Análisis**: Con `0.09992` el factor para `p=0` sería ~0.1 (velocidad colapsa al 10%), físicamente absurdo. El código `0.9992` es consistente con el caso base (`p=0 → f≈1`).
- **Veredicto**: Overleaf incorrecto (error tipográfico en la constante).
- **Acción**: Documentación matemática nueva usará `0.9992`.

---

## D-02 · Penalizaciones físicas de bicicleta y caminata (forma funcional)

- **Overleaf** — `main.tex:86-88, 92-93`, sugieren formas del tipo:
  ```
  V_bici = ASC + (β_t_viaje + β_{t>10} + β_{t>20} + β_{t>30}) · t_viaje
  ```
  Donde `β_{t>10}` aparenta ser un coeficiente multiplicativo que depende de `t`.
- **Código** — `app.py:321-327`:
  ```python
  if t_bici > 45: v_bici = -9999.0
  else:
      p = 0
      if t_bici > 10: p += penal['bici_10']
      if t_bici > 20: p += penal['bici_20']
      if t_bici > 30: p += penal['bici_30']
      v_bici = betas['asc_bici'] + betas['b_tiempo_viaje']*t_bici + p
  ```
- **Análisis**: El código aplica las penalizaciones como **constantes aditivas escalonadas** (step function), no multiplicadas por `t_viaje`. La forma correcta es:
  ```
  V_bici = ASC + β_t·t  +  Σ_k 1{t > τ_k}·π_k
  ```
  con `τ ∈ {10,20,30}` y `π_k` los parámetros de `penalizaciones_fisicas`.
- **Veredicto**: Overleaf incorrecto. La ecuación multiplicativa es inconsistente con el código y con la interpretación de "penalizaciones físicas escalonadas".
- **Acción**: Reescribir ecuaciones 4 y 5 del Overleaf como sumas aditivas indicadoras.

---

## D-03 · Parámetro de sensibilidad para caminata

- **Overleaf** — `main.tex:92-93`: `V_caminata` usa `β_{t_viaje}` como coeficiente principal del tiempo.
- **Código** — `app.py:336`:
  ```python
  v_cam = betas['asc_caminata'] + betas['b_tiempo_caminata']*t_cam + p
  ```
  Usa `b_tiempo_caminata`, no `b_tiempo_viaje`.
- **Análisis**: La caminata tiene su propio parámetro de sensibilidad al tiempo, distinto del tiempo-en-vehículo. Esto es consistente con el metro (que usa `b_tiempo_caminata` para el acceso). La ecuación del Overleaf parece un copy-paste.
- **Veredicto**: Overleaf incorrecto.
- **Acción**: Corregir ecuación 5 del Overleaf.

---

## D-04 · Tiempo de espera base en metro

- **Overleaf** — `main.tex:316`:
  ```
  t_e = 30 / f_op            (si ρ ≤ 1)
  t_e = (30/f_op) · α·ρ^β    (si ρ > 1)
  ```
- **Código** — `app.py:234`:
  ```python
  t_espera_base = (1/(2*f_op))*60 if f_op > 0 else 0
  ```
- **Análisis**: `(1/(2·f)) · 60 = 30/f`. Son equivalentes. La notación del código es pedagógicamente más clara porque muestra el origen (`1/(2f)` es el tiempo medio de espera con llegada aleatoria a un servicio con frecuencia `f` por hora, convertido a minutos).
- **Veredicto**: Equivalentes.
- **Acción**: Preferir la forma `(1/(2f))·60` en la documentación nueva, explicando la derivación.

---

## D-05 · Estatus del modo caminata

- **Overleaf** — `main.tex:128`:
  > Los usuarios no pueden realizar sus viajes caminando (inicialmente)
- **Código** — `app.py:338, 367`:
  ```python
  return {"Auto": v_auto, "Metro": v_metro, "Bici": v_bici, "Caminata": v_cam}
  # ...
  modo = elegir_modo(utils, p['tiene_auto'])
  ```
  La caminata está en el choice set junto a los demás modos.
- **Análisis**: El supuesto del Overleaf se violó durante la implementación. Dado que caminata tiene corte en 30 min, en la práctica solo compite en celdas cercanas al CBD.
- **Veredicto**: Overleaf desactualizado.
- **Acción**: Actualizar supuestos. Caminata es un modo válido sujeto a `t ≤ 30 min`.

---

## D-06 · Módulo de emisiones CO₂ (no documentado)

- **Overleaf**: No menciona emisiones.
- **Código** — `app.py:806-921`:
  ```python
  FE_auto(v) = 2467.4 · v^(-0.699)   # g/km, función de velocidad local
  FE_metro   = 0.040 · dist           # kg/pax·km, lineal
  ```
- **Análisis**: Existe un módulo completo de emisiones con descomposición espacial (por celda) y velocidad local reconstruida desde la BPR inversa. Bici y caminata asumidas en cero (implícito).
- **Veredicto**: Documentación incompleta.
- **Acción**: Añadir sección "Módulo de Emisiones" al Overleaf.

---

## D-07 · Jornadas laborales (parcialmente usadas)

- **Overleaf**: Menciona `P^s_jornada` como input.
- **Código** — `Ciudad2.py:165-211`:
  ```python
  minuto_entrada = asignar_horario_entrada_discreto(...)
  duracion_min, tipo_jornada = calcular_duracion_jornada(...)
  ```
  Se generan `hora_entrada`, `hora_salida`, `duracion_horas` por agente, pero **no se usan en `calcular_utilidades`**.
- **Análisis**: Es infraestructura preparada para un modelo de elección de hora endógeno (mencionado como "característica adicional" en el Overleaf), pero inactiva.
- **Veredicto**: Dead-path preparado para expansión. No es bug, es trabajo futuro.
- **Acción**: Mantener, documentar como opcional en v2.

---

## D-08 · Método de resolución alternativo (Frechét)

- **Overleaf** — `Suelo.tex:170-174`: Reconoce que el logit es "erróneo" ante `λ_h` heterogéneo y sugiere logit-heteroscedástico como solución.
- **Código** — `Ciudad2.py:361`: Implementa `resolver_equilibrio_frechet` (marcado "MALA" en el docstring).
- **Análisis**: Existe una implementación alternativa que el propio autor considera incorrecta. Valiosa didácticamente: permite comparar ambas y discutir sus limitaciones.
- **Veredicto**: No es discrepancia sino ampliación del alcance.
- **Acción**: Mantener ambos métodos en v2 y usarlos en material didáctico comparativo.

---

## D-09 · Parámetros del loop principal hardcodeados

- **Código** — `app.py:487-500`:
  ```python
  demora_auto_tramo(..., 31, 3.5, 5, 2, ..., 0.8, 2)   # v, a, l_veh, gap, α, β
  demora_bici_tramo(..., 14, ..., 0.5, 2, 0)           # v, α, β, pendiente
  oferta_tren(..., 35, cap_tren, num_estaciones, 4.8, 6, 10, frec_max)
  ```
- **Análisis**: Parámetros físicos relevantes (velocidad máxima auto, ancho de pista, largo vehículo, gap, α/β BPR, pendiente de la ciudad, velocidad caminata) no están expuestos al usuario en la UI.
- **Veredicto**: Limitación de la interfaz, no inconsistencia del modelo.
- **Acción**: Exponer todos vía sliders en la nueva interfaz.

---

## D-10 · Criterio de convergencia ausente

- **Código** — `app.py:476`: `MAX_ITER = 12` fijo; no mide `‖T_n − T_{n−1}‖`.
- **Análisis**: El loop MSA corre un número fijo de iteraciones sin verificar convergencia real. Con `f = 1/(it+1)`, 12 iteraciones suelen ser suficientes pero no garantizadas.
- **Veredicto**: Limitación del implementación actual.
- **Acción**: ✅ **Implementado** en `titirilquen_core.equilibrium.msa`:
  - Corte cuando `residuo < tolerance` en **2 iteraciones consecutivas** (robusto
    al ruido estocástico del residual), con fallback a `max_iter`. Con
    `tolerance = 0` se mantiene el comportamiento anterior (sólo `max_iter`).
  - El **residual es de toda la red** (máximo cambio de tiempo en auto, bici o
    metro entre iteraciones), no sólo auto — antes podía ser ~0 mientras el resto
    del sistema seguía cambiando.
  - El corte se agregó también a `iter_msa` (streaming), antes ausente.
  - **Fix de reproducibilidad**: `_run_final_assignments` ahora recibe el mismo
    `rng` que generó la población (antes re‑sembraba) → `iter_msa` (vivo) y
    `run_msa` (final) producen exactamente la misma corrida y cortan en la misma
    iteración.
  - App: default `tolerance = 0.1` min y slider en el panel *Equilibrio*; el KPI
    indica si **convergió** o llegó a `max_iter`.

---

## D-11 · Código muerto en `generar_poblacion`

- **Código** — `app.py:256-278`: Define `generar_poblacion` con sampleo uniforme de estratos (`random.choice([1,2,3])`), pero el botón simular usa `mi_ciudad.generar_poblacion_completa(config)` que respeta la distribución generada por `Ciudad` (modelo Alonso).
- **Veredicto**: Código muerto.
- **Acción**: No portar a `titirilquen_core`.

---

## D-12 · Congestión de andén del metro prácticamente inactiva (+ artefacto)

- **Código** — `titirilquen_core/supply/train.py:102-113` (portado de `app.py:237-238`):
  ```python
  capacidad_maxima_sistema = frec_max * capacidad_tren
  ratio = carga_al_salir_estacion[i] / capacidad_maxima_sistema
  factor = 1.0 if ratio <= 1 else 0.5 * ratio**4   # _ALFA=0.5, _BETA=4.0
  t_espera = t_espera_base * factor
  ```
- **Análisis**:
  1. **Umbral inalcanzable en operación normal.** El factor solo supera 1 cuando
     `ratio > 2^¼ ≈ 1.19`, es decir cuando la carga de una estación supera
     `frec_max · capacidad_tren` (24.000 pax con los valores por defecto). Una
     ciudad típica tiene ~10.000 agentes en total: aunque el 100% tomara metro,
     la carga máxima (~10k) nunca alcanza el umbral → `factor = 1` siempre →
     espera plana `30/f_op`. Interpretación: mientras el sistema pueda **agregar
     trenes** (`f_op < frec_max`) la espera no crece; recién al saturar la
     frecuencia la carga extra se vuelve espera de andén.
  2. **Discontinuidad no física.** Justo pasando `ratio = 1`, el factor cae de
     `1.0` a `0.5·ratio⁴ ≈ 0.5` y solo vuelve a 1 en `ratio ≈ 1.19`; o sea, al
     iniciarse la saturación la espera *disminuye* antes de dispararse.
  3. **Bajo saturación real** (`f_op` fijada a `frec_max`, carga ≫ umbral) la
     espera crece como `ratio⁴` y domina el tiempo de viaje (cientos de minutos).
     Verificado empíricamente forzando `densidad_por_celda=300`,
     `capacidad_tren=250`, `frec_max=12`.
- **Veredicto**: Fiel al original (no es bug de la portación); limitación/artefacto
  del modelo de oferta de tren.
- **Acción**: Mantener idéntico al original (fuente de verdad). La vista
  "Espera tren" de la Figura 1 (Sandbox) permite observar el efecto bajo
  saturación. Si en el futuro se quisiera congestión visible en operación normal,
  reformular el factor como una curva continua (p. ej. BPR `1 + α·ratio^β` sin la
  caída a 0.5) y validar con los autores.

---

## D-13 · Oferta de suelo determinista + dispersión `σ` expuesta

- **Código original** — `Ciudad2.py` / `supply.py:generar_oferta_normal`: la oferta
  de vivienda `S[i]` se genera **muestreando** `N` hogares de una `Normal(CBD, stdv)`
  y haciendo un histograma por parcela. `stdv` está **hardcodeado** en
  `min(CBD, L-1-CBD)/2` (≈ L/4).
- **Análisis**:
  - Un histograma de muestras aleatorias es dentado parcela‑a‑parcela aunque la
    densidad de fondo sea una campana suave (causa visual de la "peineta").
  - `stdv` es un supuesto de **forma urbana** (compacidad ↔ dispersión de la
    oferta de vivienda), pedagógicamente relevante pero invisible en la UI.
- **Cambio (versión web)**:
  1. Se añadió `supply.py:generar_oferta_normal_det` — discretiza la pdf
     `Normal(CBD, σ)` directamente (excluyendo el CBD) y redondea por mayor
     residuo garantizando `Σ S = N`. Curva suave, sin ruido de muestreo.
  2. `LandUseCity.build` usa la versión determinista.
  3. Se expuso `σ` vía `LandUseConfig.oferta_sigma_frac` (fracción de la
     semi‑ciudad; `σ = frac · min(CBD, L-1-CBD)`), con slider en el panel de
     Uso de suelo. Default `0.5` ⇒ `σ ≈ L/4`, preservando la magnitud original.
  - La función estocástica original se conserva (`generar_oferta_normal`).
- **Veredicto**: Divergencia intencional respecto al original (estocástico → 
  determinista) + exposición de un parámetro antes hardcodeado.
- **Acción**: Mantener. Interpretación: `oferta_sigma_frac` = compacidad urbana
  (menor ⇒ ciudad compacta junto al CBD; mayor ⇒ dispersa). λ_h sigue gobernando
  la **segregación** de estratos (los colores), no la altura.
- **Extensión (2026-06) — formas de ciudad parametrizables**: la oferta dejó de
  ser solo la Normal. Se añadió `supply.py:generar_oferta(forma, …)` con un
  dispatcher de **5 formas** (todas deterministas, CBD excluido, `Σ S = N` por
  mayor residuo): `normal` (campana, idéntica al default anterior), `uniforme`
  (densidad plana), `exponencial` (`S ∝ e^{−d/σ}`, von Thünen), `meseta` (núcleo
  de densidad plana de radio σ con borde neto — super-gaussiana de orden alto;
  ciudad compacta con frontera) `bimodal` (dos picos a ±`sep` — policéntrica) y `valle` (densidad creciente con
  la distancia — triángulo invertido / ciudad desconcentrada).
  `LandUseConfig` expone `forma`, reusa `oferta_sigma_frac` como ancho/pendiente,
  y añade `forma_param` (separación de picos, solo `bimodal`). Objetivo
  pedagógico: estudiar cómo cambia el equilibrio de asignación (y el acoplado con
  transporte) según la geometría. Validado: `normal` reproduce bit a bit el S
  anterior; las 5 convergen. La forma "normal" sigue siendo el default (sin
  cambio de comportamiento por defecto).
  - **Nota 1D**: no se incluye una forma "anular" (dona) separada porque en una
    ciudad **lineal** un anillo a radio `r` colapsa en dos puntos a ±`r`, es
    decir, es idéntico a `bimodal` (medido: correlación 0.996). La distinción
    dona vs policéntrica solo es significativa en 2D.

---

## D-14 · Loop acoplado: residual espurio (unidades) + sin amortiguar (V2)

- **Código (V2, nuevo en esta web)** — `coupled.py:_aggregate_T`: las celdas/estratos
  sin agentes de muestra caían a un fallback `|i - CBD|` que es **distancia en
  índices de celda**, no en minutos (valores hasta ~100 vs tiempos reales ~0–30).
  Como qué celdas quedan vacías varía estocásticamente por iteración, el residual
  `||T_n − T_{n−1}||_∞` quedaba dominado por ese ruido (≈ 188 → 241, creciendo).
  Además el loop exterior aplicaba `T_new` directo (sin amortiguar).
- **Veredicto**: Bug de implementación del módulo V2 (no hay contraparte Overleaf).
- **Acción (aplicada)**:
  1. Fallback **en minutos** (`dist_km / 30 km/h · 60`) en la 1ª iteración y
     **carry‑forward** del estado previo para celdas vacías → el residual refleja
     sólo cambios reales (pasó a ~10–20 min).
  2. **Amortiguación MSA** del loop exterior: `T_state ← θ·T_new + (1−θ)·T_state`
     con `θ = 1/(n+1)`.
  - Persiste un piso de ~10 min por el remuestreo estocástico de población en cada
    iteración exterior (no es divergencia).
- **Frontend asociado**: en modo acoplado se ocultó la FIG 01 (quedaba vacía por
  `final_parcelas=[]`) y la FIG 04 reconstruye la distribución como
  `round(S[i]·Q[h,i])` (campana real) en vez de 1 hogar/parcela.

---

## D-15 · Bici sin piso de velocidad: podía ser más lenta que caminar

- **Código original** — `supply/bike.py:demora_bici_tramo`: el tiempo de bici es
  la suma acumulada de tramos hacia el CBD, con BPR sobre el **flujo acumulado**
  (`cumsum`). No tiene cota superior.
- **Análisis**: como todos los viajes de bici confluyen al centro, los tramos
  centrales acumulan `flujo/capacidad ≫ 1` y con `β=2` el BPR explota; la
  periferia hereda esa suma. Bajo congestión fuerte da tiempos absurdos
  (ej.: 766 min en la periferia vs 124 min caminando y 42 min en flujo libre).
  Viola un límite físico básico: **una bici nunca debería ser más lenta que
  caminar** (el ciclista desmonta y empuja).
- **Veredicto**: Bug físico del modelo (fiel al original, pero inconsistente).
- **Acción (aplicada)**: piso por tramo — `t_bici_tramo ≤ dx / v_caminata · 60`.
  Garantiza `t_bici ≤ t_caminata` en toda celda. No altera el comportamiento con
  demanda baja (donde la bici ya es más rápida); sólo acota los casos
  congestionados. Se pasa `v_caminata` a `demora_bici_tramo` desde `msa.py`.

---

## D-16 · Constantes de congestión de andén distintas al Overleaf

- **Overleaf** — `main.tex` (eq. de $t_e$ y listado de código): la penalización por
  congestión de andén es `t_e = (30/f_op)·α·ρ^β` para `ρ > 1`, y el listado de
  código declara explícitamente **`α = 10, β = 10`**. Con esos valores, apenas
  `ρ > 1` el factor **salta a ~10×** (penalización abrupta y creciente).
- **Código** — `supply/train.py`: `_ALFA_CONGESTION = 0.5`, `_BETA_CONGESTION = 4.0`
  → `factor = 0.5·ρ^4` para `ρ > 1` (con comentario "ver app.py:237-238").
- **Análisis**: los valores difieren y, peor, **cambian el comportamiento
  cualitativo**: con `0.5·ρ^4` el factor *cae* a 0.5 justo sobre `ρ=1` y solo
  supera 1 en `ρ > 2^¼ ≈ 1.19` (ver D‑12), mientras que con `α=10, β=10` el factor
  salta hacia arriba. No se puede saber cuál refleja el `app.py` real sin el
  código original (no disponible).
- **Veredicto**: Discrepancia código ↔ Overleaf (constantes y forma).
- **Acción**: ✅ **Reformulado** como **BPR continua** sin salto ni caída:
  `factor = 1 + α·ρ^β`, `ρ = carga/(frec_max·K)`. Con `β` alto el castigo es
  despreciable bajo saturación (`ρ<1`) y crece suave al pasar `ρ=1`. Los
  parámetros `α, β` se expusieron como config del tren (`anden_alpha`,
  `anden_beta`) con sliders en la UI; default `α=0.5, β=4` (efecto visible sin
  colapsar el metro; con la calibración por defecto los escenarios no saturados
  no se ven afectados). La calibración final queda para validar con los autores.
- **Limitación conocida**: el castigo es **por estación de abordaje**, así que no
  puede forzar el `v/c` del **tramo central** a 1 — ese tramo carga también a los
  pasajeros "de paso" (que abordan en estaciones poco cargadas, con poca espera).
  Verificado: subiendo `α` el `v/c` máximo y el share de metro bajan monótonamente
  (p. ej. en un escenario saturado, `α=0`→ v/c 3.6 / metro 56%; `α=2`→ v/c 2.6 /
  metro 42%), pero no llega a 1. Clavar `v/c=1` requeriría una restricción de
  capacidad en el **arco/vehículo** (crowding) o asignación con capacidad, no solo
  en andén.

---

## D-17 · Signo de `f_h` en la disposición a pagar (Suelo)

- **Overleaf** — `Suelo.tex`, *willingness to pay*: `w_h(u,i) = y_h − (u_h + f_h(i))/λ`.
- **Código** — `land_use/equilibrium.py`: usa `y + f/λ` (`logw = y + f_dl`, y el
  operador `z_hi = H_h·e^{β(y + f_h/λ_h)}`).
- **Análisis**: despejando `p_i` de `u_h = λ_h(y_h − p_i) + f_h(i)` se obtiene
  `p_i = y_h − (u_h − f_h(i))/λ_h = y_h − u_h/λ_h + f_h/λ_h`. La ecuación del
  Overleaf tiene el signo de `f_h` invertido (`− f/λ` en vez de `+ f/λ`). El
  propio operador de punto fijo del Overleaf usa `+ f/λ`, así que es una
  inconsistencia interna; el código es correcto.
- **Veredicto**: Overleaf incorrecto (typo de signo).
- **Acción**: Corregir la ecuación de WTP en `Suelo.tex` a `y_h − (u_h − f_h(i))/λ_h`.

---

## D-18 — Refuerzo del canal Mohring (frecuencia ↔ demanda) y test de Downs‑Thomson

- **Contexto**: se evaluó empíricamente si el simulador reproduce la **paradoja
  de Downs‑Thomson** (agregar capacidad vial empeora el tiempo de sistema porque
  degrada el transporte público). El ingrediente necesario es el **efecto
  Mohring**: la frecuencia del metro es endógena a la demanda
  (`f_op = clip(carga/K, frec_min, frec_max)`), de modo que al perder pasajeros
  baja la frecuencia y sube la espera (`t_espera_base = 30/f_op`).
- **Hallazgo (antes)**: con `frec_min=10, frec_max=20` el rango es angosto y la
  frecuencia queda saturada (cerca de `fmax`) o pegada al piso (`fmin`), fuera
  del tramo sensible de `30/f`. El canal Mohring estaba **inactivo en la
  práctica** y DT no se observaba.
- **Cambio**: se amplió el rango a valores **realistas de metro**:
  `frec_min = 6` (~10 min de intervalo, valle) y `frec_max = 30` (~2 min, punta).
  Con `fmin` más bajo la pendiente `d(espera)/df = −30/f²` es más pronunciada en
  baja frecuencia → la espera responde más a la demanda. Se expone además
  `frec_min` en la UI (antes solo `frec_max`).
- **Verificación**: en régimen congestionado y con el metro dentro del tramo
  sensible (`f_op≈8`), al quitar pistas el metro pierde pasajeros, la frecuencia
  cae (8.4→8.0) y **la espera sube** (3.23→3.38 min) — el canal Mohring queda
  **activo y medible**. Sin embargo el **tiempo de sistema sigue bajando**
  monótonamente al agregar pistas (18.8→16.8 min): **DT no emerge** con
  parámetros realistas porque (a) la sustitución auto↔metro es modesta (~3 pp,
  el logit con ASCs la diluye) y (b) la espera es una **fracción chica** del
  tiempo total de metro (≈3 min de ≈17), dominado por acceso + viaje a bordo,
  ambos independientes de la demanda.
- **Nota conceptual**: DT nace del **efecto Mohring** (frecuencia↑ con la
  demanda ⇒ el TP mejora con más pasajeros), no del *crowding* (ocupación↑ ⇒ TP
  peor), que es de signo opuesto (congestión del TP, estabilizadora). El castigo
  de andén (D‑16) es del lado *crowding*. Reproducir DT pediría acoplar el
  **tiempo a bordo** a la ocupación de forma dominante, lo que sería poco
  realista para un metro; con parámetros realistas el modelo monocéntrico no
  exhibe la paradoja.
- **Veredicto**: Mejora de realismo + diagnóstico. Mohring reforzado (realista);
  DT no observable con parámetros realistas (resultado esperado y defendible).
- **Acción**: documentar en el Overleaf el rango de frecuencia y la ausencia de
  DT como hallazgo del modelo.
- **Refinamiento posterior (cap_tren, 2026-06)**: el experimento de verificación
  (`VERIFICACION_TRANSPORTE.md`, H1) detectó que, pese al rango ampliado, con
  `capacidad_tren=1200` la frecuencia seguía **clavada en `f_min`** en todo
  escenario normal: el umbral de activación `f_min·cap_tren = 6·1200 = 7.200`
  pax/h supera la carga pico típica (~2.000). En consecuencia `frec_max` era un
  parámetro **inerte** (6 vs 30 daban resultados idénticos) y la espera quedaba
  fija en 5 min. **Solución**: recalibrar `capacidad_tren` a **300** (default y
  presets ×¼), a la escala de demanda del modelo. Validado: la frecuencia ahora
  responde (f≈7,6, espera ~4 min), `frec_max` muerde, y el canal Mohring es
  visible (tarifa 0 → +pasajeros → f 6,7→8,2 → espera 4,4→3,7 min). El reparto
  modal apenas cambia (metro ~56%). No es un bug de fórmula sino de calibración
  de escala.

## D-19 — Selección de modos disponibles (set de elección)

- **Contexto**: el usuario puede ahora **habilitar/deshabilitar modos** antes de
  correr el equilibrio (`SimulationConfig.modos_habilitados`), p.ej. para
  escenarios estilizados Auto vs Metro.
- **Implementación**: los modos excluidos se marcan infeasibles (utilidad −∞) en
  `calcular_utilidades`; `elegir_modo` devuelve `None` si un agente queda sin
  modo feasible (viaje "varado", no se asigna). No afecta el teletrabajo (se
  decide antes de la elección de modo). El original no contempla esta opción.
- **Veredicto**: Ampliación de funcionalidad (no existe en el Overleaf).
- **Acción**: documentar como funcionalidad nueva de la web.

---

## D-20 — Rendimiento: asignación agrupada (independiente de la densidad)

- **Síntoma**: con `n_celdas` y `densidad_por_celda` altos el MSA corría
  extremadamente lento (p.ej. 40k agentes ≈ 19 s en Pyodide).
- **Causa**: `_correr_iteracion` recorría **cada agente** llamando
  `calcular_utilidades` + `elegir_modo` (con `rng.choice` por agente), y esto se
  repetía en **cada** iteración del MSA → costo O(max_iter · agentes). Además
  `generar_poblacion` hacía 3 llamadas a `rng` por agente.
- **Fix**:
  1. **Agrupación**: la utilidad sólo depende de `(estrato, celda, tiene_auto)`,
     así que hay ~6·`n_celdas` grupos distintos **independiente de la densidad**.
     Se calcula la probabilidad **una vez por grupo** y se agregan los flujos:
     en `expected`, `dem += nₐ·prob`; en `montecarlo`, una `rng.multinomial(nₐ,
     prob)` por grupo. Costo del loop: O(max_iter · grupos).
  2. **Registros por agente una sola vez**: `_asignar_modos_agentes` muestrea el
     modo de cada agente (vectorizado, `rng.choice(size=nₐ)`) sólo al final, a
     partir del estado convergido (antes se reescribían en cada iteración).
  3. **`generar_poblacion` vectorizada**: 3 sorteos `rng` totales en vez de 3 por
     agente.
  4. **Una sola corrida en streaming**: antes el worker corría la simulación
     **dos veces** (una para los snapshots en vivo, otra en `simulate_from_json`
     para obtener `agentes`/emisiones). Ahora `iter_msa(sim, trace)` popula el
     `ConvergenceTrace` completo durante el mismo recorrido y el worker lo lee con
     `last_trace_to_py()` sin reejecutar. `run_msa` = consumir `iter_msa` con un
     `trace`; el loop acoplado usa `run_msa_con_poblacion` (mismo `_iter_loop`
     sobre una población dada). Se eliminó el duplicado `_run_final_assignments`.
- **Resultado** (Pyodide): 40k agentes 19 s → **0.45 s**; default (10k) 8.5 s →
  **0.26 s**. La densidad ya no afecta el costo del loop; sólo escala con
  `n_celdas`. El modo `expected` es **numéricamente idéntico** al previo
  (determinista); `montecarlo` es estadísticamente equivalente (cambia la
  secuencia de sorteos).
- **Veredicto**: Mejora de rendimiento (sin cambio de modelo en `expected`).

---

## D-21 — Saturación de la ciclovía: techo de caminata plano (capacidad blanda)

- **Contexto**: en la verificación (`VERIFICACION_TRANSPORTE.md`) se evaluó si el
  modelo de bici refleja correctamente la **saturación** de la ciclovía.
- **Cómo está**: `t_tramo = min( t0·(1+α·(q/cap)^β),  t_caminata_tramo )`. El
  techo (D-15) acota el tiempo al de caminar el tramo. Es una capacidad
  **blanda**, coherente con auto y metro (ningún modo tiene tope duro ni rechaza
  demanda; todos usan funciones volumen-demora tipo BPR).
- **Limitación**: el techo es **plano** → pasada la saturación (`v/c > 1`) el
  costo de congestión de la bici **deja de crecer** (se queda en ~caminata).
  Asimetría con el auto, cuyo BPR no tiene tope (a `v/c=2,5` el auto llega a
  ~51 min; la bici se topa en caminata). En equilibrio, una ciclovía
  sub-dimensionada **no expulsa usuarios**: el flujo se apila a varios× la
  capacidad sin que suba el costo, y la **capacidad de ciclovía resulta una
  palanca de política débil**.
- **Decisión (2026-06)**: **se mantiene como está**. Es una simplificación
  defendible y consistente con el resto del modelo (capacidad blanda en todos los
  modos), y el techo D-15 está físicamente fundado (el ciclista desmonta y
  camina). Se documenta la limitación.
- **Mejora futura** (si se quiere que la capacidad de ciclovía sea una
  restricción observable): **degradar el techo bajo `v/c > 1`** — caminar
  empujando la bici en una ciclovía atestada es más lento que caminar libre —
  manteniendo D-15 intacto a `v/c ≤ 1`. Es más realista pero numéricamente más
  rígido (converge más lento), así que iría acompañado de subir `max_iter`. Se
  prototipó (`techo·(1+γ·max(0, v/c−1)^δ)`) y funciona; se descartó por ahora por
  simplicidad.
- **Sobre la convergencia (aclaración)**: las no-convergencias observadas con
  bici saturada **no son culpa del modelo de bici**, sino la cola lenta `~1/it`
  del MSA cortada por un `max_iter` bajo. El techo plano es, de hecho, el que
  **mejor converge** (es el menos rígido). Con `tolerance=0,1` (default del
  frontend) los escenarios rígidos convergen con `max_iter ≈ 20–25` (default
  actual: 12). Subir el default de `max_iter` queda como fix pendiente opcional.
- **Veredicto**: Simplificación aceptada con limitación documentada; mejora
  opcional identificada.

---

## Tabla resumen

| ID | Tema | Veredicto | Prioridad |
|----|---|---|---|
| D-01 | Factor pendiente bici | Overleaf incorrecto | Alta |
| D-02 | Penalizaciones bici/caminata | Overleaf incorrecto | Alta |
| D-03 | β caminata | Overleaf incorrecto | Alta |
| D-04 | `t_espera` base | Equivalentes | Baja |
| D-05 | Caminata habilitada | Overleaf desactualizado | Media |
| D-06 | Emisiones no documentadas | Doc incompleta | Media |
| D-07 | Jornadas inactivas | Dead-path intencional | Baja |
| D-08 | Método Frechét | Ampliación | Baja |
| D-09 | Parámetros hardcodeados | UI | Media (fix en web v1) |
| D-10 | Sin criterio de convergencia | Mejora | Media (fix en core) |
| D-11 | `generar_poblacion` muerta | Limpieza | Baja |
| D-12 | Congestión de andén metro inactiva (+ artefacto) | Fiel al original (artefacto) | Baja |
| D-13 | Oferta de suelo determinista + σ expuesta | Divergencia intencional | Media |
| D-14 | Loop acoplado: residual espurio (unidades) + MSA | Bug V2 corregido | Alta |
| D-15 | Bici sin piso de velocidad (podía ser > caminata) | Bug físico corregido | Alta |
| D-16 | Constantes congestión andén (α,β) ≠ Overleaf | Discrepancia código↔Overleaf | Media |
| D-17 | Signo de f_h en WTP (Suelo) | Overleaf incorrecto (typo) | Media |
| D-18 | Rango de frecuencia realista (Mohring) + test Downs‑Thomson | Mejora + diagnóstico (DT no observable) | Media |
| D-19 | Selección de modos disponibles (set de elección) | Ampliación de funcionalidad | Media |
| D-20 | Rendimiento: asignación agrupada (independiente de densidad) | Mejora de rendimiento | Alta |
| D-21 | Saturación ciclovía: techo de caminata plano (capacidad blanda) | Simplificación aceptada (limitación documentada) | Media |
