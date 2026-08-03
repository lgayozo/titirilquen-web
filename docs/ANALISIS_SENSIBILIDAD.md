# Análisis de sensibilidad de la configuración — Iteración 2 (agosto 2026)

Registro de hallazgos `S-xx`. Complementa a `DISCREPANCIES.md` (D-xx, fidelidad
código↔paper): aquí la pregunta no es si el código implementa el modelo, sino si
**los parámetros que la UI expone mueven el resultado**. Todos los números de este
documento están **medidos** ejecutando el core (no estimados); la evidencia clave se
reproduce con `packages/titirilquen_core/scripts/sensibilidad.py`.

| ID | Hallazgo | Estado |
|---|---|---|
| S-01 | KPI v/c usaba demanda originada en vez de flujo de corredor (subestima ~62×) | **CORREGIDO** (it. 2) |
| S-02 | NetworkDiagram dividía la capacidad dos veces por `num_pistas` | **CORREGIDO** (it. 2) |
| S-03 | Escala default (500 hab/km) dejaba la BPR del auto sin morder | **CORREGIDO** (it. 2) |
| S-04 | Capacidad del auto acoplada a la velocidad (`cap_pista ∝ v_l`) | **CORREGIDO** (it. 3: `capacidad_pista` opcional) |
| S-05 | Parámetros muertos o inertes en el schema | DOCUMENTADO |
| S-06 | Vacío de normalización de unidades (viajes/período vs veh/h) | DOCUMENTADO |
| S-07 | Metro: `capacidad_tren` con signo invertido y sin hacinamiento | PROPUESTA it. 3 |

## 0. Resumen ejecutivo

**Síntoma reportado**: mover la oferta de auto (pistas, velocidad) no cambiaba el
equilibrio. **Tres causas apiladas**, de superficie a raíz:

1. El KPI v/c mostraba 0.00× por un error de numerador (S-01) — el corredor real
   operaba a 0.27×, pero nadie podía verlo.
2. Aun con 0.27×, el término BPR aportaba +0.41 min sobre 19.16 (+2.2%): la
   congestión valía 0.014 utiles frente a una ASC de 0.79 y un costo de −1.44.
   `num_pistas` 1→20 movía el reparto **0.21 pp**. La red estaba sobredimensionada.
3. La causa raíz era de **escala, no de la BPR** (S-03): el default de la UI
   (500 hab/km) era 3.6× más liviano que el propio preset «Base» del repo (1800).

**Qué se corrigió en esta iteración**: el trace expone el flujo de corredor
(numerador correcto del v/c), el diagrama de red dejó de duplicar las pistas, y el
default subió a 1800 hab/km. Resultado medido: la sensibilidad de `num_pistas`
pasó de 0.20 a **2.05 pp** (13×) y el v/c default de 0.27 a **0.95**.

## 1. Metodología

- Baseline: defaults de la UI — 201 celdas, 20 km, seed 42, `expected`,
  tolerance 0.1, betas de `defaults.ts`. Población según la ruta indicada.
- Reparto modal baseline (10.000 hab, ruta core): auto 11.79% · metro 48.40% ·
  bici 18.26% · caminata 7.13% · teletrabajo 14.42%.
- Reproducir: `cd packages/titirilquen_core && uv run python scripts/sensibilidad.py`
  (sale 1 si los umbrales esperados no se cumplen — sirve de regresión).
- Nota de rutas de población: el core/API usan `generar_poblacion` (densidad
  plana); la app usa `iter_msa_desde_suelo` (ΣH de `LandUseConfig`). Misma escala,
  localización inicial distinta; los v/c difieren ~5%.

## 2. Diagnóstico del auto

### S-01 — KPI v/c mal calculado [CORREGIDO]

`SandboxPage.tsx` dividía `max(demanda_auto)` — los viajes **originados** por celda
(~9.6 veh) — por la capacidad direccional (2214 veh/h). En una ciudad lineal
monocéntrica el volumen crítico es el flujo que **atraviesa** el tramo rumbo al CBD
(cumsum direccional): 597 veh/h en la celda crítica. v/c real 0.27, mostrado 0.00×.

El core ya calculaba ese cumsum (`supply/car.py`, `flujos_veh_por_hora`) pero el
valor moría en el `last_state` de `msa.py` sin llegar al trace. Fix: el
`ConvergenceTrace` expone `flujos_auto_veh_h` / `flujos_bici_veh_h` (estado final)
y el KPI divide `max(flujo)/capacidad`. Espejos actualizados (worker + API).

Efecto lateral revelado: el **v/c de bici saltó de 0.03× a ~1.3×** — la ciclovía
estaba congestionada y el bug lo ocultaba (ver §4).

### S-02 — Doble conteo de pistas en el diagrama de red [CORREGIDO]

`NetworkDiagram.tsx` hacía `capacidad_auto × num_pistas`, pero `capacidad_auto` es
la `capacidad_direccion` del core, que **ya incluye** las pistas (`car.py`:
`cap_pista · num_pistas`). El v/c pintado era la mitad del real y — perverso —
**empeoraba** cuando el usuario agregaba pistas.

### S-03 — Causa raíz: escala de población [CORREGIDO]

Cálculo con defaults (previos) y los valores reales del código:

```
densidad_emb  = 1000/(5+2)        = 142.86 veh/km      (largo_vehiculo + gap)
cap_pista     = 142.86·31/4       = 1107.1 veh/h       (Greenshields q_max = k_j·v_f/4)
capacidad     = 1107.1·2          = 2214.3 veh/h       (2 pistas)
viajes auto   ≈ 11.8% de 9.950    ≈ 1.173
flujo máx     ≈ 1.173/2 (un lado) ≈ 597 veh/h  →  v/c = 0.27
BPR peor celda: 0.8·0.27² = 0.058 → +5.8% ese tramo; promedio del corredor ≈ ⅓
t_auto[0]: 19.58 min con α=0.8 vs 19.16 con α=0 → Δcongestión = +0.41 min (+2.2%)
en utiles (estrato 2): b_t·Δ = −0.0331·0.41 = −0.014, frente a |V| ≈ 1.3
```

Para v/c = 1 hacen falta ~4.430 viajes en auto ≈ 37.500 agentes ≈ **1.875 hab/km**.
El preset «Base» del propio repo define **1800**; el default de la UI era 500.

Barrido medido (salida de `scripts/sensibilidad.py`, post-fix S-01):

| densidad (hab/km) | pistas | % auto | v/c corredor | t_auto máx (min) | convergió |
|---|---|---|---|---|---|
| 500 | 1 | 11.63 | 0.53 | 20.8 | sí |
| 500 | 2 | 11.79 | 0.27 | 19.6 | sí |
| 500 | 3 | 11.82 | 0.18 | 19.3 | sí |
| 500 | 4 | 11.83 | 0.14 | 19.3 | sí |
| 500 | 5 | 11.83 | 0.11 | 19.2 | sí |
| 500 | 6 | 11.83 | 0.09 | 19.2 | sí |
| 1800 | 1 | 10.29 | 1.67 | 34.5 | sí |
| 1800 | 2 | 11.72 | 0.95 | 24.3 | sí |
| 1800 | 3 | 12.09 | 0.66 | 21.6 | sí |
| 1800 | 4 | 12.24 | 0.50 | 20.6 | sí |
| 1800 | 5 | 12.31 | 0.40 | 20.1 | sí |
| 1800 | 6 | 12.34 | 0.34 | 19.8 | sí |

Δ% auto (pistas 1→6): **0.20 pp** con 500 · **2.05 pp** con 1800 (13×).

Fix aplicado: `defaults.ts` 500→1800 y `H_por_estrato` [3600, 14400, 18000]
(ΣH = 36.000); slider de densidad media hasta 3000; divergencia intencional
registrada en `contract.spec.ts`; tutorial 02-city actualizado. El core conserva
la escala liviana (500) — la divergencia es deliberada y está documentada.
Costo verificado: corridas ~20 s post-boot (antes ~8 s) con 36.000 agentes.

### S-04 — Capacidad acoplada a la velocidad [CORREGIDO it. 3]

`car.py`: `cap_pista = k_e·v_l/4` — es el q_max de Greenshields, correcto en
teoría, pero convierte a `v_max_kmh` en una palanca doble: subir la velocidad sube
la capacidad en la misma proporción, así que **la velocidad nunca puede empeorar
la congestión** (medido: v/c cae de 0.27 a 0.10 al pasar de 31 a 80 km/h). En una
BPR estándar `v_f` y `C` son parámetros separables. **Corregido en it. 3**:
`CarSupplyParams.capacidad_pista: float | None` — `None` conserva Greenshields
exacto (default retrocompatible); un valor explícito fija C independiente de
v_f (checkbox «capacidad manual» + slider en el Sandbox). Verificado: cap 600 +
v_max 60 → capacidad 1200 con v_libre 60 y v/c 1.77 — «vía rápida y saturada»,
el régimen antes inexpresable.

## 3. Tabla parámetro → efecto medido → veredicto

Rango barrido con el resto en default (10.000 hab salvo indicación). «Δ» es el
cambio del share del modo correspondiente en puntos porcentuales.

### Ciudad y raíz

| Parámetro | Barrido | Efecto | Veredicto |
|---|---|---|---|
| `largo_ciudad_km` | 10→40 | auto 10.5→12.9%, metro 36→60% | sensible |
| `n_celdas` | 51→1001 | auto 12.20→12.13% | neutro (D-28 funciona) |
| `teletrabajo_factor` | 0→3 | tele 0→40.6%, auto 16.7→3.8% | muy sensible |
| `pendiente_porcentaje` | ±8 | bici 18.3→16.2%; casi simétrico en ± (se aplica +p izquierda, −p derecha) | sensible con matiz |
| `densidad_hab_km` | 500→20.000 | v/c 0.27→12 | sensible **pero muerto en la app** (S-05) |
| `share_estratos` | extremos | auto 3.8↔41.2% | ídem |
| `max_iter` | 1→60 | converge en 8-12 | no binding |
| `tolerance` | 0→5 | corta 20→4 iters | el corte real |
| `assignment` | mc/expected | 11.33 vs 11.79% auto | sensible leve |
| `seed` | — | nada con `expected` + ruta suelo (determinista) | condicional |

### Oferta auto (post S-03, evaluada a 1800 hab/km)

| Parámetro | Barrido | Efecto | Veredicto |
|---|---|---|---|
| `v_max_kmh` | 15→80 | 3.2 pp (a 500); mayor a 1800 | sensible, con doble efecto (S-04) |
| `num_pistas` | 1→6 | 2.05 pp (a 1800; 0.20 a 500) | **rehabilitado por S-03** |
| `alpha_bpr` | 0→5 | leve; escala con v/c | vivo a 1800 |
| `beta_bpr` | 1→8 | con v/c<1 el signo se invierte (β↑ ⇒ demora↓) | cuidado pedagógico |
| `ancho_pista_m` | 2.5→5 | escalón 0.75/0.9/1.0 topado en 3.5 | muerto hacia arriba |
| `largo_vehiculo_m`, `gap_m` | — | solo vía capacidad, efecto ínfimo a 500 | casi muerto a 500 |

### Oferta bici — el modo congestionado

| Parámetro | Barrido | Efecto | Veredicto |
|---|---|---|---|
| `capacidad_pista` | 100→5000 | bici **7.6→24.0%** (16.4 pp) | la palanca de oferta más fuerte del simulador |
| `v_media_kmh` | 8→25 | bici 10.6→25.7% | muy sensible |
| `alpha_bpr` (bici) | 0→10 | bici 24.2→9.2% | muy sensible (v/c>1: sí muerde) |
| `beta_bpr` (bici) | — | vivo | sensible |

Contexto: con defaults la ciclovía (cap. 800) tiene 2.8× menos capacidad que la
calzada (2214) con flujos comparables. El techo de caminata (R-7/D-21) la satura
en 2.92× el flujo libre — capacidad blanda, plana.

### Oferta metro

| Parámetro | Barrido | Efecto | Veredicto |
|---|---|---|---|
| `num_estaciones` | 2→40 | metro **38.7→50.7%** | la palanca dominante (vía t_acceso) |
| `v_tren_kmh` | 15→70 | metro 45.4→49.6% | sensible |
| `capacidad_tren` | 100→3000 | metro 49.0→48.2%, f 23.4→6.0 | **signo invertido** (S-07) |
| `frec_min` / `frec_max` | — | f_op = 7.69 en el interior de [6,30]: ambos inertes | inertes con defaults |
| `anden_alpha` / `anden_beta` | 0→5 / 1→10 | ρ = 0.256 → factor 1.002 (+0.5 s): nada | inertes (D-16 abierto) |
| `v_caminata_kmh` (acceso) | — | vivo | sensible |
| `tasa_carga` | 6→100 | resultado byte a byte idéntico | **no implementado** |

### Economía (las palancas reales del auto)

| Parámetro | Barrido | Efecto | Veredicto |
|---|---|---|---|
| `costo_parking` | 0→30.000 | auto **22.9→2.7%** | la palanca #1 del simulador |
| `costo_combustible_km` | 120→600 | auto 11.8→9.6% | sensible |
| `costo_tarifa_metro` | 0→3000 | metro 52.5→39.1% | sensible |
| `v_caminata` (global) | 4.8→8 | caminata 7.1→12.5% | sensible (también techo de bici) |

## 4. Parámetros muertos e inertes (S-05)

Detalle en el Anexo C de `docs/diagrama-flujo.html`. Resumen:

| Parámetro | Por qué está muerto | Recomendación |
|---|---|---|
| `tasa_carga` | `train.py`: `_ = tasa_carga` (no implementado) | implementar o quitar del schema |
| `factor_emision_auto` | huérfano: la emisión usa COPERT `2467.4·v^-0.699` | quitar (con migración .ttrq) |
| `prob_jornada_flexible`, `prob_part_time`, `jornada.*` | nunca leídos (D-07) | quitar o documentar como futuro |
| `frec_min`/`frec_max` | f_op cae en el interior; presets «Máx Metro» y «TP Gratis» tocan un knob inerte | recalibrar presets o mostrar actividad en la UI |
| `anden_alpha`/`anden_beta` | factor 1.002 con defaults | recalibrar con autores (B1/B2) |
| `v_auto`/`v_metro`/`v_bici` globales | solo semilla de iteración 0 | documentar en la UI o quitar sliders futuros |
| `densidad_hab_km`, `share_estratos` | la ruta `desde_suelo` puebla desde `H_por_estrato` | señalizar en la UI que la escala vive en Uso de Suelo |
| `densidad_max/min`, `densidad_estrato` (suelo) | vestigiales post `S/Δx` | quitar con migración |

Ninguno se elimina en esta iteración (tocan schema y migraciones de escenarios
guardados); la decisión de limpieza es de la iteración 3.

## 5. Vacío de normalización de unidades (S-06)

La demanda es «hogares que viajan en el período» y la capacidad es veh/**hora**.
No existen `factor_hora_punta` (~0.10–0.25) ni `ocupacion_auto` (~1.2–1.5
pax/veh) en el core: la comparación demanda/capacidad asume implícitamente
1 viaje = 1 veh/h. Los dos factores se cancelarían parcialmente, pero
explicitarlos haría auditable la escala (y daría dos palancas pedagógicas
nuevas). Las emisiones (`total_kg` «por hora») heredan la misma ambigüedad.
Propuesta para iteración 3, coordinada con los autores del apunte.

## 6. Metro: signo invertido y hacinamiento ausente (S-07)

`capacidad_tren` no es una restricción de confort: es el **divisor de la
frecuencia** (`f = carga/K`). Trenes más grandes ⇒ menos frecuencia ⇒ más espera
⇒ menos metro (medido: K 100→1000 baja el share 0.9 pp). No existe penalización
por hacinamiento en el vehículo en todo el core; el único castigo por carga es la
BPR de andén, hoy inerte (D-16). Un usuario que sube «capacidad del tren»
esperando mejorar el metro obtiene lo contrario. Propuesta it. 3: añadir un
término de hacinamiento en vehículo (p. ej. multiplicador BPR sobre t_viaje con
ρ = carga/(f·K)) y revisar la calibración del andén con los autores.

## 7. Recomendaciones priorizadas para iteración 3

- **P0** — Desacoplar capacidad de velocidad (S-04); término de hacinamiento en
  vehículo + calibración de andén con autores (S-07/B1-B2); exponer presets de
  ciudad en el Sandbox para que la escala sea una elección visible (ver
  ANALISIS_FRONTEND F-01).
- **P1** — `factor_hora_punta` + `ocupacion_auto` explícitos (S-06); señalizar
  en la UI los parámetros inertes (frec_min/max cuando f_op está en el interior;
  densidad cuando manda H_por_estrato).
- **P2** — Limpieza de muertos con migración de schema (S-05); revisar el rango
  del slider β BPR auto (con v/c<1 su efecto pedagógico es contraintuitivo).

## Anexo — Reproducción

```bash
cd packages/titirilquen_core
uv run python scripts/sensibilidad.py
```

Salida esperada: la tabla de §2/S-03 y `OK: sensibilidad conforme a lo esperado`
(exit 0). Si el core cambia y los umbrales dejan de cumplirse, el script sale 1.
