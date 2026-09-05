# Registro de Discrepancias — Código ↔ Overleaf

Este documento registra las divergencias entre el código fuente (`titirilquen-repo/`) y la documentación matemática en el Overleaf (`Titirilquen_overleaf/`). La política del proyecto es **tratar el código como fuente de verdad** y corregir la documentación matemática; este archivo preserva la trazabilidad de las decisiones.

> **Nota (auditoría 2026-06):** el Overleaf original (`main.tex`, `Suelo.tex`) se
> copió a `reference/overleaf_original/` (no versionado; la versión con los
> cambios de este proyecto está en `reference/overleaf_modificado/`) y se auditó contra el core de esta
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

## D-08 · `λ_h` no está identificado en el logit de uso de suelo

- **Overleaf** — `Suelo.tex:170-174`: reconoce que el logit es "erróneo" ante `λ_h` heterogéneo y propone un método alternativo.
- **Código** — `Ciudad2.py:361`: implementaba `resolver_equilibrio_frechet` (marcado "MALA" en el docstring). No se portó a v2.
- **Estado (2026-08-24): CERRADO.** Implementada la subasta heteroscedástica
  (HEV) de Train §4.5 / Bhat (1995) en `land_use/hev.py`. `solve_subasta`
  despacha según los datos: λ uniformes → forma cerrada (exacta ahí); λ
  distintos → HEV. Con eso λ queda **identificado** — mover λ deja de ser
  idéntico a re-escalar (α, ρ), que es lo que este hallazgo denunciaba.
  Fijado en `tests/test_hev.py`.
- **Actualizado 2026-09-04.** El default ya es heterogéneo: `λ = (0,5 · 1 ·
  1,9375)`, importado de la anatomía de transporte (D-33). Todo lo que sigue
  abajo en esta entrada —«El problema», «Cómo se manifiesta», el **Veredicto**
  «pendiente para los autores» y la nota de UI— describe el régimen de la
  **forma cerrada** y se conserva como historia: bajo HEV la identidad
  `y + f/λ ≡ y + f(α/λ, ρ/λ)` sigue siendo cierta para el determinístico, pero
  `λ` mueve además la escala del ruido y por eso está identificado. La
  advertencia de que `λ` entra por dos canales a la vez sí sobrevive.
- **Advertencia que sobrevive:** λ sigue entrando también por la parte
  determinística `f_h/λ_h`, así que mueve preferencias y dispersión a la vez.
  Para que actúe puramente por sensibilidad al precio hace falta un modelo de
  **elección**, no de subasta: en una subasta todos los postores de una parcela
  pagan lo mismo y el precio se cancela.
- **Ojo con lo que decía Suelo.tex.** Su bloque S-5 llamaba «logit
  heteroscedástico» a reponderar las pujas por `β_h = β·λ_h` conservando forma
  cerrada. Eso no es HEV —Train: «the integral does not take a closed form»— y
  además deja λ inerte (`max|ΔQ| = 2e-8` entre λ=0,01 y λ=100). El `.tex` local
  se corrigió; `reference/` no se versiona, así que hay que llevarlo a Overleaf.

**El problema.** La utilidad es `U_hi = λ_h(y_h − p_i) + f_h(i) + ε_hi` con `ε`
Gumbel de escala `1/β` (homoscedástica **en utilidad**). La puja (WTP) divide por
`λ_h`, y el solver aplica un `β` **uniforme** sobre las pujas. Consecuencia
exacta, dado que `f = −α·T − ρ·dens` es lineal en `α` y `ρ`:

    y_h + f_h(i)/λ_h  ≡  y_h + f(i;  α_h/λ_h,  ρ_h/λ_h)

**Mover `λ_h` es idénticamente re-escalar `(α_h, ρ_h)` por `1/λ_h`** —verificado
con `max|ΔQ| = 0,000e+00`, fijado en `test_land_use.py`— y a la vez escalar el
ruido de ese estrato a `1/(β·λ_h)`. Las tres cosas se mueven juntas y no se
pueden separar: `λ` **no es un parámetro económico independiente**, es una
re-parametrización redundante de `α` y `ρ`.

**Cómo se manifiesta** (medido en `scripts/auditoria_suelo.py`, ver AU-06):
- Salto casi discontinuo: entre `λ = 0,8` y `λ = 0,95` el estrato alto cruza la
  ciudad entera (8,26 → 1,33 km del CBD). Fuera de esa banda, `λ` casi no hace
  nada.
- Dirección absurda: bajar `λ` manda a los ricos a la periferia, porque
  `ρ_eff = ρ/λ` castiga justamente las celdas centrales, que son las densas.

**El ingreso `y_h` es inerte**, en cambio: entra como constante por estrato,
independiente de `i`, y se absorbe en `ū_h` → `Q` idéntico al variar `y`
(verificado ≈1e‑14). Ese contraste es lo que separa el artefacto de un
efecto-ingreso real: si `λ` reasignara gente por una razón económica, `y`
también debería.

**Intento de corrección fallido (eliminado 2026-08).** Existió un segundo solver
presentado como la corrección consistente y declarado default.
**No corregía nada**: metía `λ` solo como `λ_h·y_h`, una constante por estrato
que el punto fijo absorbe, dejando `λ` **completamente inerte** (`Q` idéntica con
`λ` de 0.01 a 100). Nunca aplicó la escala por estrato que su documentación
afirmaba — el operador de punto fijo toma un `β` **escalar**, así que esa escala
no estaba implementada en ninguna parte. Sus tests pasaban vacuamente por lo
mismo. Se eliminó junto con el campo `solver` del schema; los escenarios
guardados que lo traen se migran en `serialization.ts`.

- **Veredicto**: limitación **declarada** del modelo, no un bug. Una corrección
  real exige que el ruido escale por estrato, lo que implica cambiar el operador
  de punto fijo, no solo el `score`. **Pendiente para los autores.**
- **UI**: el slider de `y` queda **deshabilitado siempre** (`land_use.y_na`,
  regla: se deshabilita lo que no mueve la asignación). El de `λ` queda activo
  pero con un **aviso de artefacto** (`land_use.lambda_artifact_logit`).
- **Acción**: no presentar el efecto de `λ` como resultado en material docente.
  Ver `AUDITORIA_USO_SUELO.md` AU-06/AU-07 y el tutorial §6.

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
  (`archivo/VERIFICACION_TRANSPORTE.md`, H1) detectó que, pese al rango ampliado, con
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

- **Contexto**: en la verificación (`archivo/VERIFICACION_TRANSPORTE.md`) se evaluó si el
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
  frontend) los escenarios rígidos convergen con `max_iter ≈ 20–25`.
  **Fix aplicado (jun-2026)**: el default de `max_iter` subió de 12 a 20 (core y
  frontend); el corte real sigue siendo por `tolerance`, así que los escenarios
  fáciles no se encarecen.
- **Veredicto**: Simplificación aceptada con limitación documentada; mejora
  opcional identificada.

---

## D-22 — Loop acoplado: accesibilidad común por ubicación (no por estrato)

- **Síntoma**: al correr "Ciudad en equilibrio", la asignación de estratos en el
  suelo se veía **invertida/revuelta** (ricos a la periferia, pobres al centro) y
  el loop convergía instantáneamente.
- **Causa**: `_aggregate_T_expected` devolvía la accesibilidad `T[h,i]` **por
  estrato**. Como los estratos con más `prob_auto` (auto = modo rápido)
  experimentan menor tiempo, el bid-rent lo leía como "a los ricos no les molesta
  la distancia" e **invertía** el ordenamiento Alonso/Martínez. Verificado: per
  estrato daba alto 7.6 km / bajo 2.2 km (invertido); común da 3.1 / 4.7 / 6.2 km
  (correcto).
- **Fix**: la accesibilidad es un **atributo de la ubicación** → se devuelve una
  **media entre estratos** común, replicada en todas las filas. La
  heterogeneidad entre usuarios ya la captura `α_h`. El tiempo experimentado por
  estrato (con el efecto auto) se sigue reportando en `coupled_metrics.py` a
  partir de los agentes.
- **Refinamiento (jun-2026)**: la media pasó de simple a **ponderada por
  población** (`T(i) = Σ_h (H_h/ΣH)·Te_h(i)`): con shares 10/40/50 el estrato
  bajo pesa lo que su población, no 1/3 — T(i) es el tiempo esperado del viajero
  *representativo* de la ubicación. Sigue siendo común por ubicación (no
  reintroduce el problema de la inversión).
- **Veredicto**: Bug del modelo acoplado corregido (decisión del autor del
  modelo, jun-2026). NO reintroducir T por estrato en el bid-rent.
- **Revisada 2026-09-04 (D-34).** La prohibición valía para `T` en minutos.
  Con la accesibilidad = logsum en pesos, `T` por estrato NO invierte Alonso
  (medido) y es el objeto teórico correcto; `_aggregate_T_expected` fue
  reemplazada por `_T_logsum_snapshot`, por estrato, sin promedio.

---

## D-23 — Loop acoplado: baseline "sin feedback" en minutos a flujo libre

- **Síntoma**: la comparación "sin feedback" (iter 0) vs "con feedback" (iter N)
  mostraba un efecto enorme y engañoso (Theil colapsaba ~0.46 → ~0.05).
- **Causa**: el arranque (`LandUseCity.build`, antes con `T=None`) resolvía el
  suelo con `_default_T` = **distancia en índices de celda** (escala 0–100),
  mientras las iteraciones acopladas usan **minutos** (0–33). El salto iter0→
  final era mayormente un **reescalado de unidades**, no el efecto real del
  feedback de congestión.
- **Fix**: el baseline se inicializa con `_freeflow_T` = accesibilidad ingenua a
  **flujo libre en minutos** (`T(i) = d_km/v_auto·60`, común), en la **misma
  escala** que el loop. Con el baseline honesto el feedback transporte→suelo
  sobre la **localización es genuinamente modesto** (Theil ~0.08); lo que
  responde fuerte es el lado transporte (congestión, frecuencia de metro) y la
  diferencia **entre escenarios**.
- **Veredicto**: Artefacto de unidades corregido; el feedback honesto es modesto
  (no era un bug que estuviera "apagado", era el artefacto el que lo inflaba).
- **Actualizado 2026-09-04 (D-34).** El baseline y las iteraciones usan ahora
  el mismo objeto —logsum mensual a flujo libre vs. sobre el snapshot—, así
  que la comparación sin/con feedback sigue siendo en la misma escala.

---

## D-24 — Loop acoplado: gridlock del corredor monocéntrico → población por escenario

- **Síntoma**: con demanda alta, escenarios grandes y auto-dependientes (p. ej.
  `sparse-proauto`, corredor de 30 km) el loop externo **diverge** (residual
  oscila/crece, t_medio explota a cientos de min).
- **Causa**: estructura monocéntrica (todo el flujo al CBD) + BPR → la congestión
  cerca del CBD crece sin techo cuando la demanda supera la capacidad vial. Es
  **físico**, no numérico: probado damping (θ constante) y no estabiliza un
  estado genuinamente gridlockeado. La escala de demanda del loop es ΣH (del
  suelo); `densidad_por_celda` **no** afecta el acoplado.
- **Fix (UI/configuración)**: la población (ΣH) se expone como **palanca de
  demanda** en la página, y cada preset tiene un `poblacionDefault` acorde a su
  capacidad antes de gridlockear (compacta 12 km ~40k, base 20 km ~30k, sparse
  30 km ~12k; custom 25k). Régimen sano donde se activan los feedbacks del
  transporte (frecuencia de metro responde, congestión real) sin diverger.
- **Pendiente**: estabilizar el loop externo (damping adaptativo / relajación)
  para admitir demanda alta en ciudades grandes sin acotar por población.
- **Robustez (jun-2026)**: en gridlock extremo (p.ej. Dispersa·Pro-Auto a 120k),
  T llega a miles de minutos y las diferencias de score α_h·T superan el rango
  de `exp()` → `Q` underfloweaba a 0/1 exactos y `asignar_hogares_simple`
  crasheaba ("Asignación estancada") cuando la única masa de una parcela estaba
  en un estrato con cuota agotada. Fix: la asignación se completa por
  **desborde de cuotas** (los hogares restantes llenan los espacios restantes),
  con test de regresión; y el slider de población muestra una advertencia al
  superar la población recomendada del escenario.
- **Veredicto**: Acotado por configuración; mejora de robustez del loop externo
  identificada como pendiente.

---

## D-25 — Uso de suelo: Q sin la ponderación H_h de la subasta (no conservaba hogares por estrato)

- **Síntoma**: con `H_por_estrato` heterogéneo (default web `[1000, 4000, 5000]`)
  la asignación espacial se veía "rara": el estrato alto sobrerrepresentado
  (Σ_i S_i·Q[1,i] ≈ 2287 con solo 1000 hogares) y la asignación final
  (`asignar_hogares_simple`) lo corregía agotando cuotas en orden de barrido,
  distorsionando el patrón espacial.
- **Causa**: `_solve_fixed_point` (y los solvers del commit inicial, portados
  verbatim de `Ciudad2.py`) calculaban la matriz final como
  `Q[h,i] ∝ e^{β(s_hi − ū_h)}` — **sin el factor `H_h`**. La ec. (3) del
  `Suelo.tex` es `Q_hi = H_h·e^{βw}/Σ_g H_g·e^{βw}`: la parcela la disputan
  `H_g` postores de cada tipo, y el máximo de `H_g` Gumbel i.i.d. corre la
  ubicación en `ln(H_g)/β`. El propio punto fijo y el precio (`e^{βp_i} =
  Σ_g H_g·e^{β(s_gi − ū_g)}`) sí incluían `H` — solo el `Q` devuelto lo omitía.
  Con `H` igual entre estratos (el default histórico, 33300×3) el factor se
  cancela, por eso pasó inadvertido.
- **Fix (jun-2026)**: `log_q = log(H) + β(score − ū − p_i)`, normalizado por
  columna. Verificado: `Σ_i S_i·Q[h,i] = H_h` exacto en ambos solvers
  (test de regresión `test_q_conserva_hogares_por_estrato_con_H_desigual`).
  El punto fijo, `ū` y `p` no cambian (ya eran correctos).
- **Veredicto**: Bug del port corregido (afectaba ambos solvers); ahora fiel a
  Suelo.tex ec. 3.

---

## D-26 — Uso de suelo: unidades físicas (T en minutos, densidad en hogares/km) → invariancia de grilla

- **Síntoma**: el equilibrio de suelo dependía de la **resolución de la grilla**:
  con la misma ciudad física (20 km, misma población y parámetros), el índice de
  Theil pasaba de 0.245 (L=101) a 0.462 (L=201) y 0.658 (L=401). Subir el
  slider "número de celdas" — una decisión puramente numérica — cambiaba las
  conclusiones del modelo.
- **Causa**: dos términos de la atractividad `f_h(i) = −α_h·T(i) − ρ_h·S_i`
  estaban en **unidades de grilla**, no físicas: `T = |i − CBD|` en *índices de
  celda* (su rango crece con L) y `S_i` en *hogares por celda* (se diluye con
  L). Refinar la grilla era matemáticamente **idéntico** a estirar la ciudad:
  los Theil del artefacto (0.245/0.462/0.658 para L=101/201/401) coinciden
  exactamente con los de agrandar la ciudad física (10/20/40 km a L fija).
- **Fix (jun-2026)**:
  - `T` en **minutos** a flujo libre (`d_km/v_ref·60`, `v_ref = 30 km/h`), la
    misma convención que el baseline del loop acoplado (D-23) — standalone y
    acoplado quedan en la misma escala, y α gana unidades interpretables
    (utiles/min, las mismas del `b_tiempo_viaje` de demanda).
  - La penalización de densidad usa **hogares/km** (`ρ·S_i/Δx`), separando los
    dos roles de `S`: capacidad por parcela (clearing del punto fijo, sigue en
    hogares/celda) y desamenidad por densidad (física, en hogares/km).
  - Defaults recalibrados para reproducir el comportamiento previo en la grilla
    de referencia (201 celdas / 20 km): `α = (6.5, 6.0, 5.5)` utiles/min
    (≈ α_viejo·5), `ρ = 0.1` utiles/(hogar/km) (= ρ_viejo·Δx).
- **Por qué es lo correcto**: la discretización es una elección numérica y los
  indicadores deben **converger** al refinarla (el límite continuo es el modelo
  monocéntrico de Alonso/Fujita); que un resultado dependa de la unidad espacial
  de agregación es el clásico *Modifiable Areal Unit Problem* (Openshaw 1983),
  documentado para índices de segregación por Reardon & O'Sullivan (2004). El
  tamaño **físico** de la ciudad, en cambio, sí debe mover los indicadores —
  más km ⇒ el gradiente α·T pesa más contra el ruido del logit ⇒ más sorting.
- **Verificación** (`test_land_use.py`):
  `test_invariancia_a_la_resolucion_de_la_grilla` — Theil estable (±2%) y
  distancias medias estables (±0.35 km) entre L=101/201/401;
  `test_sensibilidad_al_tamano_fisico` — Theil(40 km) > Theil(10 km).
- **Referencias**: Alonso (1964) *Location and Land Use*; Fujita (1989) *Urban
  Economic Theory*; Martínez (2018) *Microeconomic Modeling in Urban Science*
  caps. 3–5; Openshaw (1983) *The Modifiable Areal Unit Problem* (CATMOG 38);
  Reardon & O'Sullivan (2004) "Measures of Spatial Segregation", *Sociological
  Methodology* 34; Hansen (1959) "How Accessibility Shapes Land Use", *JAPA* 25.
- **Migración**: escenarios `.ttrq` con α/ρ/y en unidades viejas (solo los
  exportados desde esta rama antes del cambio) requieren reescalar a mano
  (α×5, ρ×0.1); los v1 no traían suelo, así que no les afecta.
- **Veredicto**: Bug de unidades corregido (decisión de modelo, jun-2026);
  documentar en el Overleaf (ver OVERLEAF_CHANGES §C9).

---

## D-27 — Métrica de carga: costo mensual / ingreso mensual (unidades monetarias reales)

- **Síntoma**: la "carga costo/ingreso" del reporte del acoplado mostraba
  valores absurdos (3.494% / 6.165% / **27.443%** con los defaults): dividía el
  costo **por viaje en $** (~3.000) por un ingreso **adimensional** (120/50/10).
- **Fix (jun-2026)**: el ingreso `y` del suelo se declara en **$/mes**
  (defaults 3.5M / 1.5M / 0.5M, ~deciles chilenos estilizados) y la carga pasa a
  ser **mensual**: `(costo_por_viaje · 44 viajes/mes) / y` (2 viajes × 22 días).
  Con los defaults da ~4% / 9% / 26% — y el ~26% del estrato bajo es el hallazgo
  pedagógico correcto (umbral típico de (in)asequibilidad de transporte).
- **Nota de modelo**: `y` sigue **sin mover la asignación** (entra como constante
  por estrato y se absorbe en ū — ver D-08); solo alimenta la
  métrica de equidad. El ratio bajo/alto era válido incluso antes (adimensional);
  lo que no tenía sentido era el *nivel*.
- **Referencia**: el costo de transporte como fracción del ingreso es la métrica
  estándar de asequibilidad (p.ej. el *H+T Affordability Index* del CNT usa 15%
  del ingreso como umbral de transporte asequible).
- **Veredicto**: Unidades corregidas; métrica interpretable.

---

## D-28 — Transporte: densidad física (hab/km) → `n_celdas` puramente numérico

- **Síntoma**: en el módulo de transporte (V1/Sandbox), subir el slider
  "número de celdas" con largo y densidad fijos **multiplicaba la población**:
  `generar_poblacion` creaba `densidad_por_celda × (n_celdas − 1)` agentes, así
  que 201 → 401 celdas duplicaba la demanda (y la congestión) de la misma
  ciudad de 20 km. El mismo artefacto de unidades que D-26, entrando por la
  generación de población; peor aún, el slider significaba dos cosas opuestas
  según la página (resolución pura en suelo/acoplado tras D-26, palanca de
  población encubierta en transporte).
- **Discusión de modelo**: la parametrización antigua es coherente con la
  lectura literal "celda = parcela llena" (más parcelas ⇒ más vivienda), pero
  esa lectura hace que una decisión numérica tenga efectos urbanos. La densidad
  de la ciudad debe ser una **palanca explícita del usuario**, no un efecto
  colateral de la grilla. La lectura física de la celda se conserva vía la
  **cuadra de referencia de 100 m** (la celda de la grilla 201/20 km): 500
  hab/km ≡ 50 hogares por cuadra, que es exactamente el default anterior.
- **Fix (jun-2026)**: `CityConfig.densidad_por_celda` (hab/celda) →
  `densidad_hab_km` (hab/km). Población total = densidad × largo, repartida por
  celda con el método del mayor residuo sobre el objetivo uniforme `dens·Δx`
  (determinista). Presets convertidos preservando su población (Compacta 4200,
  Base 1800, Dispersa 650 hab/km; default 500). El frontend **migra** escenarios
  viejos al importar (`.ttrq`/`?s=`): `densidad_hab_km = dpc·(N−1)/largo`.
- **Semántica resultante** (los tres diales quedan ortogonales):
  `n_celdas` = resolución (no cambia nada económico, en ningún módulo) ·
  `densidad_hab_km` = qué tan densa es la ciudad · `largo_ciudad_km` = qué tan
  grande (más gente a densidad constante + más distancia).
- **Verificación**: `test_poblacion_invariante_a_la_grilla` — población total
  estable (±6 sobre 250) entre 51, 101 y 401 celdas con la misma ciudad física.
- **Veredicto**: Continuación de D-26 (unidades físicas en todos los módulos);
  decisión de modelo jun-2026.

---

## D-29 — Emisiones de metro por tren-km (no por pax·km)

- **Cómo estaba**: `FE_metro = 0.040 kg/pax·km` — la emisión del metro crecía
  linealmente con los pasajeros, como si cada pasajero nuevo "emitiera".
- **Problema conceptual**: el costo ambiental del metro es por **tren
  circulando**, no por pasajero: un tren emite (energía de tracción) casi lo
  mismo vacío que lleno. Con la formulación por pax·km, atraer pasajeros al
  metro aumentaba sus emisiones uno a uno y el modelo ocultaba las **economías
  de escala** del transporte público — exactamente el efecto pedagógico
  interesante (el "Mohring de emisiones": más demanda ⇒ más frecuencia ⇒ más
  servicio, pero emisiones POR PASAJERO a la baja; y el servicio mínimo emite
  igual aunque viaje vacío).
- **Fix (jun-2026)**: `emisiones_metro = factor · tren-km/h`, con
  `tren-km/h = f_op · largo_línea · 2` (ida y vuelta: el retorno es costo real
  de proveer la frecuencia). El perfil espacial se reparte uniforme sobre la
  línea. Con la frecuencia endógena, las emisiones del metro ahora solo
  responden al **nivel de servicio**.
- **Calibración**: `factor_emision_metro_tren_km = 2.5 kg/tren·km` — continuidad
  con la calibración anterior en el escenario de referencia (medido 2.45) y
  plausible físicamente (~8 kWh/km × ~0.3 kgCO₂/kWh de la red).
- **Migración**: el campo `factor_emision_metro` (kg/pax·km) se elimina; el
  frontend lo descarta al importar escenarios viejos y adopta el default nuevo
  (no hay conversión automática: requeriría el factor de carga).
- **Verificación** (`test_emissions.py`): emisión exacta `factor·f·span·2`;
  invariante a la carga de pasajeros a frecuencia fija; doble frecuencia ⇒
  doble emisión; perfil espacial suma el total.
- **Veredicto**: Corrección conceptual del módulo de emisiones (D-06 sigue
  pendiente de documentarse en el Overleaf; ver OVERLEAF_CHANGES C5).

---

## D-30 — Tres baselines de "sin congestión": convenciones y por qué difieren

No es un bug sino una aclaración (auditoría jun-2026): el modelo usa **tres
nociones distintas de "red sin congestión"**, cada una apropiada a su contexto.
Se documentan aquí para que no se confundan:

| Uso | Baseline | Definición | Por qué |
|---|---|---|---|
| **Iteración 0 del MSA** | Flujo libre *naive* | auto/bici a velocidad libre; metro con `t_acceso=10`, `t_espera=5` fijos | Es el arranque histórico del original (fiel al Overleaf, ver D-04 nota); solo necesita ser un punto de partida razonable — el MSA lo corrige en 1–2 iteraciones. |
| **ΔCS (excedente del consumidor)** | **Red vacía** | la misma infraestructura con demanda 0: BPR(0), tren a `f_min` con las estaciones reales | El Δ debe aislar el efecto de la DEMANDA sobre la red (congestión vs Mohring); usar tiempos fijos inventados sesgaría el signo (con pocas estaciones, el acceso real a flujo libre es peor que el "10 min" naive). |
| **Arranque del loop acoplado** | Flujo libre **en minutos** a `v_auto` | `T(i) = d_km/v_auto·60` | El suelo de la iteración 0 no conoce la red (aún no corre el MSA); solo necesita una accesibilidad monótona en la MISMA unidad (minutos) que las iteraciones siguientes (D-23). |

- **Nota relacionada (caminata sin congestión)**: `d_caminata` se calcula y
  reporta pero no existe función de oferta peatonal — la caminata nunca se
  congestiona. Simplificación deliberada: su rol en el modelo es ser el "piso"
  del set de elección (y el techo físico de la bici, D-15), no un modo con
  capacidad.
- **Veredicto**: Convenciones documentadas; no requiere cambio de código.

---

## D-31 — Uso de suelo: `beta` significaba cosas distintas a cada lado del despacho

**Qué pasaba.** `solve_subasta` elige el modelo según los datos: forma cerrada si
los `λ_h` son uniformes, HEV si difieren. Las dos ramas recibían `beta`, pero lo
interpretaban en espacios distintos:

- la rama cerrada lo aplicaba directo a la puja, que está **en dinero** → `b = β`;
- la rama HEV construía `θ_h = 1/(β·λ_h)`, o sea `b_h = β·λ_h`, tratándolo como
  precisión **en útiles**.

**Por qué importa.** Por la ec. (4.3) de Martínez (p. 77), la disposición a pagar
es `q_hi = y_h + (f_h − u_h)/λ_h + ε_hi/λ_h`, con `ε_hi/λ_h ~ Gumbel(0, b_h)` y
`b_h = λ_h·μ_h`. La precisión en dinero **lleva λ**. La rama cerrada la omitía, y
con eso el despacho quedaba **discontinuo**: volver los λ infinitesimalmente
heterogéneos —perturbación de 10⁻⁹, que sólo cambia de rama— movía la asignación
de golpe. Medido: `max|ΔQ|` = 4,7·10⁻² con λ = 2 y 8,9·10⁻² con λ = 0,5.

**Por qué no se había visto.** Con `λ_h = 1` —el default de los tres estratos, y
ningún preset lo cambia— `β·λ = β` y las dos lecturas coinciden bit a bit. El
test que decía verificar la reducción comparaba `solve_subasta` contra
`solve_logit`, y **con λ uniforme las dos iban a la forma cerrada**: era un test
de despacho, no de reducción.

**Qué se hizo.** `solve_subasta` convierte igual en las dos ramas (`b_h = β·λ_h`),
y `_solve_fixed_point` pasó a nombrar su parámetro `b` documentando que es la
precisión en dinero. `solve_logit` **conserva** su semántica —aplica `beta` tal
cual a la puja en dinero— porque es la referencia homoscedástica con la que se
demuestra D-08, y meterle λ rompería justamente la identidad que D-08 exhibe;
queda anotado en su docstring que para compararla con `solve_subasta` hay que
pasarle `β·λ`.

**Efecto en la línea base: ninguno.** Con λ = 1 la rama cerrada recibe
exactamente lo de antes; `test_linea_base` no se movió y el contrato generado
quedó byte-idéntico. Lo único que cambió de resultado son las corridas con λ
uniforme ≠ 1, que antes usaban una escala equivocada.

**Fijado por** `test_el_despacho_no_salta_al_romper_la_uniformidad_de_lambda`
(el salto ahora es ~10⁻¹⁰, la tolerancia del solver) y por
`test_hev_reduce_al_logit_cuando_lambda_es_uniforme`, corregido para hacer la
conversión al comparar.

**Encontrada** el 2026-09-01, tirando del hilo de una pregunta de análisis
dimensional: si `y_h` entra en dinero, ¿en qué unidades está cada término de la
puja?

**No era una distracción nuestra: Martínez la nombra.** En el capítulo de
estimación (p. 242) plantea exactamente esta ambigüedad sobre el exponente del
modelo de elección:

> «If they are interpreted as a utility function, then `e_h = β·λ_h`, with `λ_h`
> the marginal utility of income, whereas if they are interpreted as a consumers'
> surplus, then `e_h = β` because willingness-to-pay functions have no parameter
> for prices or rents. **The ambiguity prevails unless β or λ_h is estimated
> independently** of Eq. (9.9).»

O sea que las dos lecturas que el despacho mezclaba son las dos lecturas
legítimas del modelo, y sólo una estimación independiente de `β` o de `λ_h` las
separa. La corrección de acá elige la de utilidad (`b_h = β·λ_h`), que es la
consistente con la ec. (4.3) y con el HEV. Ver también AU-13: mientras `β` no se
ancle, su nivel queda libre.

## D-32 — Uso de suelo: la densidad de `f` es exógena, no una externalidad de localización

**Qué hace el código.** La atractividad de la parcela es
`f_h(i) = −α_h·T_h(i) − ρ_h·dens(i)`, con `dens = S/Δx` y `S` la **oferta**,
generada una sola vez por `generar_oferta(forma, σ)`. El `score` se arma una vez
antes del punto fijo (`equilibrium.py:246` y `:362`), así que `ρ·dens` queda
congelado durante toda la iteración: el punto fijo mueve `ū` y `p`, nunca `f`.

Hay un segundo motivo, más fuerte que el primero: el mercado se vacía —las
columnas de `Q` suman 1 y `Σ S = Σ H` es obligatorio—, de modo que la densidad
**realizada** es idénticamente `S/Δx`. El equilibrio decide *quién* vive en cada
celda; *cuántos* lo fija la oferta y no cambia con ninguna configuración.

**Qué dice Martínez.** En su modelo la atractividad es **endógena**: las
externalidades de localización son un mecanismo central, no un detalle.

> «The decision of agents to locate themselves in a site inevitably contributes
> to define their neighbor's perception of the quality of the neighborhood»
> — Martínez, p. 8

> «When such an effect is associated with the increment on density, this type of
> location externality is called an agglomeration economy» — p. 29

> «the variability in the location choice process softens the reaction of agents
> after a relocation of neighboring agents, thus reducing the strength of the
> cascade changes induced by location externalities» — p. 116

La última frase presupone la cascada: los agentes se relocalizan, eso cambia la
atractividad, y eso vuelve a moverlos. El punto fijo de Martínez incluye ese
lazo. El de acá no.

**Por qué importa.** `ρ·dens` **no modela congestión residencial**: ningún hogar
puede mover la magnitud por la que se lo penaliza. Es un atributo fijo de la
parcela, estructuralmente indistinguible de un segundo término de accesibilidad
— y en la geometría por defecto es *casi literalmente* el mismo término, con
`corr(T, dens) = −0,996` (AU-12).

Consecuencias: no hay cascada, no hay equilibrios múltiples inducidos por
externalidades, y la segregación que produce el modelo sale sólo de la puja
diferencial por accesibilidad, no de que los estratos se atraigan o se repelan
entre sí. Cualquier lectura pedagógica que hable de «congestión» sobre este ρ
está prometiendo un mecanismo que no está implementado.

**Veredicto.** Simplificación que estaba sin declarar; queda declarada.
Implementar la externalidad es cambio de modelo —`f` tendría que entrar al punto
fijo como función de `Q`— y toca convergencia, línea base y unicidad del
equilibrio. No se hace acá.

**Encontrada** el 2026-09-02, a partir de una observación de Leandro: `ρ`
penaliza una densidad que el modelo nunca mueve.

## D-33 — Transporte homoscedástico y una sola función de utilidad para el hogar

- **Síntoma.** El mismo hogar valoraba su tiempo con dos números: en transporte
  `b_tiempo_viaje/b_costo` daba 6.200 / 3.100 / 1.600 $/h (razón alto/bajo
  3,875), y en uso de suelo `α/λ` con λ = 1 daba 6,5 / 6,0 / 5,5 (razón 1,18).
- **Causa, en transporte.** La recalibración de ago-2026 ajustó **sólo** `b_costo`
  para llevar el VoT del original ($41.250/h el alto) a los valores pedidos,
  dejando `b_tiempo_viaje` heredado (0,055 / 0,0331 / 0,015). Eso dejó un
  `b_costo` **no monótono** (0,000532 / 0,000641 / 0,000563: el medio valoraba
  más un peso que el bajo). No era una preferencia: era el residuo de cuadrar
  el VoT sobre escalas heredadas.
- **Lo que revela.** Multiplicar el bloque entero de betas de un estrato por
  `k` no cambia ninguna razón interna (minutos-equivalentes, ASC en minutos,
  VoT): sólo cambia la escala del ruido Gumbel de ese estrato. Así que un
  `b_tiempo_viaje` distinto por estrato **no era heterogeneidad en la
  preferencia por el tiempo, era heteroscedasticidad**: el alto elegía modo con
  un ruido 3,7× menor que el bajo, sin que nadie lo hubiera decidido. Lo mismo
  vale en el suelo: dado el VoT, repartirlo entre `α` y `λ` sólo fija la
  escala de ruido de cada estrato (medido: Theil 0,911 vs 0,907 vs 0,899 para
  tres anatomías con el mismo VoT).
- **Decisión (2026-09-04).** Transporte **homoscedástico**: `b_tiempo_viaje =
  0,0331` en los tres estratos (la escala del medio, 50 % de la población); el
  bloque del alto se reescaló por 0,0331/0,055 y el del bajo por 0,0331/0,015.
  `b_costo = 0,0331·60/VoT` sale monótono solo: 0,000320 / 0,000641 /
  0,001241. **Toda** la heterogeneidad del VoT vive ahora en la utilidad
  marginal del ingreso, que decrece con el ingreso — la única pieza con teoría
  detrás. Uso de suelo **importa** esa anatomía: `α = 6` común y
  `λ_h = VoT_medio/VoT_h = (0,5 · 1 · 1,9375)`. Un hogar, una función de
  utilidad.
- **Alternativas medidas y descartadas.** (a) Homoscedástico a la escala del
  alto (0,055): el bajo cae a 1,9 % de auto. (b) A la del bajo (0,015): el alto
  cae de 57 % a 38 %. (c) «Monótono mínimo» —conservar las escalas heredadas y
  bajar apenas la del medio—: no mueve nada, pero deja el VoT viviendo en `α`
  y `λ` casi plano, o sea la historia del original y no la de la teoría.
  (d) `λ ∝ 1/y` (utilidad logarítmica): implica VoT proporcional al ingreso
  (razón 8,3), inconsistente con la calibración de transporte contra el SNI y
  con la evidencia de elasticidad-ingreso del VoT bien por debajo de 1.
- **Lo que se mueve.** Línea base en las dos ramas (auto −1,6 pp; ver
  `tests/test_linea_base.py` y el `CLAUDE.md`). Por estrato, sobre viajeros,
  sin uso de suelo: auto 47,7 / 22,6 / 3,7 % (antes 57,4 / 22,0 / 5,8). Nótese
  que el «46,3 / 19,2 / 6,4» que citaba `presets.py` no tenía denominador ni
  fecha y no se pudo reproducir; se reemplazó por el valor medido.
- **Lo que queda libre y declarado.** El nivel de `α` (sólo `β·α` está
  identificado, AU-13) y el de `λ` (escalarlos todos es escalar `β`). Con
  `α = 6` y `β = 1`, el suelo asume que localizarse es ~180 veces más
  determinista que elegir modo (`b_tiempo_viaje = 0,0331`): razón señal/ruido
  177:1, Theil 0,91. Ese `β` es una decisión pedagógica pendiente (AU-10).
- **Invariantes.** `tests/test_presets.py` (escala del tiempo común, `|b_costo|`
  creciente del alto al bajo, ASC del auto = 20 min en los tres) y
  `tests/test_vot_consistente.py` (mismo VoT en ambos módulos, `α` común, `λ`
  decreciente en el ingreso).
- **Veredicto**: calibración corregida en la raíz, con cambio de línea base
  declarado. Ninguna ecuación se tocó.

---

## D-34 — Uso de suelo: la accesibilidad es el logsum de transporte, con α = 1 (el ancla del original, recuperada)

- **Síntoma.** `α` y `ρ` no salían de ninguna parte. `α = 6,5/6,0/5,5` era el
  `[1,3, 1,2, 1,1]` del constructor de `Ciudad2.py` ×5 por el cambio de unidades
  (D-26); `ρ = 0,0025` salió de rebalancear la grilla el 2026-08-24. En el
  Overleaf original, `α_h` se define como «factor que acompaña al coste de
  transporte, para tener más control sobre el mismo» y `ρ` como «factor de
  penalización a la densidad», sin un número justificado. La app original ni
  siquiera llamaba a `actualizar`: corría con los defaults del constructor y
  `T` = distancia en celdas.
- **Lo que sí traía el original.** `construir_T_desde_csv` cargaba
  `LogSuma_Utilidad` por (estrato, celda) —el **logsum del logit modal**— y el
  demo y el `.tex` llamaban `actualizar(T, alpha=[1,1,1])`. O sea: `α = 1` sobre
  la utilidad esperada del viaje, en utiles de transporte. Esa vía nunca se
  ejecutó (el CSV no existe en el repo, `app.py` no lo produce) y tenía el
  signo al revés (`f = −α·T` con `T` = logsum penaliza la buena accesibilidad),
  pero es la única definición de `α` con significado.
- **Decisión (2026-09-04).** Recuperarla, con unidades que cierren:
  `T_h(i) = −VIAJES_MES · logsum_h(i)` (utiles de transporte por mes; el signo
  lo vuelve costo y los 44 viajes lo ponen en la escala mensual del arriendo `p`
  y el ingreso `y`, D-27), `α = 1` común, `λ_h = |b_costo_h|` literal (utiles
  por peso), `β = 1` (el mismo ruido Gumbel que un viaje). Con eso el score
  `y + f/λ` está en $/mes, el VoT `α/λ · b_tiempo · 60` es exactamente el de
  transporte en nivel, y el ruido de la puja `1/λ_h` = $3.122 / $1.561 / $806
  al mes. `β` pasa a ser la **única perilla propia** del módulo y tiene lectura:
  «cuánto más ruidoso es elegir casa que elegir modo».
  Implementado en `land_use/accesibilidad.py`; el standalone recibe `demand`
  (`/land-use/solve`, `landUseSolve`) porque sin los betas no hay accesibilidad.
- **D-22, revisada.** El logsum es por estrato por naturaleza. D-22 promediaba
  la accesibilidad entre estratos porque `T` en minutos por estrato invertía
  Alonso (el auto del rico le aplanaba el tiempo). Medido con el logsum en
  pesos: **no invierte** —alto 0,72 km, medio 2,97, bajo 6,69; Theil 0,75— y la
  variante común ponderada da 0,88. La heterogeneidad de acceso vuelve a la
  puja, que es donde corresponde. Guard: `tests/test_accesibilidad.py`.
- **`ρ`, todavía sin fuente.** Se fija para que `ρ·dens` recorra el 50 % del
  rango de `α·T` del estrato medio en la ciudad por defecto (decisión
  2026-09-04): `0,5·87,4/8.410 = 5,2·10⁻³`. Gradiente de renta +0,75. La
  asignación se invierte al 200 % (≈1,0·10⁻²), antes que el gradiente de precios
  (~300 %): el slider topa en 0,01.
- **Lo que mide.** Un mes de viajes es mucho dinero frente al ruido de un
  viaje: el rango centro–borde vale $212k/$136k/$84k al mes contra ruido de
  $3k/$1,5k/$0,8k, señal/ruido ~90:1, así que con `β = 1` la ciudad sigue
  nítida. `k = 1` (un solo viaje contra el arriendo) da Theil 0,009: por eso el
  factor mensual no es opcional. Escalar `α` sin `ρ` NO equivale a bajar `β`
  (cambia el balance accesibilidad/densidad e invierte Alonso con `α = 0,0331`);
  la perilla honesta es `β`.
- **Lo que se mueve.** Sólo la rama `equilibrio` de la línea base, y poco:
  auto 15,19 → 15,22, metro 35,31 → 35,18, bici 22,70 → 22,75, caminata 7,34 →
  7,42. `original` intacta. El acoplado arranca y itera con el mismo objeto
  (`T_flujo_libre` y `_T_logsum_snapshot`); `T_residual` queda en utiles de
  transporte por mes.
- **`β` = 0,15 ≈ 1/√44 (decisión 2026-09-04).** Con `β = 1` la señal está
  mensualizada ×44 pero el ruido es el de un viaje: eso supone que el gusto por
  una casa es un solo sorteo, y da Theil 0,75. Si el ruido también se acumula
  viaje a viaje (iid), su escala mensual crece como √44 ≈ 6,6 y la razón
  señal/ruido honesta es 6,6 veces menor. Ninguna hipótesis se estima con estos
  datos; se eligió la que no infla la nitidez. Medido: Theil 0,16, alto/medio/
  bajo 2,15 / 3,11 / 5,50 km, gradiente +0,78, 29 iteraciones. Mueve la rama
  `equilibrio` (metro −3,0 pp, caminata +1,65): declarado en `test_linea_base`.
  Los otros dos caminos a un Theil menor con `β = 1` son trampa: bajar `α` sin
  `ρ` cambia el modelo (invierte Alonso), y bajar la escala de `λ` es `β` con
  otro nombre rompiendo el nivel del VoT.
- **UI.** `α` y `λ` se editan sin poder romper las razones: un control común
  para `α` y una *escala* para `λ` (`λ_h = escala·|b_costo_h|`, leídos de la
  demanda de transporte). `β` en 0,01–2; `ρ` en 0–0,01.
- **Invariantes.** `tests/test_vot_consistente.py` (`α = 1`, `λ = |b_costo|`
  exacto, VoT igual en nivel, `λ` decreciente, HEV), `tests/test_accesibilidad.py`
  (logsum = el del logit modal; `T` es un costo creciente; por estrato no
  invierte Alonso), `tests/test_coupled.py` (accesibilidad por estrato).
- **Veredicto**: ancla del original recuperada y hecha consistente. `ρ` sigue
  siendo la única cantidad sin fuente, declarada como decisión.

---

## Auditoría externa del 2026-09-05 (D-35 a D-44)

Una auditoría científica y numérica hecha por ChatGPT («ASTRA») sobre `b9afa73`
—carpeta `docs/auditoria-2026-09-05/`, **no versionada**— reportó 14 hallazgos
(A01–A14). Se contrastó cada uno contra el código y por medición
(2026-09-05). Lo que sigue registra los que se confirmaron, con el veredicto
propio y el estado; los descartados o ya documentados se anotan al final.
Convención de esta tanda: **Estado** `pendiente` → `corregido <fecha>`.

## D-35 — Acoplado: el bienestar total multiplica el excedente *por viajero* por *todos* los hogares (A03)

- **Evidencia**: `coupled_metrics.py`, `compute_equilibrium_metrics`. `cs_medio =
  cs_sum/nv` promedia sólo sobre quienes viajan (excluye teletrabajo y varados);
  luego `bienestar_total = Σ_h cs_medio·n_hogares`, con `n_hogares` = todos.
  Infla la magnitud en ≈ n_hogares/nv (≈ 20 % en la base).
- **Veredicto**: error contable. El teletrabajador tiene ΔCS = 0 y el varado no
  tiene medida: el total es la suma sobre la población elegible, no un promedio
  reescalado. Corrección: acumular sobre los pesos de quienes viajan y explicitar
  el período; decidir y declarar qué se hace con los varados (hoy se omiten en
  silencio, lo que puede *mejorar* un promedio al empeorar la red).
- **Estado**: pendiente.

## D-36 — Bienestar: los tren-km se despejan de las emisiones, así que un factor de emisión 0 anula el costo del operador (A05)

- **Evidencia**: `bienestar.py`: `tren_km = trace.emisiones_metro_kg / factor_em
  if factor_em > 0 else 0.0`. El comentario declara que se hizo para no duplicar
  la fórmula `f_op·span·2` de `emissions.py`. Con factor 0 (metro
  descarbonizado) el costo operador pasa de ~$5,6 M a $0 y el bienestar «mejora»
  en esa cifra con el mismo servicio.
- **Veredicto**: bug. Corrección: `emissions.py` expone los tren-km (o el trace
  los serializa) y `bienestar.py` los consume; test con factor 0.
- **Estado**: pendiente.

## D-37 — Bienestar: el costo generalizado aplica el VoT en vehículo a todos los minutos (A04)

- **Evidencia**: `bienestar.py`: `cg_percibido += d·((minutos/60)·vot_h + dinero)`
  y `cg_social += d·((minutos/60)·vot_social + dinero)` con `minutos` =
  acceso + espera + viaje. La utilidad que decide el modo pondera espera y
  acceso ×2 (`b_tiempo_espera`, `b_tiempo_acceso`; ponderador 2 de la tabla 2.1
  del SNI que el propio `presets.py` cita) y la caminata ×1,7. En la base, sólo
  la corrección del metro mueve el agregado social ~13,7 %.
- **Veredicto**: el «costo percibido» no es el equivalente monetario de la
  utilidad, y el «costo social» no sigue la tabla que dice seguir. Corrección:
  costo por componente de tiempo con sus ponderadores, y presentar el excedente
  social reescalado como lo que es (una agregación distributiva), no como
  cumplimiento de la metodología SNI.
- **Estado**: pendiente.

## D-38 — Theil ponderado por celdas, no por hogares (A06)

- **Evidencia**: `coupled_metrics._theil(Q)` usa `Q.sum(axis=0)` = 1 como peso
  de cada celda habitada, así que una celda con 5 hogares pesa lo mismo que una
  con 300. `LandUsePage.tsx` y `ComparePage.tsx` hacen lo mismo en TS (espejo).
  En la base la diferencia es chica (3,4 %); con ofertas no uniformes puede
  cambiar el orden entre escenarios.
- **Veredicto**: el índice poblacional requiere `N_hi = S_i·Q_hi`. Corrección:
  un único Theil poblacional calculado en el núcleo y expuesto por
  `serializacion.py` (cae el espejo TS); si se conserva el territorial, con otro
  nombre.
- **Estado**: pendiente.

## D-39 — Convergencia: el residual del MSA se mide después de amortiguar, y «terminó» se rotula «convergió» (A01, A02)

- **Evidencia (A01)**: `msa.py::_iter_loop`. Con `promediar_flujos` la demanda se
  promedia con paso `1/(it+1)` y el residual mide el cambio del *promedio*; el
  desajuste entre la oferta recién evaluada y el estado es `(it+1)` veces eso.
  En la base con suelo, 0,072 min de residual a la 8ª iteración son ~0,5 min de
  brecha, contra una tolerancia publicada de 0,1.
- **Evidencia (A02)**: `coupled.py`: `is_converged = outer > 0 and residual <
  outer_tol`, sin exigir `transport_trace.converged` ni la convergencia del
  suelo; con `max_iter=1` interior devuelve `converged=True`. En la web,
  `RunStatus.tsx` traduce `stage === "done"` como «Equilibrio alcanzado» y
  `CoupledPage.tsx` construye `converged: stage === "done"`. El campo
  `residual_final_min` sigue nombrado en minutos aunque desde D-34 `T` va en
  utiles de transporte por mes (los textos se corrigieron en `b9afa73`; el
  nombre y la lógica no).
- **Veredicto**: el criterio de parada por cambio del iterado es el estándar de
  MSA en código docente y no prueba que el punto fijo no exista, pero la
  tolerancia publicada **no acota** lo que la interfaz sugiere. Corrección:
  publicar además un *gap* no amortiguado (recalcular demanda y oferta al estado
  final), separar «finalizó» de «convergió» en núcleo y UI, exigir las tres
  convergencias en el acoplado, renombrar el residual con su unidad.
- **Estado**: pendiente.

## D-40 — Acoplado: el estado final no es el de la última iteración, y las métricas reciben otro `assignment` que la corrida (A07, A08)

- **Evidencia (A07)**: al agotar `outer_max_iter` sin converger, `city.update(T_state)`
  corre *después* del último `yield`: `final_city` es una ciudad que nunca vio
  transporte, mientras `final_agents` y las métricas son de la anterior. Con un
  paso exterior, `max|ΔQ| = 0,19` entre ambas.
- **Evidencia (A08)**: `sim_eq = sim.model_copy(update={"assignment": "expected"})`
  corre el transporte, pero `compute_equilibrium_metrics(sim=sim)` recibe el
  original: si el usuario pidió `todo_o_nada`, el flujo es logit y el excedente
  se rotula `utilidad_maxima`.
- **Veredicto**: inconsistencias de contrato. Corrección: no actualizar la
  ciudad al salir si no se va a simular su transporte (o simularlo y emitir ese
  estado); pasar la configuración *efectiva* a las métricas y al usuario, o
  rechazar `todo_o_nada` en el acoplado explícitamente.
- **Estado**: pendiente.

## D-41 — Suelo: el control «λ · escala» es inerte sobre la asignación, y β = 1/√44 es una aproximación de segundo momento (A10, A11)

- **Evidencia (A10)**: medido: `λ × 0,1` → `max|ΔQ| = 4·10⁻¹⁴`, rango de precios
  ×10. Es la invariancia de AU-13 vista desde `λ`: el determinístico `f/λ` y el
  ruido `1/(β·λ)` escalan juntos, y `ρ/λ` escala igual que `α/λ`, así que
  tampoco cambia el balance con la densidad. El *hint* del control en
  `LandUseBuilder.tsx` (introducido en `b9afa73`) afirma lo contrario: **falso**.
  Lo único que mueve esa escala es la unidad monetaria de las rentas.
- **Evidencia (A11)**: la suma de 44 Gumbel no es Gumbel; escalar el ruido por
  √44 es un ajuste de segundo momento, y los shocks de vivienda no están
  justificados como 44 shocks de viaje iid. El comentario de `config.py`
  (`920e176`) lo presenta como hipótesis alternativa, no como derivación, pero
  debe decir «aproximación de segundo momento, no estimada».
- **Veredicto**: ambos ciertos y propios. Corrección: quitar el control o
  reetiquetarlo como unidad monetaria; corregir el comentario de `β`; agregar un
  test de que la escala común de λ no mueve `Q`.
- **Estado**: pendiente.

## D-42 — Suelo standalone: «flujo libre» no usa la red configurada (A09)

- **Evidencia**: `T_flujo_libre` usa `_tiempos_flujo_libre` (velocidades de la
  demanda, acceso 10 min y espera 5 min fijos), no la red vacía con las
  estaciones y frecuencia mínima configuradas. Cambiar estaciones o velocidad
  del metro no mueve el suelo standalone. Diferencia máxima con la red vacía
  real en la base: 14,7 utiles/mes.
- **Veredicto**: herencia, no regresión (antes de D-34 el standalone ignoraba la
  oferta por completo) y es la misma convención de la iteración 0 del MSA. Pero
  `resolver_red_vacia` (`supply/oferta.py`) y `_tiempos_red_vacia`
  (`coupled_metrics.py`) ya existen: el standalone debe recibir la oferta y usar
  la red vacía, que además es el baseline con el que el acoplado mide ΔCS.
- **Estado**: pendiente.

## D-43 — Validación de dominios y precisión de la cuadratura HEV fuera de la base (A13)

- **Evidencia**: el schema acepta `v_auto = 0`, `b_costo = 0` y shares
  negativos; la cuadratura HEV es de grilla fija (401 nodos en [−10, 40]) y con
  razones de escala 100 y 10.000 el error absoluto de probabilidad llega a
  0,005 y 0,008; normalizar columnas lo esconde.
- **Veredicto**: cierto, acotado a entradas por API o archivo (ningún `b_costo`
  razonable produce esas razones). Corrección: validadores de dominio en los
  schemas; en HEV, grilla adaptada a la razón de escalas o cuadratura adaptativa
  y exigir balance de hogares al declarar convergencia.
- **Estado**: pendiente.

## D-44 — Redondeos, muestras y convenciones geométricas (A14)

- **Evidencia**: la población entera derivada del suelo conserva `S` por celda
  pero no `H` por estrato (7.194/17.998/10.808 en la base); la página de suelo
  muestra una realización aleatoria mientras el acoplado usa esperanzas; auto y
  bici descuentan medio tramo propio al acumular tiempos (0,096 vs 0,193 min en
  la celda vecina al CBD).
- **Veredicto**: cierto, de baja prioridad. Corrección: redondeo con márgenes,
  métricas esperadas para comparar, convención origen/destino documentada.
- **Estado**: pendiente.

**Descartados o ya cubiertos.** A12 (`/simulate` con densidad plana vs. motor
local con suelo) es C-02, documentado en `api.ts`; la diferencia de 9 pp que
mide es real y unificar el contrato es decisión aparte. La observación de §4.2
—que la forma cerrada con `λ` heterogéneo es *otro supuesto* (precisiones de
utilidad distintas), no un modelo inválido— es correcta y corrige la redacción
de D-08. El dictamen general («no certificar como equilibrio validado ni como
evaluación social») es cierto como afirmación, pero nadie lo afirmó: lo que
importa de él es que las etiquetas de la UI prometen más de lo que el cálculo
cumple, y eso está en D-39.

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
| D-22 | Acoplado: accesibilidad común por ubicación (no por estrato) | Bug del modelo corregido | Alta |
| D-23 | Acoplado: baseline "sin feedback" en min a flujo libre (no índices) | Artefacto de unidades corregido | Alta |
| D-24 | Acoplado: gridlock monocéntrico → población por escenario | Acotado por config (robustez pendiente) | Media |
| D-25 | Suelo: Q sin ponderación H_h (no conservaba hogares por estrato) | Bug del port corregido | Alta |
| D-26 | Suelo: unidades físicas (T en min, densidad hog/km) → invariancia de grilla | Bug de unidades corregido (decisión de modelo) | Alta |
| D-27 | Carga mensual costo/ingreso con y en $/mes | Unidades corregidas | Media |
| D-28 | Transporte: densidad física hab/km (n_celdas puramente numérico) | Continuación de D-26 | Alta |
| D-29 | Emisiones de metro por tren-km (economías de escala visibles) | Corrección conceptual | Media |
| D-30 | Tres baselines de "sin congestión" (convenciones) | Documentado, sin cambio de código | Baja |
| D-31 | Suelo: `beta` en espacios distintos a cada lado del despacho (salto de 4,7 pp) | Bug corregido, línea base intacta | Alta |
| D-32 | Suelo: `ρ·dens` exógeno — sin externalidad de localización (Martínez) | Simplificación declarada, sin cambio de código | Media |
| D-33 | Transporte homoscedástico; suelo importa la anatomía (α común, λ ∝ b_costo) | Calibración corregida, línea base movida y declarada | Alta |
| D-34 | Suelo: accesibilidad = logsum mensual de transporte, α = 1, λ = |b_costo|, β = 1/√44; D-22 revisada | Ancla del original recuperada, línea base movida y declarada | Alta |
| D-35 | Acoplado: bienestar total = excedente por viajero × todos los hogares | Pendiente (auditoría 2026-09-05) | Alta |
| D-36 | Bienestar: tren-km despejados de emisiones; factor 0 anula el costo operador | Pendiente (auditoría 2026-09-05) | Alta |
| D-37 | Bienestar: costo generalizado sin ponderadores de espera/acceso | Pendiente (auditoría 2026-09-05) | Alta |
| D-38 | Theil ponderado por celdas, no por hogares (y espejo TS) | Pendiente (auditoría 2026-09-05) | Media |
| D-39 | Convergencia: residual amortiguado; «terminó» rotulado «convergió»; residual en «minutos» | Pendiente (auditoría 2026-09-05) | Alta |
| D-40 | Acoplado: estado final de otro paso; `assignment` distinto en métricas | Pendiente (auditoría 2026-09-05) | Media |
| D-41 | Suelo: «λ · escala» inerte sobre Q; β = 1/√44 es aproximación de 2º momento | Pendiente (auditoría 2026-09-05) | Media |
| D-42 | Suelo standalone: flujo libre sin la red configurada | Pendiente (auditoría 2026-09-05) | Media |
| D-43 | Validación de dominios; cuadratura HEV fija fuera de la base | Pendiente (auditoría 2026-09-05) | Media |
| D-44 | Redondeos, muestras y convenciones geométricas | Pendiente (auditoría 2026-09-05) | Baja |
