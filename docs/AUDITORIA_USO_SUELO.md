# Auditoría del módulo de USO DE SUELO — iteración 4 (agosto 2026)

Barrido de **todos** los parámetros de `LandUseConfig` con medición del efecto
sobre los resultados. Hallazgos con ID `AU-xx` (auditoría uso de suelo).

Reproducir: `cd packages/titirilquen_core && uv run python scripts/auditoria_suelo.py`
Base: 201 celdas · 20 km · ΣH = 36.000 · shares 10/40/50 · α = 6,5/6,0/5,5 · β = 1.

| ID | Hallazgo | Veredicto |
|---|---|---|
| AU-01 | El efecto Alonso funciona en dirección y magnitud correctas | ✅ conforme |
| AU-02 | `y` (ingreso) es inerte en la asignación — correcto por teoría | ✅ conforme |
| AU-03 | La asignación es invariante a la escala de población | ✅ conforme |
| AU-04 | `β` opera como escala de ruido del logit, monótona | ✅ conforme |
| AU-05 | `ρ` uniforme no reasigna pero **sí aplana el gradiente de precios** | ✅ conforme, no documentado |
| AU-06 | `λ` mueve la localización con `logit` — artefacto D-08 **vivo** | ⚠️ incoherencia conocida |
| AU-07 | `utility_logit` neutraliza `λ` correctamente, pero **no se expone** | ⚠️ el arreglo existe y no se usa |
| AU-08 | No hay **techo de densidad**: la densidad puede crecer sin límite | ⚠️ decisión de modelo a discutir |
| AU-09 | Convergencia lenta en configuraciones asimétricas (hasta 2.640 iter) | ℹ️ observación |
| AU-10 | Sensibilidad muy alta a diferencias pequeñas de α | ℹ️ para la lectura pedagógica |

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

### AU-05 — `ρ` uniforme: no reasigna, pero aplana los precios ✅ (no documentado)

| ρ (todos) | d_alto | d_medio | d_bajo | Theil | **grad_p** |
|---|---|---|---|---|---|
| 0 | 0,99 | 2,13 | 5,36 | 0,357 | **+1,00** |
| 0,1 (base) | 0,99 | 2,13 | 5,36 | 0,357 | **+0,50** |
| 0,5 | 0,99 | 2,13 | 5,36 | 0,357 | **+0,21** |

Una `ρ` **común** a los tres estratos no reasigna a nadie —es un término común
que se absorbe en ū, igual que `y`— pero **sí achata el gradiente de precios**:
las celdas centrales son las densas, así que la penalización golpea justo donde
el suelo vale más. De +1,00 a +0,21 hay un factor 5.

Es teóricamente correcto y pedagógicamente interesante (congestión residencial
vs. renta de localización), pero **hoy no está dicho en ninguna parte**: un
estudiante que mueve ρ y solo mira la distribución espacial concluye que «no
hace nada». Recomendación: mencionarlo en el tutorial de uso de suelo.

Con `ρ` **heterogénea** sí hay reasignación (alto 0,5 y resto 0 → el estrato
alto se va a 8,48 km): también correcto.

## 2. ¿Tiene coherencia con la teoría?

### AU-06 / AU-07 — El artefacto de λ sigue vivo, y el arreglo está sin usar ⚠️

| Configuración | solver | d_alto | d_medio | d_bajo |
|---|---|---|---|---|
| λ = 1,1,1 | `logit` | 0,99 | 2,13 | 5,36 |
| **λ_alto = 0,5** | `logit` | **8,48** | 1,70 | 4,21 |
| λ_alto = 3 | `logit` | 0,94 | 2,14 | 5,37 |
| **λ_alto = 3** | `utility_logit` | **0,99** | **2,13** | **5,36** |

Bajar λ del estrato alto de 1 a 0,5 lo manda de **0,99 a 8,48 km** — de vivir
pegado al CBD a la periferia. λ es la utilidad marginal del ingreso: no es una
preferencia por localización y no debería mover a nadie. Es el artefacto
documentado en D-08 / Suelo.tex §2.6: al dividir por λ_h se rompe la hipótesis
de shocks idénticamente distribuidos, y λ termina actuando como escala de ruido
por estrato (~1/βλ).

**Lo relevante de esta auditoría**: la última fila muestra que `utility_logit`
**neutraliza λ por completo** — el resultado es idéntico al de λ = 1. O sea, la
corrección teórica funciona y está implementada en el core, pero la app corre
`logit` y no expone el selector. La razón está documentada (el precio del
solver consistente queda en utiles y no se integra con el downstream en $ del
acoplado), pero la consecuencia es que **el simulador enseña un modelo con una
inconsistencia conocida teniendo el arreglo al lado**.

Esto conecta con la contradicción ya detectada entre documentos: `Suelo.tex`
§2.7 (S-5) afirma que el heteroscedástico «es el default de la implementación
de referencia», lo que es falso. Punto para la reunión con los autores.

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

Iteraciones del punto fijo: base 36, pero **2.640** con ρ heterogénea y 511 con
λ heterogénea. El tope es `max_iter = 10.000`, así que no truncan, pero el
tiempo de respuesta se nota en la UI. Ninguna configuración probada falló en
converger.

## 4. Resumen ejecutivo

**El módulo es teóricamente sólido y responde correctamente en casi todo**: el
efecto Alonso funciona con la dirección, la magnitud y los casos límite
correctos (inversión y mezcla perfecta); las invariancias que la teoría exige
(ingreso, escala) se cumplen; β se comporta como escala de ruido; la
conservación de hogares es exacta.

Las dos observaciones de fondo:

1. **El artefacto de λ (AU-06/07)** — es la única incoherencia teórica viva, y
   el arreglo ya está implementado sin exponerse. Decisión de los autores.
2. **Sin techo de densidad (AU-08)** — la restricción de capacidad que sí existe
   (vaciado de mercado sobre `S`) es la correcta; falta la normativa. Extensión
   posible, no defecto.

Y una de forma: **`ρ` uniforme afecta precios y no localización (AU-05)**, lo
que es correcto pero invisible para el estudiante.
