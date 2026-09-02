# Auditoría del módulo de USO DE SUELO — iteración 4 (agosto 2026)

Barrido de **todos** los parámetros de `LandUseConfig` con medición del efecto
sobre los resultados. Hallazgos con ID `AU-xx` (auditoría uso de suelo).

Reproducir: `cd packages/titirilquen_core && uv run python scripts/auditoria_suelo.py`
Base: 201 celdas · 20 km · ΣH = 36.000 · shares 10/40/50 · α = 6,5/6,0/5,5 · β = 1.

Todas las cifras de este documento salen de ese script. Las columnas son
`d_h` (distancia media al CBD del estrato h, km), `disp_a` (desviación estándar
de la posición del estrato alto, km — distingue «se mudó» de «se desparramó»),
`theil` (segregación entre celdas), `grad_p` (gradiente de precio centro-periferia,
positivo = Alonso), `dens_pk` (densidad máxima) e `iters`.

| ID | Hallazgo | Veredicto |
|---|---|---|
| AU-01 | El efecto Alonso funciona en dirección y magnitud correctas | ✅ conforme |
| AU-02 | `y` (ingreso) es inerte en la asignación — correcto por teoría | ✅ conforme |
| AU-03 | La asignación es invariante a la escala de población | ✅ conforme |
| AU-04 | `β` opera como escala de ruido del logit, monótona | ✅ conforme |
| AU-05 | `ρ` uniforme no reasigna **sólo si `λ` es uniforme**; con `λ` heterogéneo sí reasigna | 🐛 corregido 2026-09-02 |
| AU-06 | `λ` ≡ re-escalar α y ρ: no es un parámetro, es un artefacto | ✅ esperado, limitación declarada |
| AU-07 | El solver que decía corregirlo no lo hacía — **eliminado** | 🐛 corregido |
| AU-08 | No hay **techo de densidad**: la densidad puede crecer sin límite | ⚠️ decisión de modelo a discutir |
| AU-09 | Convergencia lenta en configuraciones asimétricas (hasta 2.640 iter) | ℹ️ observación |
| AU-10 | Sensibilidad muy alta a diferencias pequeñas de α | ℹ️ para la lectura pedagógica |
| AU-11 | **El gradiente de renta estaba INVERTIDO** y `grad_p` lo tapaba | 🐛 corregido 2026-08-24 |
| AU-12 | `α` y `ρ` no son canales independientes: colineales en la geometría base | ⚠️ no identificados |
| AU-13 | El **nivel** de `α` no está identificado: sólo el producto `β·α` | ⚠️ normalización libre |

> **AVISO (2026-08-24).** Todo lo que este documento dice sobre `grad_p` en las
> iteraciones 1 a 4 está **medido en la celda equivocada** y varias conclusiones
> tienen el signo cambiado. `grad_p` se calculaba en `p[CBD]`, la única celda sin
> oferta (`S=0` ⇒ `T=0` y `dens=0`, amenidad máxima por construcción y nadie
> puede vivir ahí). Entre celdas habitadas el gradiente de la base era **−0,48**,
> no +0,50: el suelo más caro estaba en la **periferia**. Ver AU-11.
>
> Corregido: `grad_p` se mide sobre celdas con oferta y ρ se recalibró de 0,1 a
> **0,0025**. Las tablas de AU-01 y AU-05 de abajo conservan los números de
> localización (que no cambiaron) pero sus columnas `grad_p` son de la medición
> vieja. Reproducir con `uv run python scripts/auditoria_suelo.py`.

## 1. ¿Responde el modelo en la dirección correcta?

### AU-01 — El efecto Alonso funciona ✅

Teoría (Alonso-Muth-Mills): quien más valora el acceso —α más alto— debe pujar
más por el centro y localizarse **más cerca** del CBD.

| α (alto/medio/bajo) | d_alto | d_medio | d_bajo | Theil |
|---|---|---|---|---|
| 6,5 / 6,0 / 5,5 (base) | 0,99 | 2,13 | 5,36 | 0,357 |
| 12 / 6 / 3 | **0,37** | 1,90 | 5,68 | 0,822 |
| 3 / 6 / **12** | **8,45** | 4,99 | **1,58** | 0,875 |
| 6 / 6 / 6 | 3,63 | 3,63 | 3,63 | **0,000** |
| 20 / 6 / 1 | 0,35 | 1,89 | 5,68 | 0,879 |

Los cuatro comportamientos que la teoría exige se cumplen: gradiente correcto
en la base, refuerzo al separar los α, **inversión completa** al invertirlos
(el estrato bajo pasa a 1,58 km y el alto a 8,45), y **mezcla perfecta**
(Theil = 0, todos a 3,63 km) cuando los α son iguales. El módulo es fiel al
modelo de puja.

### AU-04 — `β` es la escala de ruido, no una preferencia ✅

| β | 0,1 | 0,5 | 1 (base) | 3 | 10 |
|---|---|---|---|---|---|
| Theil | 0,013 | 0,176 | 0,357 | 0,651 | 0,843 |
| d_alto | 2,85 | 1,43 | 0,99 | 0,55 | 0,37 |

Monótona y con los dos límites correctos: β → 0 da asignación casi aleatoria
(Theil ≈ 0), β → ∞ tiende a la asignación determinista del bid-rent puro. Es
exactamente la interpretación de β como precisión del logit.

### AU-02 / AU-03 — Invariancias que deben cumplirse ✅

- **Ingreso `y`**: 3,5M/1,5M/0,5M, todos 1M, o el alto a 100M → asignación
  idéntica (0,99 / 2,13 / 5,36). Correcto: `y` se absorbe en la utilidad de
  equilibrio ū y no puede mover la localización (D-08 §C8). Sí importa para la
  métrica de carga costo/ingreso del acoplado.
- **Escala de población**: ΣH de 9.000, 36.000 y 144.000 → misma asignación y
  mismo Theil (0,3569 / 0,3570 / 0,3570). La densidad escala proporcionalmente
  (764 / 3.045 / 12.181 hab/km). Correcto: el modelo es homogéneo de grado 0 en
  la escala.
- **Vestigiales**: `densidad_max`/`densidad_min` en 800/200 o en 9999/1 →
  idéntico. Confirmado muertos, como declara el propio schema.

### AU-05 — `ρ` uniforme: no reasigna **si `λ` es uniforme** 🐛 (corregido 2026-09-02)

| ρ (todos) | d_alto | d_medio | d_bajo | Theil | **grad_p** |
|---|---|---|---|---|---|
| 0 | 0,99 | 2,13 | 5,36 | 0,357 | **+1,00** |
| 0,1 (base) | 0,99 | 2,13 | 5,36 | 0,357 | **+0,50** |
| 0,5 | 0,99 | 2,13 | 5,36 | 0,357 | **+0,21** |

Con los `λ` uniformes, una `ρ` **común** a los tres estratos no reasigna a nadie
—es un término común que se absorbe en ū, igual que `y`— pero **sí achata el gradiente de precios**:
las celdas centrales son las densas, así que la penalización golpea justo donde
el suelo vale más. De +1,00 a +0,21 hay un factor 5.

Es teóricamente correcto y pedagógicamente interesante, pero **hoy no está
dicho en ninguna parte**. Ojo con llamarlo «congestión residencial»: `dens` es
la oferta, exógena, y ningún hogar puede moverla — no hay externalidad de
localización en el sentido de Martínez (D-32). La tensión que se ve es entre dos
funciones fijas de la parcela, y en la geometría base son casi la misma función
(AU-12). Dicho eso, un estudiante que mueve ρ y sólo mira la distribución
espacial concluye que «no hace nada». Recomendación: mencionarlo en el tutorial de uso de suelo.

Con `ρ` **heterogénea** sí hay reasignación (alto 0,1 y resto 0 → el estrato
alto se va a 8,48 km): también correcto.

> **Corregido 2026-09-02 — el hallazgo valía sólo con `λ` uniforme.** Lo que
> entra en la puja no es `ρ_h` sino **`ρ_h/λ_h`**: el score es `y + f/λ` con
> `f = −α·T − ρ·dens`. Con los `λ` iguales una `ρ` común sigue siendo un término
> común y se absorbe en ū —la tabla de arriba es correcta—, pero **en cuanto los
> `λ` difieren, una `ρ` uniforme deja de ser uniforme en la puja y sí reasigna**.
> Con `λ = (0,5 · 1 · 2)`, decreciente en el ingreso como manda Martínez (p. 77):
>
> | ρ (todos) | d_alto | d_medio | d_bajo | Theil | grad_p |
> |---|---|---|---|---|---|
> | 0 | 0,38 | 1,89 | 5,68 | 0,828 | +0,97 |
> | 0,0025 (base) | 0,38 | 1,89 | 5,68 | 0,823 | +0,81 |
> | 0,01 | 0,39 | 1,89 | 5,68 | 0,806 | +0,51 |
> | **0,05** | **5,67** | 4,57 | **2,47** | **0,514** | −0,04 |
>
> Con ρ = 0,05 la ciudad **se invierte**: el estrato alto sale a 5,67 km y el
> bajo entra a 2,47 km, y la segregación cae casi a la mitad (Theil 0,83 →
> 0,51). No es un efecto de segundo orden. Reproducir con la sección **2b** de
> `scripts/auditoria_suelo.py`.

## 2. ¿Tiene coherencia con la teoría?

### AU-06 — `λ` es un artefacto: no es un parámetro económico independiente ✅

> **Actualizado 2026-08-24.** La identidad sigue valiendo exacta, pero **las
> tablas y la interpretación de abajo describen el régimen de ρ = 0,1** y ya no
> aplican. Con ρ = 0,0025 el canal dominante pasó de ρ a α, y con eso el efecto
> de λ **cambió de dirección**: ahora bajar λ acerca al estrato alto al centro
> (α_eff = α/λ sube, valora más el acceso), que es coherente, en vez de
> expulsarlo. El salto abrupto también se corrió: hoy está entre λ=1,0 y λ=1,5.
>
> Además, el cotejo con Martínez (2018) precisa el diagnóstico: la ec. (4.3) del
> libro deja el ruido de la puja con forma `b_h = λ_h·μ_h`, y el código fija
> `b_h = β`, o sea supone `μ_h = β/λ_h`. Bajo ese supuesto —que es el de la ec.
> (4.25) del libro— **λ no tiene canal estocástico alguno**: entra sólo en la
> parte determinística. Por eso mover λ no produce dispersión sino un
> desplazamiento limpio y reproducible. Ver §7.1 de `docs/informe-uso-suelo.html`.

`λ_h` es la utilidad marginal del ingreso. Mover `λ` cambia la asignación, y eso
**es lo esperado dado el modelo implementado**. Pero la razón es más fuerte —y
más incómoda— que «escala el ruido».

**El hallazgo central: `λ_h` es una identidad algebraica, no un parámetro.** La
puja es `y_h + f_h(i)/λ_h` con `f = −α·T − ρ·dens`, así que dividir por `λ_h`
es **exactamente lo mismo** que re-escalar las preferencias de ese estrato:

```
y_h + f_h(i)/λ_h  ≡  y_h + f(i;  α_h/λ_h,  ρ_h/λ_h)
```

Verificado (§4b del script): con λ ∈ {0,4 · 0,5 · 1,5 · 3,0} la matriz `Q` de
ambas vías coincide con `max|ΔQ| = 0,000e+00` — **cero, no «aproximadamente
cero»**. Fijado como test de regresión
(`test_lambda_equivale_exactamente_a_reescalar_alpha_y_rho`).

O sea, `λ` mueve tres cosas a la vez y no permite separarlas: `α_eff = α/λ`
(cuánto pesa el acceso), `ρ_eff = ρ/λ` (cuánto molesta la densidad) y la escala
del ruido `1/(β·λ)`. No agrega información al modelo: es una
**re-parametrización redundante** de α y ρ.

**Consecuencia medida — bajar λ expulsa al estrato alto del centro:**

| λ del estrato alto | 0,4 | 0,5 | 0,8 | 0,9 | 0,95 | 1,0 (base) | 1,5 | 3,0 |
|---|---|---|---|---|---|---|---|---|
| d_alto (km al CBD) | 8,48 | 8,48 | 8,26 | 4,75 | **1,33** | 0,99 | 0,89 | 0,94 |
| dispersión (km) | 8,51 | 8,51 | — | — | — | 1,27 | 1,02 | 1,02 |
| Theil | 0,537 | 0,532 | — | — | — | 0,357 | 0,386 | 0,405 |
| iteraciones | 801 | 511 | 70 | 21 | 31 | 36 | 52 | 68 |

Dos cosas que un parámetro de comportamiento no hace:

1. **Salto casi discontinuo.** Entre λ = 0,8 y λ = 0,95 —un cambio de 19%— el
   estrato alto **cruza la ciudad entera**, de 8,26 km a 1,33 km. Fuera de esa
   banda estrecha, λ casi no hace nada (0,4 y 0,5 dan el mismo resultado; 1,5 y
   3,0 también).
2. **Dirección absurda.** Bajar λ manda a los **ricos a la periferia**. El
   mecanismo es transparente con la identidad de arriba: `ρ_eff = ρ/λ` crece
   (0,1 → 0,25 con λ = 0,4) y la penalización de densidad castiga justo las
   celdas centrales, que son las densas. Gana ρ sobre α y el estrato huye. De
   hecho λ = 0,4 reproduce **exactamente** la fila «alto ρ = 0,5, resto 0» de
   AU-05 (8,48 / 1,70 / 4,21) — es el mismo corner solution.

El contraste que cierra el argumento: el ingreso `y` —que sí es un parámetro
económico del estrato— **no reasigna a nadie** (AU-02), porque entra como
constante y se absorbe en ū. Si λ moviera gente por una razón económica, `y`
también debería.

**Qué debe verse en clase.** Que mover λ cambia el mapa es una **limitación
declarada del modelo**, no un resultado. La lectura honesta es: «este parámetro
no está identificado; lo que ves es el ruido y el re-escalamiento de α y ρ, no
una respuesta al ingreso».

> **Corregido el 2026-08-24:** la subasta heteroscedástica (HEV, Train §4.5 / Bhat 1995) está implementada en `land_use/hev.py` y `solve_subasta` la usa automáticamente cuando los λ difieren. Con eso λ queda identificado. Sigue entrando también por `f_h/λ_h`, así que no es un parámetro limpio: para eso haría falta un modelo de elección y no de subasta. El hint de la UI y
el tutorial §6 lo dicen así.

> Corrección de esta iteración: el tutorial afirmaba «sube λ ⇒ el estrato se
> dispersa; bájalo ⇒ se concentra». Es **al revés** incluso según la teoría del
> ruido (~1/βλ), y la medición lo desmiente: λ = 0,4 da dispersión 8,51 y
> λ = 3,0 da 1,02. Corregido en `07-experimenting.mdx` (es/en) y en los hints
> `lambda_artifact_logit` y `bidrent_hint`.

### AU-07 — el solver que decía corregirlo no lo hacía 🐛 ELIMINADO

El core traía un segundo solver presentado como «el método consistente que
corrige el λ heterogéneo», seleccionable por el campo `solver`. **No corregía
nada.** Su implementación era:

```python
score = (lambda_h * y)[:, None] + _f(T, S_arr, alpha, rho, ancho_celda_km)
return _solve_fixed_point(score, H_arr, S_arr, beta, tol, max_iter)
```

`λ_h·y_h` es una **constante por estrato**, y el punto fijo absorbe cualquier
constante por estrato en ū_h. Además `_solve_fixed_point` recibe un β **escalar**:
la escala por estrato `β_h = β·λ_h` que su docstring afirmaba aplicar no estaba
implementada en ninguna parte. Verificado empíricamente: con λ de `[1,1,1]` a
`[100, 0.01, 1]` —rango de 10.000×— la matriz `Q` es **idéntica dígito a
dígito**.

O sea: no corregía el artefacto, lo **borraba**, haciendo λ completamente
inerte. Sus dos tests pasaban vacuamente por lo mismo (una invariancia trivial).

Eliminado: el solver, el campo `solver` del schema, el selector de i18n y los
tests vacuos. Queda un único solver (`logit`) con su limitación documentada. Los
escenarios guardados que traen el campo se migran en `serialization.ts`.

**Cola del mismo problema, en el propio script de auditoría.** Su §10 comparaba
los dos solvers vía `base_cfg(solver=...)`. Tras la eliminación el
barrido **no falló**: `model_copy(update=...)` de Pydantic **no valida**, así
que la clave se colaba como atributo suelto y se ignoraba — las filas decían
usar el método removido y corrían el logit. Un barrido de sensibilidad que reporta un
efecto inexistente es peor que uno que se cae. Se eliminó la §10 y `base_cfg`
ahora valida las claves contra `LandUseConfig.model_fields` antes de copiar.

### AU-08 — No hay techo de densidad ⚠️

**¿El modelo tiene restricción de capacidad?** Sí, y del tipo correcto: `S_i`
es la capacidad de cada parcela y el equilibrio cumple `Σ_i S_i·Q_hi = H_h`
exactamente (conservación S-4/D-25). Es una restricción de **vaciado de
mercado**: los precios ajustan hasta que la demanda por cada parcela iguala su
oferta. Eso es Alonso puro y está bien.

**Lo que no hay es un techo de densidad.** La oferta `S` se genera de la forma
elegida y puede concentrarse sin límite:

| σ | 0,15 | 0,3 | 0,5 | 0,8 | 1,2 |
|---|---|---|---|---|---|
| densidad pico (hab/km) | **9.859** | 4.874 | 3.045 | 2.291 | 2.020 |

Con σ = 0,15 y ΣH = 144.000 la densidad pico llega a ~40.000 hab/km. Ninguna
normativa urbana permite eso; en la realidad la altura máxima y la
constructibilidad acotan `S`. Los campos `densidad_max`/`densidad_min` del
schema, hoy vestigiales, parecen ser exactamente el resto de esa idea.

**¿Debería tenerlo?** Es una decisión de alcance, no un bug: el modelo
Alonso-Muth-Mills toma `S` como exógena, así que un techo sería un módulo de
zonificación aparte. Pero para el fin académico —discutir densificación vs.
expansión— tener un tope normativo activable sería un buen ejercicio.
Recomendación: llevarlo a los autores como extensión, no cambiarlo ahora.

## 3. ¿Está calibrado para observar el efecto esperado?

### AU-10 — Sí, pero la respuesta a α es muy sensible ℹ️

La calibración base (α = 6,5 / 6,0 / 5,5) produce un gradiente claro:
0,99 / 2,13 / 5,36 km. Se lee bien.

Ahora, esos tres α difieren en apenas **1,0 utiles/min (≈15%)** y generan una
razón de distancias de **5,4×** entre el estrato alto y el bajo. La mecánica de
puja amplifica mucho las diferencias pequeñas. Dos consecuencias para el uso en
clase:

1. Es fácil producir resultados extremos moviendo α poco — bueno para mostrar
   el mecanismo, riesgoso para interpretar magnitudes como si fueran realistas.
2. La calibración base no es neutra: ya trae segregación (Theil 0,357). Si se
   quiere partir de una ciudad mezclada para «construir» la segregación en
   clase, hay que igualar los α (Theil 0).

### AU-09 — Convergencia lenta en configuraciones asimétricas ℹ️

Iteraciones del punto fijo: base 36, pero **2.640** con ρ heterogénea y 801 con
λ = 0,4. El tope es `max_iter = 10.000`, así que no truncan, pero el tiempo de
respuesta se nota en la UI. Ninguna configuración probada falló en converger.

El patrón es informativo: las configuraciones lentas son exactamente las que
caen en el corner solution de AU-05/AU-06 (el estrato alto expulsado a la
periferia). La lentitud es la firma de un equilibrio cerca de la bifurcación,
no un problema numérico.

## 4. Resumen ejecutivo

**El módulo es teóricamente sólido y responde correctamente en casi todo**: el
efecto Alonso funciona con la dirección, la magnitud y los casos límite
correctos (inversión y mezcla perfecta); las invariancias que la teoría exige
(ingreso, escala) se cumplen; β se comporta como escala de ruido; la
conservación de hogares es exacta.

Las dos observaciones de fondo:

1. **El artefacto de λ (AU-06)** — es la única incoherencia teórica viva, y es
   una limitación **declarada**. Esta iteración la precisa: `λ_h` no es un
   parámetro económico independiente sino, **con identidad exacta verificada**,
   re-escalar `(α_h, ρ_h)` por `1/λ_h`. **En la región económicamente válida**
   —λ decreciente en el ingreso, `λ_alto < λ_medio < λ_bajo`— su efecto es suave
   y acotado: con `λ = (1/r, 1, r)` el estrato alto va de 1,47 km en r = 1 a
   1,05 km en r = 4, saturando. La cifra «cruza la ciudad entre λ = 0,8 y 0,95»
   que decía esta línea era del régimen de ρ = 0,1, igual que la dirección: con
   ρ = 0,0025 el canal dominante es `α_ef = α/λ` y **bajar** λ acerca al estrato
   alto al centro (ver AU-11). La transición violenta —hasta 6,25 km— aparece
   sólo si se sube `λ_alto` por encima de los otros, que es una configuración al
   revés y no debe leerse como el comportamiento del modelo. Re-medido el
   2026-09-02.
   **Corregido el 2026-08-24** con HEV; ver la nota de AU-06. Lo que sí se
   eliminó antes (AU-07) fue un solver que decía corregirlo sin hacerlo.
2. **Sin techo de densidad (AU-08)** — la restricción de capacidad que sí existe
   (vaciado de mercado sobre `S`) es la correcta; falta la normativa. Extensión
   posible, no defecto.

Y una de forma: **`ρ` uniforme afecta precios y no localización (AU-05)** —
pero eso vale sólo en la línea base, donde `λ` es uniforme. Con `λ` heterogéneo
`ρ` reasigna, y fuerte.

---

## AU-11 — El gradiente de renta estaba invertido 🐛 (corregido 2026-08-24)

Con ρ = 0,1 el suelo **más caro estaba en la periferia**: en `f = −α·T − ρ·dens`
el término de densidad aplastaba al de accesibilidad, y como la densidad es
máxima en el centro, el centro era el peor lugar.

| a km del CBD | α·T | ρ·dens | manda |
|---|---|---|---|
| 0,1 | 1,3 | **845** | densidad |
| 5,0 | 65 | **185** | densidad |
| 9,95 (borde) | **129** | 41 | acceso |

**Por qué esta auditoría no lo vio.** `grad_p` se medía en `p[CBD]`, la única
celda sin oferta. Reportaba +0,50 mientras el gradiente entre celdas habitadas
era −0,48.

**De dónde venía.** En unidades de celda, la razón entre los dos términos es
`≈ α·(L/2)²·1,253/(ρ·N)`: va con el **cuadrado** del número de celdas. El
`Suelo.tex` original usa 1001 celdas con α=1 y ρ=0,5 → razón 6,0 y gradiente
**+0,72** (verificado corriendo el modelo con esa parametrización). Pasar a 201
celdas dividió la razón por 25. La migración a unidades físicas (D-26) eliminó
la dependencia de la grilla, pero se calibró sobre la grilla ya cambiada, así
que preservó el balance roto.

**Corregido:** ρ = 0,0025 (razón 6,1, gradiente **+0,92**), `grad_p` sobre celdas
con oferta, tres tests que fijan el signo a las tres escalas de población, y la
FIG. 04 excluye el CBD de su escala. ρ es común a los tres estratos, así que la
recalibración **no reasignó a nadie**: distancias medias y línea base de
transporte idénticas. (Con los `λ` uniformes de la línea base; ver AU-05.)

---

## AU-12 — `alpha` y `rho` no son dos canales independientes ⚠️ (2026-09-02)

`dens` es una función **fija** de la parcela: es la oferta, y el equilibrio no la
mueve (D-32). En las formas monocéntricas es además casi proporcional a `T`.
Medido sobre la ciudad de la auditoría:

| forma | corr(T, dens) | dens min | dens max | lectura |
|---|---|---|---|---|
| **normal** *(default)* | **−0,996** | 412 | 3.045 | colineal |
| uniforme | — *(plana)* | 1.809 | 1.809 | `ρ` inerte |
| exponencial | −0,969 | 573 | 4.141 | colineal |
| meseta | −0,922 | 0 | 3.889 | colineal |
| **bimodal** | **−0,098** | 402 | 2.955 | **canal independiente** |
| valle | +1,000 | 40 | 3.578 | colineal |

Con `dens ≈ a − b·T`, la atractividad colapsa:

    f = −α·T − ρ·dens ≈ −(α − ρ·b)·T + constante

y la constante se absorbe en ū. **De los dos parámetros, la localización
identifica sobre todo la combinación `α_h − ρ_h·b`.**

> **Corregido 2026-09-02, con medición.** Acá decía que mover `ρ` heterogéneo
> es «al 99,6 %» mover `α` en sentido contrario. **La correlación no es la
> redundancia**: 0,996 es cuánto de la *varianza* de `dens` explica `T`, no
> cuánto del *efecto* de ρ reproduce α. Medido en `sandbox/impacto-rho` (E3),
> construyendo el equivalente `α'_h = α_h − b·ρ_h` y comparando asignaciones:
>
> | forma | R² | % del efecto de ρ que α reproduce |
> |---|---|---|
> | normal | 0,991 | **70,5 %** |
> | exponencial | 0,939 | 59,3 % |
> | meseta | 0,851 | **−19,6 %** |
> | bimodal | 0,010 | −0,9 % |
> | valle | 1,000 | 99,3 % |
>
> O sea que en la ciudad por defecto **a ρ le queda ~30 % de efecto propio**, no
> 0,4 %. El residuo `dens − (a − b·T)` pesa poco en varianza y mucho en
> resultado, porque la subasta amplifica diferencias chicas (AU-10). Sólo en
> `valle`, donde la colinealidad es exacta (R² = 1,000), α reproduce a ρ casi
> perfecto. En `meseta` y `bimodal` el «equivalente» es peor que no corregir:
> ahí `b` no significa nada.

Eso explica AU-05 más a fondo: cuando una `ρ` heterogénea da vuelta la ciudad
entera no está agregando una fuerza nueva, está reescribiendo `α`.

Consecuencia para calibrar: **no se pueden estimar `α` y `ρ` por separado** a
partir de datos de localización en la geometría por defecto. La única forma que
rompe la colinealidad es **bimodal** (−0,098), donde la oferta tiene dos picos y
`dens` deja de ser monótona en la distancia. Con `uniforme`, `dens` es plana, `ρ`
entra como constante pura y no hace nada — ni siquiera sobre los precios.

Reproducir con la sección **6b** de `scripts/auditoria_suelo.py`.

> **No es un defecto de la clase de modelo, es de nuestra geometría.** Martínez
> (p. 242) dice que la identificación de estos parámetros viene justamente de la
> variabilidad espacial: «the choice model is particularly suitable to estimate
> parameters of variables that differentiate bids by location such as
> accessibility or **densities** because the denominator in Eq. (9.9) is defined
> for the space of locations; hence, **its variability helps identify** better
> estimates of these parameters». En una ciudad real, con muchas zonas y densidad
> no monótona, `α` y `ρ` se separan. En un corredor monocéntrico con `dens`
> monótona en la distancia, no.

---

## AU-13 — El nivel de `alpha` no está identificado ⚠️ (2026-09-02)

`Q ∝ exp(b·score)` con `b = β·λ` y `score = y + f/λ`, así que

    b·score = β·λ·y + β·f

El primer término es constante por estrato y lo absorbe ū. Queda **`β·f`**:
sólo el producto `β·α` (y `β·ρ`) es observable. Medido —escalar `(α, ρ)` por `k`
y `β` por `1/k`:

| k | α_alto | β | max\|ΔQ\| vs k = 1 |
|---|---|---|---|
| 10 | 65,0 | 1,00·10⁻¹ | 1,00·10⁻⁹ |
| 377 | 2.450,5 | 2,65·10⁻³ | 1,17·10⁻⁹ |
| 1.000 | 6.500,0 | 1,00·10⁻³ | 1,17·10⁻⁹ |

Idéntico a la tolerancia del solver en los tres casos.

**Consecuencia para calibrar.** Poner `α` al nivel que implicaría un valor del
tiempo en pesos no es una corrección: da exactamente la misma ciudad si se
compensa `β`. Lo que **sí** está identificado son las **razones** `α_h/α_g`
entre estratos —que son las que producen el gradiente de Alonso— y el producto
`β·α`, que fija cuán nítida sale la segregación.

**Hay una salida, y no está implementada.** Martínez (p. 243) ancla `β` con la
ley de escala de rentas contra población, `R = β·ln N`: «this equation provides
a **very powerful condition for the estimate of the β-parameter**, which is the
same parameter for rents at the micro and macro spatial scales». El modelo de
acá no tiene esa condición macro, así que el nivel queda libre.

Reproducir con la sección **10** de `scripts/auditoria_suelo.py`.
