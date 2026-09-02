# Plan: el efecto de ρ en la subasta de suelo

Plan de análisis para determinar **qué hace ρ en el modelo implementado**, qué
rango o qué diferencias entre estratos producen una asignación realista, y
cuánto de lo que hace ρ es propio y cuánto es α disfrazado. Escrito para que lo
ejecute una sesión nueva sin acceso a la conversación que lo originó: todo lo
que hace falta saber está acá o en los archivos que se citan.

Fecha: 2026-09-02. Estado del repo al escribirlo: rama
`ciudad-equilibrio-mejoras`, HEAD `246be2a`, working tree limpio (los `.tsx`
que `git status` muestra como modificados son fantasmas CRLF; `git diff` sobre
ellos está vacío).

---

## 0. Antes de empezar — leer, en este orden

1. `CLAUDE.md` (raíz) — convenciones, comandos, gotchas. Obligatorio.
2. `docs/DISCREPANCIES.md`, entradas **D-31** y **D-32**.
3. `docs/AUDITORIA_USO_SUELO.md`, entradas **AU-05** (con su corrección del
   2026-09-02), **AU-06**, **AU-11**, **AU-12**.
4. `packages/titirilquen_core/src/titirilquen_core/land_use/equilibrium.py` —
   docstrings de `_f`, `solve_logit`, `solve_subasta`.
5. `packages/titirilquen_core/scripts/auditoria_suelo.py` — secciones 2, 2b y
   6b; y la función `resolver()`, que ya calcula las métricas de este plan.
6. `sandbox/impacto-hev/` entero — es el **patrón** a seguir: `impacto.py`
   calcula y escribe `salida/impacto.json`, `figuras.py` dibuja, `informe.html`
   presenta. Reutilizar la estructura, no reinventarla.

---

## 1. La pregunta

> ¿Cuál debería ser el rango de ρ, o las diferencias de ρ entre estratos, para
> que la asignación resulte realista dado el modelo?

Y la pregunta previa que la condiciona:

> ¿Qué puede hacer ρ en este modelo, y qué no?

El resultado del plan es una **región admisible** en el espacio de parámetros
de ρ, con las restricciones de realismo como bordes, más una cuantificación de
cuánto de ese efecto es separable de α.

---

## 2. Estado de partida — lo ya establecido

Todo esto está verificado y documentado. No re-derivar; citar.

### 2.1 El modelo

Puja del estrato `h` por la parcela `i` (Martínez 2018, ec. 4.3; código en
`equilibrium.py`):

    score_h(i) = y_h + f_h(i) / λ_h
    f_h(i)     = −α_h · T_h(i) − ρ_h · dens(i)
    dens(i)    = S_i / Δx                       (hogares/km)

- `T_h(i)` en minutos, indexado por estrato (viene del módulo de transporte;
  en la corrida aislada es `_default_T`, proporcional a la distancia al CBD).
- `S` es la **oferta** de viviendas por celda, generada una vez por
  `generar_oferta(forma, oferta_sigma_frac)`. Exógena. **Nunca cambia** durante
  el equilibrio (D-32).
- `λ_h` utilidad marginal del ingreso; `β` precisión del ruido en útiles.
- Con λ uniforme la subasta usa la forma cerrada (logit); con λ heterogéneo
  despacha al HEV (`hev.py`), que es ~4× más lento y converge en más
  iteraciones (AU-09).

### 2.2 Hechos que el plan da por sentados

| ID | Hecho | Dónde |
|---|---|---|
| D-31 | La precisión en dinero es `b_h = β·λ_h`, no `β`. El despacho era discontinuo; corregido. Martínez p. 242 lo nombra como ambigüedad de identificación. | DISCREPANCIES |
| D-32 | `dens` es exógena; el mercado se vacía (`Σ_h Q[h,i] = 1`, `ΣS = ΣH`), así que la densidad realizada es idénticamente `S/Δx`. **ρ·dens no es congestión residencial**: ningún hogar puede mover lo que se le penaliza. | DISCREPANCIES |
| AU-05 | ρ uniforme **no reasigna si λ es uniforme** (se absorbe en `p_i`), pero aplana el gradiente de precios. **Con λ heterogéneo sí reasigna**, porque lo que entra es `ρ_h/λ_h`. Con λ = (0,5·1·2) y ρ = 0,05 la ciudad se invierte. | AUDITORIA §AU-05, script §2b |
| AU-11 | Con ρ = 0,1 el gradiente de precios salía invertido (periferia más cara). Recalibrado a 0,0025. La razón de balance `≈ α·(L/2)²·1,253/(ρ·N)` va con el cuadrado del número de celdas. | AUDITORIA §AU-11, `config.py` |
| AU-12 | En la forma `normal`, `corr(T, dens) = −0,996`: `dens ≈ a − b·T`. α y ρ **no se identifican por separado**; sólo la combinación. `bimodal` es la única forma que los separa (corr −0,098). Martínez p. 242: la identificación viene de la variabilidad espacial — es propiedad de nuestra geometría, no de la clase de modelo. | AUDITORIA §AU-12, script §6b |
| AU-13 (medido, no documentado aún) | El **nivel** de α no está identificado: escalar (α, ρ) por k y β por 1/k deja Q idéntico (max\|ΔQ\| ≈ 2·10⁻⁹ hasta k = 1000). Sólo `β·α` es observable. Martínez p. 243 da una ruta para anclar β (ley de escala `R = β·ln N`) que no está implementada. | medido en sesión; **el ejecutor debe agregarlo al script como sección 10 y a AUDITORIA como AU-13** |

### 2.3 La calibración pendiente (NO aplicada todavía)

Decisiones tomadas por Leandro el 2026-09-02, aún **sin tocar `config.py`**:

- **λ lleva el efecto ingreso; α uniforme.** Fuente: Martínez p. 77 («it is
  expected that λ_h decreases with income») y Jara-Díaz, *Transport Economic
  Theory* (en `reference/`), ec. (2.25)/(2.28): `SVTTS = (∂V/∂t)/(∂V/∂c) = w`,
  el valor subjetivo del tiempo es la tasa salarial. Ese cociente **es**
  `α/λ`. Empíricamente, MUI decreciente con el ingreso en Santiago:
  Jara-Díaz & Videla (1989), citado en p. 57 del libro.
- Con horas trabajadas iguales entre estratos, `w ∝ y` ⇒ `e_t = 1` ⇒
  `λ_h ∝ 1/y_h`. Normalizando `λ_medio = 1`: **λ = (0,43 · 1,00 · 3,00)**,
  α = 6,0. Cuesta ~5× en tiempo de cómputo (4,6 s vs 0,9 s la corrida
  acoplada por defecto en CPython; en Pyodide, más).
- **ρ queda abierto.** No hay fuente para la elasticidad ingreso de la demanda
  de espacio: ni Jara-Díaz (es de transporte) ni Martínez (no publica valores
  numéricos de ningún parámetro; verificado en las 296 páginas). **Este plan
  es el insumo para cerrarlo.**

Defaults vigentes en `config.py`: `α = 6,5 / 6,0 / 5,5`, `ρ = 0,0025 ×3`,
`λ = 1 ×3`, `β = 1`, `y = 3,5M / 1,5M / 0,5M` $/mes, `forma = normal`,
`oferta_sigma_frac = 0,5`.

### 2.4 Lo que NO se va a hacer

- **No** implementar la externalidad endógena (`f` dentro del punto fijo).
  Decidido explícitamente; queda declarado en D-32.
- **No** cambiar los defaults de `config.py` como parte de este plan. El plan
  informa esa decisión; no la ejecuta. Si al final se decide cambiar, es un
  commit aparte que re-pinea `test_linea_base.py` y lo declara.
- **No** inventar referencias ni elasticidades. Donde falte un dato empírico,
  el plan lo deja como **ancla pendiente** (§9) y el ejecutor lo pide.

---

## 3. Marco analítico — qué puede hacer ρ, derivado antes de medir

Esto es lo que el modelo *tiene* que hacer por construcción. Cada afirmación
se convierte en una predicción verificable (§3.4). Si una medición la
contradice, hay un bug o un error de derivación — no un hallazgo.

### 3.1 Las tres reglas de absorción

La probabilidad de que `h` gane la parcela `i` depende de
`b_h·(score_h(i) − ū_h − p_i)`. De ahí:

1. Un término **constante por estrato** (depende de `h`, no de `i`) se absorbe
   en `ū_h`. No mueve Q. Ejemplo: `y_h`.
2. Un término **constante por parcela** (depende de `i`, no de `h`) se absorbe
   en `p_i`. No mueve Q, **pero mueve el precio**. Ejemplo: `ρ·dens(i)/λ` con
   ρ y λ uniformes — de ahí AU-05.
3. Sólo las **interacciones** `h × i` mueven la asignación.

### 3.2 Los dos canales en dinero

Definir

    v_h = α_h / λ_h      valor del tiempo ($/min)
    r_h = ρ_h / λ_h      aversión a la densidad en dinero ($ por hogar/km)

La parte de la puja que interactúa es `−v_h·T(i) − r_h·dens(i)`. La asignación
depende de la **dispersión entre estratos** de `v_h` y de `r_h`, multiplicada
por la **variabilidad espacial** de `T` y de `dens` respectivamente.

### 3.3 El coeficiente efectivo κ

En la forma `normal`, `dens(i) ≈ a − b·T(i)` (AU-12, R² = 0,991). Entonces

    −v_h·T − r_h·dens ≈ −(v_h − b·r_h)·T + cte_h

y la constante se absorbe (regla 1). Queda **un solo coeficiente por estrato**:

    κ_h = v_h − b·r_h = (α_h − b·ρ_h) / λ_h

**El estrato con mayor κ_h gana el centro.** Rico central ⟺ κ creciente en el
ingreso. Para el HEV la lógica del parámetro de localización es la misma; lo
que cambia es la escala del ruido por estrato (§3.5).

`b` es una **tasa de cambio entre ρ y α**: ρ entra en la asignación como si
fuera una reducción de α en `b·ρ`. Medido en la ciudad por defecto
(L = 201, 20 km, ΣH = 99.900, forma normal): **b ≈ 423 hogares/km por
minuto**. Entonces ρ = 0,0025 ≡ −1,06 útiles/min sobre α = 6, y
ρ ≈ 0,0142 anula el tirón del centro para el estrato medio (κ = 0).

**Ojo**: `b` depende de la geometría **y de la población** (`dens ∝ N`). Hay
que recalcularlo para cada configuración que se use; no copiar el 423.

### 3.4 Predicciones que el plan debe confirmar o refutar

| # | Predicción | Si falla… |
|---|---|---|
| P1 | ρ uniforme + λ uniforme ⇒ Q invariante a ρ (max\|ΔQ\| ≲ 10⁻⁸), `p` cambia. | bug en la absorción, o el solver no converge. |
| P2 | ρ uniforme + λ heterogéneo ⇒ Q **sí** cambia, y el efecto crece con la dispersión de `1/λ_h`. | AU-05 corregido está mal. |
| P3 | Con λ uniforme, la pareja `(α_h, ρ_h)` y la pareja `(α_h − b·ρ_h, 0)` dan la misma Q salvo el residuo `dens − (a − bT)`. En `normal` el residuo es chico; en `bimodal` no. | AU-12 está mal, o `b` mal estimado. |
| P4 | El orden de los estratos en el espacio sigue el orden de κ_h. La inversión ocurre exactamente cuando κ_alto cae por debajo de κ_medio. | la reducción a κ no captura algo (p. ej. el efecto del ruido). |
| P5 | El nivel ρ_0 (común) fija el gradiente de precios dado α, y su efecto sobre Q es nulo (λ unif.) o de segundo orden (λ het.). | — |
| P6 | Bajo HEV con λ ∝ 1/y, el estrato alto tiene `θ_alto = 1/(β·λ_alto)` ≈ 2,3× `θ_medio` ⇒ **más disperso** (mayor `disp_a`) que lo que le correspondería por κ. La forma cerrada no puede producir esta asimetría. | — es un hallazgo del HEV, vale la pena confirmarlo. |
| P7 | Escalar (α, ρ) por k y β por 1/k deja Q idéntico (AU-13). | bug de escala. |

### 3.5 La condición de vuelco (Muth/Wheaton en este modelo)

Con `v_h = A·y_h^{e_t}` y `r_h = R·y_h^{e_s}`:

    κ(y) = A·y^{e_t} − b·R·y^{e_s}

- Si `e_s ≤ e_t` y `κ(y_bajo) > 0`, κ es creciente en todo el rango: rico
  central, sin vuelco.
- Si `e_s > e_t`, κ crece hasta `y* = [(A·e_t)/(b·R·e_s)]^{1/(e_s − e_t)}` y
  decrece después. **El estrato con y > y* se va a la periferia.** El vuelco
  del estrato alto ocurre cuando `y* < y_alto`.

Es la condición clásica de Muth/Wheaton (elasticidad ingreso de la demanda de
suelo vs. del valor del tiempo) escrita para este modelo. `y*` depende de la
brecha `e_s − e_t` **y** del nivel `R` (o sea de ρ_0). El plan mapea esa
frontera numéricamente (E2) y la contrasta con la fórmula.

### 3.6 Parametrización económica de ρ y λ

Usar siempre esta parametrización, que ya está probada (está en el script de
auditoría como `elasticidades()` si el ejecutor la agrega; si no, está en §11):

    λ_h = (y_h / y_med)^{−e_t}                  → v_h ∝ y^{e_t}
    ρ_h = ρ_0 · (y_h / y_med)^{e_s − e_t}       → r_h ∝ y^{e_s}
    α   = α_0 uniforme

con `y_med = 1,5M`, `α_0 = 6,0`, `ρ_0 = 0,0025` (los valores del medio). Con
`e_s = e_t` la ρ queda **uniforme**. La brecha `e_s − e_t` es el único
parámetro que decide el vuelco; `ρ_0` decide dónde está el umbral.

---

## 4. Qué significa «realista» — criterios operacionales

Cada criterio tiene un objetivo. Los marcados **[ancla]** necesitan un dato
empírico que hay que pedir a Leandro (§9); mientras no esté, se reporta la
métrica y se deja el umbral en blanco, **no se inventa**.

| ID | Criterio | Métrica | Objetivo | Estado |
|---|---|---|---|---|
| C1 | **Orden**: el estrato alto más cerca del centro de empleo que el bajo (patrón chileno; el estadounidense es el inverso). | `d_alto < d_medio < d_bajo` | estricto | listo |
| C2 | **Gradiente de precios de Alonso**: el suelo central vale más. | `grad_p > 0` sobre celdas con oferta, excluyendo el CBD (AU-11) | estricto | listo |
| C3 | **Sin corner solution**: ningún estrato expulsado a la periferia extrema ni concentrado en una sola celda. | `disp_a > 0,3 km` y `d_alto < 0,4·(L/2)·Δx` | orientativo | listo |
| C4 | **Mezcla en las fronteras**: anillos puros son irreales; las ciudades reales mezclan a escala fina. | `mezcla = mean_i(1 − max_h Q[h,i])` en `[0,03; 0,25]` | **[ancla]**: el rango es una hipótesis; Leandro lo confirma o lo reemplaza | pendiente |
| C5 | **Intensidad de segregación** comparable a Santiago. | Theil entre celdas (ya en `resolver()`), o Duncan si Leandro prefiere | **[ancla]**: valor publicado para Santiago | pendiente |
| C6 | **Gradiente de renta** de magnitud plausible, no sólo de signo. | `(p_1km − p_10km)/p_1km` o pendiente en $/km | **[ancla]**: gradiente observado en Santiago | pendiente |
| C7 | **Costo de cómputo** aceptable para la app. | tiempo de la corrida acoplada por defecto | ≤ 3× el actual (0,9 s CPython) es tolerable; > 5× hay que decirlo | listo |

**Regla de lectura**: C1 y C2 son *eliminatorios*. C3–C6 delimitan la región.
C7 no es de realismo pero condiciona qué se puede poner de default.

---

## 5. Diseño experimental

Todos los experimentos corren sobre **dos regímenes de λ**, siempre:

- **R0**: λ = (1, 1, 1) con α = (6,5 · 6,0 · 5,5) — la calibración vigente.
- **R1**: λ = (0,43 · 1,00 · 3,00) con α = 6,0 uniforme — la propuesta
  (`e_t = 1`).

Y sobre la **ciudad de la auditoría** (L = 201, 20 km, ΣH = 36.000, shares
10/40/50, forma normal, σ = 0,5), salvo donde se indique otra cosa. Semilla
fija (`np.random.default_rng(42)`) donde haya RNG.

Cada experimento escribe sus números a `salida/*.json` y una o más figuras a
`salida/*.png`. Ninguna cifra del informe puede venir de otro lado.

### E0 — Sanidad y tasa de cambio

**Objetivo.** Confirmar P1 y P7, y medir `b` para cada régimen y geometría.

**Barrido.** Para cada `forma ∈ {normal, exponencial, meseta, bimodal, valle,
uniforme}` y cada régimen: ajustar `dens ≈ a − b·T` por mínimos cuadrados
sobre celdas con oferta, reportar `b`, `R²`, `corr(T, dens)`. Para R0 con
ρ ∈ {0, 0,0025, 0,01, 0,05} uniforme: `max|ΔQ|` vs ρ = 0 (P1). Para
k ∈ {10, 377, 1000}: escalar (α, ρ)·k, β/k, `max|ΔQ|` vs base (P7).

**Salida.** `salida/e0-sanidad.json`. Tabla en el informe.

**Criterio.** P1 y P7 con `max|ΔQ| < 10⁻⁶`. Si no, **parar** y diagnosticar.

### E1 — Nivel de ρ uniforme

**Objetivo.** El efecto del nivel ρ_0 (común a los tres estratos) sobre
localización y precios, en los dos regímenes. Es AU-05 y su corrección,
completados con precios.

**Barrido.** ρ_0 ∈ {0, 0,001, 0,0025, 0,005, 0,01, 0,02, 0,05, 0,1}, ×{R0, R1}.

**Salida.** Por punto: `d_h` (3), `disp_a`, `theil`, `mezcla`, `grad_p`,
`p(i)` completo, iteraciones, tiempo. `salida/e1-nivel.json`.

**Figuras.** (a) `d_h` vs ρ_0, dos paneles R0/R1. (b) `grad_p` vs ρ_0, ambos
regímenes en el mismo panel. (c) perfil `p(i)` para 4 valores de ρ_0, R1.

**Predicciones.** P1 en R0 (d_h planos, grad_p cae y cruza cero cerca de
ρ ≈ 0,05 según AU-11). P2 y P5 en R1.

**Lectura esperada.** Dónde cruza `grad_p = 0` en cada régimen: ése es el
**techo de ρ_0** que impone C2. Reportarlo explícitamente.

### E2 — Brecha de elasticidades y frontera de vuelco

**Objetivo.** Mapear la región `(e_s − e_t, ρ_0)` donde se cumple C1, y
ubicar la frontera de vuelco. Contrastar con la fórmula de `y*` (§3.5).

**Barrido.** Sólo R1 (con R0 la brecha no tiene sentido: λ uniforme). Grilla
`e_s − e_t ∈ {−1, −0,5, −0,25, 0, 0,25, 0,5, 0,75, 1, 1,25, 1,5, 2}` ×
`ρ_0 ∈ {0,001, 0,0025, 0,005, 0,01, 0,02}`. Son 55 corridas HEV; en CPython
~2–5 s cada una. Correr en background si hace falta.

**Salida.** Por punto: `d_h`, `theil`, `mezcla`, `grad_p`, κ_h calculado con
el `b` de E0, y un flag `orden_ok` (C1). `salida/e2-brecha.json`.

**Figuras.** (a) mapa de calor `d_alto` sobre la grilla, con la curva de
vuelco predicha por `y* = y_alto` superpuesta. (b) `d_alto` vs brecha para
cada ρ_0, con la línea `d_medio` de referencia.

**Predicciones.** P4: la frontera numérica coincide con `y*(e_s, ρ_0) = y_alto`
salvo por el efecto del ruido. Si la frontera numérica está sistemáticamente
desplazada, cuantificar el desplazamiento y atribuirlo (§3.4, P6).

**Lectura esperada.** «Para ρ_0 = X, el rico se va a la periferia cuando la
elasticidad de la demanda de espacio supera a la del VOT en más de Y.» Ese Y
es la **cota superior de la brecha** que impone C1.

### E3 — Cuánto de ρ es α disfrazado

**Objetivo.** Cuantificar la redundancia (AU-12) como fracción del efecto, no
como correlación. Para cada geometría.

**Diseño.** Para cada `forma` y para R0: tomar ρ heterogéneo
`(0,0050 · 0,0025 · 0,0010)`, medir `Q_ρ`. Construir el equivalente
`α'_h = α_h − b·ρ_h`, ρ = 0, medir `Q_α`. Reportar
`max|Q_ρ − Q_α|`, `Σ_i |Q_ρ − Q_α|·S_i / 2` (hogares que no reproduce),
y el cociente entre ese número y los hogares que ρ movió respecto de la base.
Ese cociente es **la fracción del efecto de ρ que α no puede imitar**.

Repetir con R1 usando `κ_h` completo (con λ) para construir el equivalente.

**Salida.** `salida/e3-redundancia.json`. Tabla por forma.

**Predicción.** P3: fracción ≈ 1 − R² en `normal` (≈ 1 %), cerca de 1 en
`bimodal`.

**Lectura esperada.** «En la ciudad por defecto, el 99 % de lo que hace ρ lo
hace α. Para que ρ signifique algo propio hay que correr en `bimodal`.»

### E4 — Dónde actúa ρ en el espacio

**Objetivo.** Igual que `impacto-hev` §4: ver si el efecto se concentra en las
fronteras entre estratos o se reparte.

**Diseño.** Tomar tres puntos de E2 (brecha −0,5, +0,5, y el primero después
del vuelco) contra la base (brecha 0). Calcular `|ΔQ[h,i]|·S_i` por celda,
ubicar las fronteras (cruces de `Q_h = Q_g`; hay código en
`impacto-hev/impacto.py` que las calcula), y reportar el % del movimiento
total que cae en las 20 celdas alrededor de cada frontera, y cuánto se corrió
cada frontera en metros.

**Salida.** `salida/e4-donde.json`; figura tipo `fig2-donde.png` de impacto-hev.

### E5 — El nivel de ρ contra el gradiente de precios

**Objetivo.** Convertir C2 y C6 en una calibración del nivel. Dado α (y λ),
¿qué ρ_0 reproduce un gradiente objetivo?

**Diseño.** Sobre R1, para el gradiente medido como
`g = (p_1km − p_10km)/p_1km` (adimensional; robusto al nivel de `p`, que no
está fijado — ver `e_max_hev` docstring y D-31 «precios no comparables entre
ramas»), barrer ρ_0 fino en `[0, 0,03]` y tabular `g(ρ_0)`. Invertir: dado un
`g*` **[ancla C6]**, reportar ρ_0*. Mientras no haya `g*`, entregar la curva
completa y marcar en ella el valor de `g` de la calibración vigente.

**Salida.** `salida/e5-precios.json`, figura `g` vs ρ_0.

**Nota.** Verificar antes que `g` es invariante a la constante de `p` (lo es
por construcción si es un cociente de diferencias; si se usa una diferencia
absoluta, no lo es). Ver AU-11 para cómo medir `grad_p` sin caer en la celda
del CBD.

### E6 — Arrastre sobre el transporte

**Objetivo.** Cuánto mueve el reparto modal de la corrida acoplada por
defecto cada punto relevante de E1/E2. Es la línea base pineada en
`tests/test_linea_base.py` (`ESPERADO["equilibrio"]`).

**Diseño.** Usar el harness de §11.2 (ya probado). Puntos: base R0; R1 con
brecha 0 y ρ_0 ∈ {0,0025, 0,01}; R1 con brecha +0,5 y +1,0; y el primer punto
tras el vuelco. Reportar `pct` por modo, `Δ` vs pineado, iteraciones del MSA,
tiempo. La rama `original` debe quedar **idéntica** siempre (no usa suelo);
si se mueve, hay un bug de acoplamiento.

**Salida.** `salida/e6-transporte.json`.

**Contexto medido en sesión** (para chequeo): R1 con brecha 0 y ρ_0 = 0,0025
dio `16,83 · 34,16 · 22,38 · 7,18 · 19,45` (auto·metro·bici·caminata·tele)
en 8 iteraciones y 4,6 s, contra el pineado `16,95 · 32,79 · 22,84 · 7,98 ·
19,44` en 7 y 0,9 s. Si el ejecutor no reproduce esto a ±0,05 pp, algo cambió.

### E7 — Robustez

**Objetivo.** Que las conclusiones de E1–E3 no dependan de detalles.

**Diseño.** Repetir el subconjunto mínimo de E2 (brecha ∈ {0, 0,5, 1,0, 1,5},
ρ_0 = 0,0025) variando **de a una**:

- `β ∈ {0,5, 1, 2}` (nitidez del logit).
- `oferta_sigma_frac ∈ {0,3, 0,5, 0,8}` (compacidad).
- shares `H ∈ {10/40/50, 20/50/30, 33/33/33}`.
- `L ∈ {101, 201, 401}` (invariancia de grilla, D-26).
- `forma ∈ {normal, bimodal}` — bimodal es donde ρ es independiente (AU-12).

**Salida.** `salida/e7-robustez.json`. Reportar sólo qué cambia el **vuelco**
(la brecha crítica) y qué cambia el **orden** en cada variación.

### E8 — Costo

**Objetivo.** Documentar el costo de cómputo de cada configuración candidata,
porque condiciona el default (C7).

**Diseño.** Para cada punto de E6: tiempo de `LandUseCity.build` aislado
(mín de 5 repeticiones), iteraciones del punto fijo, tiempo de la corrida
acoplada. Correlacionar iteraciones con la dispersión de λ y de ρ.

**Salida.** `salida/e8-costo.json`.

---

## 6. Métricas — definiciones exactas

Reutilizar `resolver()` de `scripts/auditoria_suelo.py`, que ya calcula
`d_alto/d_medio/d_bajo`, `disp_a`, `theil`, `grad_p`, `dens_pk`, `iters`.
Agregar:

- **`mezcla`** `= mean_i (1 − max_h Q[h,i])` sobre celdas con oferta.
  0 = anillos puros; 0,667 = mezcla total con tres estratos.
- **`movidos`** `= Σ_i |Q_A[h,i] − Q_B[h,i]| · S_i / 2` por estrato, entre dos
  configuraciones A y B. Es la cantidad de hogares reubicados (misma
  definición que impacto-hev).
- **`g`** gradiente de precios adimensional
  `= (p(1 km) − p(10 km)) / p(1 km)`, con `p` interpolado linealmente entre
  celdas con oferta. **No** usar la celda del CBD (S = 0).
- **`κ_h`** `= (α_h − b·ρ_h)/λ_h`, con el `b` de E0 para esa geometría y
  población.
- **`fronteras`**: cruces de `Q_h(i) = Q_g(i)` entre estratos adyacentes en el
  orden espacial, interpolados; en km desde el CBD. Código base en
  `impacto-hev/impacto.py`.

Todo en unidades físicas: km, minutos, hogares/km, $/mes.

---

## 7. Entregables

    sandbox/impacto-rho/
    ├── PLAN.md          ← este archivo
    ├── pyproject.toml   ← copiar el de impacto-hev
    ├── impacto.py       ← E0–E8; escribe salida/*.json; sin matplotlib
    ├── figuras.py       ← lee los JSON, escribe salida/*.png
    ├── informe.html     ← presenta; toda cifra viene de los JSON
    └── salida/          ← versionado, como en impacto-hev

**Informe.** Mismo estilo que `impacto-hev/informe.html` (CSS, `.aviso`,
`.envoltorio-tabla`, ecuaciones con `data-tex` → MathML vía
`node tools/renderiza_ecuaciones.js`). Secciones sugeridas:

1. La pregunta y la respuesta corta.
2. Qué puede hacer ρ — el marco de §3, con las predicciones.
3. El nivel (E1).
4. La brecha y el vuelco (E2, E4).
5. Cuánto es α disfrazado (E3).
6. El precio como calibrador del nivel (E5).
7. Lo que arrastra al transporte y lo que cuesta (E6, E8).
8. Robustez (E7).
9. **La región admisible** — el resultado: en el plano `(e_s − e_t, ρ_0)`,
   dibujar la región que cumple C1–C3 y marcar dónde faltan las anclas.
10. Qué queda pendiente y qué anclas empíricas faltan.

**Además**, fuera del sandbox:

- Agregar **AU-13** a `docs/AUDITORIA_USO_SUELO.md` (nivel de α no
  identificado; ruta de Martínez p. 243 para anclar β) y la sección 10 al
  script. Fila en la tabla resumen.
- Agregar a **D-31** la cita de Martínez p. 242 sobre la ambigüedad
  `β` vs `β·λ_h` («The ambiguity prevails unless β or λ_h is estimated
  independently»).
- Matizar **AU-12** con Martínez p. 242: la identificación de densidades viene
  de la variabilidad espacial; es propiedad de nuestra geometría.
- Fila en `docs/arquitectura.html` apuntando a `sandbox/impacto-rho/informe.html`
  (ver cómo está la de impacto-hev).

---

## 8. Criterio de cierre — cómo se ve la respuesta

El plan está cumplido cuando el informe puede afirmar, con cifras del JSON:

1. «ρ uniforme no reasigna con λ uniforme; con λ ∝ 1/y reasigna X hogares
   por cada 0,001 de ρ_0» (E1).
2. «El estrato alto se va a la periferia cuando `e_s − e_t > Y` con
   ρ_0 = 0,0025, y ese umbral baja a Y' con ρ_0 = 0,01; la fórmula de `y*`
   lo predice con error Z» (E2).
3. «En la ciudad por defecto, α reproduce el W % del efecto de ρ; en bimodal,
   sólo el W' %» (E3).
4. «El nivel ρ_0 que da un gradiente de precios `g` está en la curva de E5;
   con la calibración vigente `g = …`» (E5).
5. «La región admisible por C1–C3 es: brecha en [a, b], ρ_0 en [c, d]. Las
   anclas C4–C6 la acotarían más y faltan» (§9).
6. Un veredicto sobre C7 para cada candidato a default.

Y cuando todas las predicciones P1–P7 estén marcadas confirmada/refutada con
el número que lo decide.

---

## 9. Anclas empíricas que faltan — pedir a Leandro

| Ancla | Para qué | Qué se necesita |
|---|---|---|
| Elasticidad ingreso de la demanda de espacio/suelo (`e_s`) | fijar la brecha en vez de barrerla | valor y fuente (economía urbana; no está en Jara-Díaz ni en Martínez) |
| Índice de segregación de Santiago (Theil o Duncan, escala comparable a celdas de 100 m en un corredor) | C5 | valor y fuente |
| Gradiente de renta/precio de suelo en Santiago (o razón centro/periferia) | C6, calibrar ρ_0 por E5 | valor y fuente |
| Rango de mezcla plausible a escala de manzana/celda | C4 | criterio de Leandro |
| Confirmación de que «rico cerca del centro de empleo» es el patrón a reproducir (el cono de alta renta está a ~10 km del centro histórico pero cerca del empleo actual) | C1 | criterio de Leandro |

Mientras falten, el informe reporta las métricas y deja los umbrales en
blanco. **No rellenar.**

---

## 10. Instrucciones operativas para el ejecutor

Gotchas de este repo y de este entorno (Windows), todos sufridos en la sesión
que escribió este plan:

- **Python**: `uv` únicamente. Desde `packages/titirilquen_core`:
  `uv run python …`, `uv run --extra dev pytest -q`. En el sandbox, su propio
  `pyproject.toml` (copiar el de impacto-hev).
- **Encoding**: al redirigir salida a archivo, Python usa cp1252 y revienta
  con `Σ`, `ρ`, etc. Anteponer siempre `PYTHONIOENCODING=utf-8`.
- **Heredocs en Bash colapsan `\n` y `\\`** dentro de scripts Python. Para
  cualquier archivo con backslashes (f-strings con `\n`, LaTeX en `data-tex`),
  usar la herramienta Write/Edit, no `cat <<'EOF'`.
- **`node` no está en el PATH del Bash tool**; `npm run …` y `npx prettier`
  van por PowerShell.
- **Tras tocar el core**: `npm run sync:core --workspace @titirilquen/web` y
  luego `npx prettier --write "apps/web/src/lib/gen/*.gen.ts"
  "apps/web/e2e/fixtures/*.json"` (el generador no puede correr prettier
  solo). Verificar con `git diff --stat` que sólo cambia lo esperado.
- **`verifica_mapa.py`** (dentro de pytest) falla si un docstring del core
  desplaza un símbolo. Arreglar el número en `docs/arquitectura.html`; el
  mensaje dice dónde quedó.
- **`git status` muestra ~60 `.tsx` modificados**: fantasmas CRLF. `git diff`
  sobre ellos está vacío. **No** hacer `git add -A` en la raíz; agregar
  archivos por nombre. `npm run format:check` falla por lo mismo en 17
  archivos commiteados; no es de este trabajo.
- **Grep de encabezados HTML**: `<h3>7\.` no captura `<h3 id="s76">7.6 …`.
  Listar los encabezados por DOM (navegador) o con regex `<h3[^>]*>` antes de
  numerar secciones nuevas. Ya pasó una colisión.
- **Mensajes de commit en ASCII** (sin acentes), en español, con el porqué.
  Terminar con `Co-Authored-By: Claude <noreply@anthropic.com>` y el nombre
  del modelo que corresponda.
- **Verificación**: ninguna cifra en el informe sin su JSON. Abrir el HTML en
  el navegador y comprobar por DOM que tablas y secciones renderizan.
  Screenshot puede fallar; `read_page`/`javascript_tool` no.
- **Commits**: por bloque coherente, no uno gigante. Sugerido: (1) el sandbox
  con E0–E3, (2) E4–E8, (3) informe, (4) AU-13 + D-31 + AU-12 + arquitectura.
  No pushear sin que Leandro lo pida.

---

## 11. Código de arranque — probado en sesión

### 11.1 Parametrización por elasticidades

```python
import numpy as np
from titirilquen_core.land_use.ciudad import LandUseCity, _default_T
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig

YS = (3.5e6, 1.5e6, 0.5e6)
Y_MED = 1.5e6


def estratos(e_t: float, e_s: float, alpha: float = 6.0, rho0: float = 0.0025):
    """lambda_h ~ y^-e_t ; rho_h/lambda_h ~ y^e_s ; alpha uniforme."""
    return tuple(
        LandUseStratumConfig(
            y=y,
            alpha=alpha,
            rho=rho0 * (y / Y_MED) ** (e_s - e_t),
            **{"lambda": (y / Y_MED) ** (-e_t)},
        )
        for y in YS
    )


def ciudad(estr, forma="normal", L=201, CBD=100, largo_km=20.0, H=(7200, 18000, 10800)):
    cfg = LandUseConfig(H_por_estrato=H, forma=forma, oferta_sigma_frac=0.5)
    if estr is not None:
        cfg.estratos = estr
    return LandUseCity.build(
        L=L, CBD=CBD, cfg=cfg, ancho_celda_km=largo_km / L, rng=np.random.default_rng(42)
    )
```

Regímenes: R0 = `estr=None` con los defaults; R1 = `estratos(1.0, 1.0)`
(λ = 0,43·1·3, ρ uniforme). Brecha: `estratos(1.0, 1.0 + brecha)`.

### 11.2 Tasa de cambio b y equivalente en α (E0, E3)

```python
def tasa_b(ciudad_obj, L=201, CBD=100, largo_km=20.0):
    T = _default_T(L, CBD, 3, largo_km / L)[0]
    dens = np.asarray(ciudad_obj.densidad_por_celda(), dtype=float)
    m = np.arange(L) != CBD
    b = -np.polyfit(T[m], dens[m], 1)[0]
    r2 = np.corrcoef(T[m], dens[m])[0, 1] ** 2
    return b, r2
```

Medido en sesión, forma normal, L = 201, 20 km:

| ΣH | b | R² | b/ΣH |
|---|---|---|---|
| 99.900 (defaults de `config.py`) | 423,4 | 0,9911 | 0,00424 |
| 36.000 (ciudad de la auditoría) | 152,6 | 0,9910 | 0,00424 |

`b` escala **exactamente** con la población (`dens ∝ N`). **Recalcular siempre**
para la configuración que se use; la tasa de cambio ρ↔α no es una constante
del modelo, es de la ciudad.

### 11.3 Línea base acoplada (E6)

```python
import sys, time
sys.path.insert(0, "tests")                 # desde packages/titirilquen_core
import test_linea_base as tlb
from titirilquen_core.equilibrium.msa import ConvergenceTrace


def linea_base(estr, localizacion="equilibrio"):
    kw = dict(H_por_estrato=(7200, 18000, 10800), forma="normal",
              oferta_sigma_frac=0.5, max_iter=2000)
    if estr is not None:
        kw["estratos"] = estr
    trace = ConvergenceTrace()
    t0 = time.perf_counter()
    for _ in tlb.iter_msa_desde_suelo(tlb._config_web(), LandUseConfig(**kw),
                                      trace, localizacion=localizacion):
        pass
    dt = time.perf_counter() - t0
    split = trace.iteraciones[-1].modal_split
    tot = sum(split.values())
    return {m: 100.0 * v / tot for m, v in split.items()}, len(trace.iteraciones), dt
```

`tlb.ESPERADO["equilibrio"]` es el pineado. Con `estr=None` debe reproducirlo
exacto.

### 11.4 Invariancia de nivel (E0, P7 / AU-13)

```python
def nivel_invariante(k):
    cfg = LandUseConfig(H_por_estrato=(7200, 18000, 10800), forma="normal",
                        oferta_sigma_frac=0.5, beta=1.0 / k)
    cfg.estratos = tuple(
        LandUseStratumConfig(y=y, alpha=a * k, rho=0.0025 * k)
        for y, a in zip(YS, (6.5, 6.0, 5.5))
    )
    return np.asarray(LandUseCity.build(L=201, CBD=100, cfg=cfg, ancho_celda_km=20 / 201,
                                        rng=np.random.default_rng(42)).result.Q)
```

Esperado: `max|Q(k) − Q(1)| ≈ 2·10⁻⁹` para k ∈ {10, 377, 1000}.

---

## 12. Resumen para quien tenga prisa

- ρ entra en la asignación **sólo** vía `κ_h = (α_h − b·ρ_h)/λ_h`. En la
  ciudad por defecto es α disfrazado al 99 %; su nivel se ve en los precios,
  no en el mapa.
- Con λ ∝ 1/y (Jara-Díaz), ρ uniforme **sí** reasigna, y ρ heterogéneo
  parametrizado por `e_s − e_t` decide si el rico queda en el centro (patrón
  chileno) o se va a la periferia (vuelco de Muth/Wheaton) — el umbral depende
  de ρ_0.
- El plan mapea esa región, mide cuánto de ρ es propio, y deja marcadas las
  tres anclas empíricas que faltan para cerrar el número. No las inventa.
