# Registro de Discrepancias — Código ↔ Overleaf

Este documento registra las divergencias entre el código fuente (`titirilquen-repo/`) y la documentación matemática en el Overleaf (`Titirilquen_overleaf/`). La política del proyecto es **tratar el código como fuente de verdad** y corregir la documentación matemática; este archivo preserva la trazabilidad de las decisiones.

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
- **Acción**: En `titirilquen_core.equilibrium.msa` añadir criterio `tol` con fallback a `MAX_ITER` y exponer residuo por iteración para visualización.

---

## D-11 · Código muerto en `generar_poblacion`

- **Código** — `app.py:256-278`: Define `generar_poblacion` con sampleo uniforme de estratos (`random.choice([1,2,3])`), pero el botón simular usa `mi_ciudad.generar_poblacion_completa(config)` que respeta la distribución generada por `Ciudad` (modelo Alonso).
- **Veredicto**: Código muerto.
- **Acción**: No portar a `titirilquen_core`.

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
