# Cambios pendientes en el Overleaf — agenda para discutir con los autores

Este documento lista los cambios a revisar en el Overleaf original
(`main.tex`, `Suelo.tex`) surgidos de la auditoría **código ↔ Overleaf**
(junio 2026). Es una **agenda de discusión**, no cambios aplicados.

- **Política del proyecto**: el *código* es la fuente de verdad; el Overleaf se
  corrige para reflejarlo (salvo donde se indique "decisión de modelo").
- Cada ítem referencia su entrada en [`DISCREPANCIES.md`](DISCREPANCIES.md) y la
  ubicación aproximada en el `.tex` (sección/ecuación; los números de línea son
  orientativos y pueden moverse).
- El Overleaf se encuentra en `reference/overleaf/` (no versionado).

Categorías:
- **A. Correcciones de fidelidad** — el Overleaf está equivocado o es
  internamente inconsistente; hay que corregir el `.tex`.
- **B. Decisiones de modelo** — requieren criterio de los autores (calibración o
  alcance); no hay una respuesta "correcta" mecánica.
- **C. Funcionalidad nueva a documentar** — existe en el código (web V2) y falta
  en el paper.
- **D. Limpieza / menores**.

---

## A. Correcciones de fidelidad

> En varios casos el Overleaf **se contradice a sí mismo**: la *ecuación* dice una
> cosa y su propio *listado de código* dice otra. El código de esta web sigue los
> listados (que son los correctos). La acción es alinear la ecuación con el
> listado.

| ID | Ubicación (`.tex`) | Dice ahora | Debería decir | Motivo |
|----|---|---|---|---|
| **A1** (D‑01) | `main.tex` §Oferta bici, factor pendiente `p>0` | `f_p = -0.0579·p + 0.09992` | `f_p = -0.0579·p + 0.9992` | Con `0.09992` la velocidad colapsa al ~10% en terreno plano. El propio listado del Overleaf usa `0.9992`. |
| **A2** (D‑02) | `main.tex` §Demanda, utilidad bici (eqs. del resumen y de la sección Caminata/Bici) | `V_bici = ASC + (β_tviaje + β_{>10} + β_{>20} + β_{>30})·t` (multiplicativo) | `V_bici = ASC + β_tviaje·t + Σ_k 1{t>τ_k}·π_k` (penalizaciones **aditivas** escalonadas) | El listado de código del Overleaf es aditivo (`p += penal`). La forma multiplicativa no corresponde. |
| **A3** (D‑03) | `main.tex` §Demanda, utilidad caminata (ambas ecuaciones) | coeficiente de tiempo = `β_tviaje` | `β_tcaminata` | La caminata tiene su propia sensibilidad al tiempo (`b_tiempo_caminata`); el código y el listado lo usan. |
| **A4** (D‑05) | `main.tex` §Demanda, utilidad caminata (ecuación resumen) | umbrales `>5, >15, >30` | `>5, >15, >25` | El config y el código usan `walk_5/walk_15/walk_25`. (El corte de factibilidad sí es a 30 min; los umbrales de penalización son 5/15/25.) |
| **A5** (D‑05) | `main.tex` §Demanda, "Supuestos" | "Los usuarios no pueden realizar sus viajes caminando (inicialmente)" | La caminata **es** un modo válido, sujeto a corte de factibilidad `t_caminata ≤ 30 min` | El supuesto quedó desactualizado; caminata está en el choice set. |
| **A6** (D‑17) | `Suelo.tex` §Función de puje, *willingness to pay* | `w_h(u,i) = y_h − (u_h + f_h(i))/λ` | `w_h(u,i) = y_h − (u_h − f_h(i))/λ_h`  (es decir, **`+ f_h/λ`**) | Despejando `p` de `u_h = λ_h(y_h − p_i) + f_h(i)` se obtiene `+f_h/λ`. El operador de punto fijo del propio Overleaf y el código usan `y + f/λ`. La ecuación de WTP tiene el signo de `f` invertido. |
| **A7** | `Suelo.tex` (varias) | `λ` sin subíndice en algunas ecuaciones | `λ_h` | Notación: el parámetro es por estrato. |

**Resumen A:** todas son correcciones de texto/ecuaciones en el `.tex` para que
coincida con el código (que ya es correcto). No implican cambios de código.

---

## B. Decisiones de modelo (requieren a los autores)

| ID | Tema | Situación | A decidir |
|----|---|---|---|
| **B1** (D‑16) | Constantes de congestión de andén (metro) | Overleaf declara `α=10, β=10` (factor salta a ~10× apenas `ρ>1`). El código usa `α=0.5, β=4` (factor *cae* a 0.5 y solo supera 1 en `ρ>1.19`). | ¿Cuál es la calibración real del `app.py`? Idealmente reformular como **BPR continua** sin salto/caída en `ρ=1`. |
| **B2** (D‑12) | Activación de la congestión de andén | El umbral usa `frec_max·K` (capacidad a frecuencia máxima); con ciudades típicas (~10k agentes) **nunca** se alcanza → la espera queda plana. | ¿Es el comportamiento deseado, o se quiere que la congestión sea visible en operación normal? |
| **B3** (D‑08) | Logit de uso de suelo con `λ_h` heterogéneo | El propio Overleaf (sección "Notas") reconoce que es inconsistente y sugiere logit‑heteroscedástico; el código incluye además un método `frechet` marcado "MALA". | ¿Se adopta el logit‑heteroscedástico como método principal? ¿Se documenta el `frechet` como alternativa didáctica? |

---

## C. Funcionalidad nueva a documentar en el Overleaf

> Existe en el código de la web (V2) pero **no aparece en el Overleaf**. Hay que
> decidir si se documenta en el paper y redactar la sección correspondiente.

| ID | Qué | Estado en código |
|----|---|---|
| **C1** (D‑14) | **Loop acoplado suelo↔transporte**: itera uso de suelo y transporte hasta estabilizar `T`, con amortiguación MSA exterior y residual. El Overleaf describe suelo y transporte **por separado**, no el bucle. | Implementado (`coupled.py`); corregido esta sesión (residual en minutos + MSA). |
| **C2** (D‑10) | **Criterio de convergencia por tolerancia**: corta cuando el residual (máx. cambio de tiempo de cualquier modo) `< tol` en 2 iteraciones consecutivas. El Overleaf solo describe `MAX_ITER`. | Implementado (`msa.py`), con slider en la UI. |
| **C3** (D‑13) | **Oferta de suelo `S(i)` determinista** (campana normal exacta, Σ=N) + parámetro **σ** de dispersión (compacidad urbana) expuesto. El Overleaf solo dice "según una distribución normal centrada en el CBD". | Implementado (`supply.py`, `LandUseConfig.oferta_sigma_frac`). |
| **C4** (D‑15) | **Piso bici ≤ caminata**: una bici congestionada no puede ser más lenta que caminar (el Overleaf no lo acota → produce tiempos absurdos en periferia). | Implementado (`bike.py`). |
| **C5** (D‑06) | **Módulo de emisiones de CO₂** (factores `factor_emision_auto/metro` ya en config). El Overleaf lo menciona en globales pero no lo formaliza; en la web aún **no está conectado** al pipeline ni se muestra. | Parcial: parámetros existen, falta cablear y documentar. |
| **C6** (D‑09) | **Parámetros físicos expuestos en la UI** (velocidades, anchos, α/β BPR, pendiente, etc.) que en el original estaban hardcodeados. | Mayormente expuestos en la web. |
| **C7** | **Método de asignación opcional**: además del Monte Carlo del Overleaf (sorteo por agente con `random.choices`), se agregó **"flujos esperados"** (asignación fraccional por probabilidades logit), determinista y sin ruido entre iteraciones. Toggle en la UI; **pendiente decidir con el profesor cuál dejar definitivo**. | Implementado (`msa.py`, `SimulationConfig.assignment`). |

---

## D. Limpieza / menores

| ID | Tema | Nota |
|----|---|---|
| **D1** (D‑07) | Jornadas laborales (`P^s_jornada`) | Infraestructura preparada pero **inactiva** (no entra en `calcular_utilidades`). Documentar como trabajo futuro o quitar del paper. |
| **D2** (D‑11) | `generar_poblacion` con sampleo uniforme | Código muerto en el original; no portado. No documentar como parte del modelo vigente. |
| **D3** | Figuras del Overleaf (`ofbi`, `ofau`, `oftr`, `suelo1`, diagramas de demanda) | Revisar que reflejen las ecuaciones corregidas (A1–A6). |
| **D4** | Constantes de iter 0 (`t_acceso=10`, `t_espera=5`) | El Overleaf y el código coinciden; solo verificar que queden explícitas como supuesto. |

---

## Lo que ya es fiel (no requiere cambios)

Para acotar la discusión: la auditoría confirmó que **sí coinciden** Overleaf y
código en — config de demanda completa (betas, ASC, costos, velocidades,
penalizaciones por estrato), MSA (`f=1/(it+1)`), flujo libre en iteración 0,
Greenshields + BPR acumulada (auto/bici), tren de 3 componentes con frecuencia
endógena, y el modelo bid‑rent de uso de suelo (utilidad lineal en ingreso,
logit `Q`, operador de punto fijo). Las divergencias se concentran en A, B y C.

---

## Prioridad sugerida para la reunión
1. **B1/B2** (congestión de andén) — es la única divergencia *numérica* de comportamiento.
2. **A1–A6** — correcciones de ecuaciones (rápidas, mejoran la consistencia del paper).
3. **C1–C4** — decidir qué V2 se documenta en el paper.
4. **B3 / D** — alcance futuro y limpieza.
