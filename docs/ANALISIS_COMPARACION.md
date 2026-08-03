# Análisis del flujo de comparación de escenarios — Iteración 2 (agosto 2026)

Registro de problemas `C-xx` de ComparePage y propuesta de métricas pedagógicas.
**Diagnóstico + propuesta; la implementación es de la iteración 3.**

La comparación de escenarios es el cierre pedagógico del simulador: ahí es donde
«¿qué pasa si…?» se convierte en una tabla de efectos. Hoy la mecánica existe
(4 tarjetas × 3 lentes) pero tiene una inconsistencia de población que puede
producir conclusiones falsas (C-02) y varios costos de fricción.

| ID | Problema | Estado |
|---|---|---|
| C-01 | Base de comparación implícita, no seleccionable | P1 (pendiente) |
| C-02 | La lente Transporte corre sin `land_use`: población distinta al Sandbox | **CORREGIDO** (it. 3; paridad exacta verificada, salvo modo engine=api) |
| C-03 | Sin detección de staleness en tarjetas | P1 (pendiente) |
| C-04 | Sin export CSV de la comparación | **CORREGIDO** (it. 3, + fila v/c en KPITable) |
| C-05 | Sin cancelación ni feedback de cola | P2 |
| C-06 | `outer_max_iter` incoherente (12 al exportar vs 8 al correr) | P2 (corrección) |
| C-07 | Colores hex fijos fuera del sistema de temas | P2 |

## 1. El flujo actual

- `compareStore`: hasta 4 tarjetas (A–D), cada una con `{config, landUse,
  poblacion}` y 3 resultados independientes (uno por lente).
- Fuentes de escenario: «Usar Transporte actual» (copia los stores vivos),
  import `.ttrq.json` (con migraciones v1→v2), o nada.
- Lentes: **Transporte** (`pyodideEngine.simulate`), **Uso de suelo**
  (`solveLandUse`), **Ciudad en equilibrio** (`solveCoupled`, `COMPARE_OUTER_MAX
  = 8`, `outer_tol = 1.0`).
- Salidas por lente: chips de highlights vs base (ΔCO₂, Δ%auto, Δtiempo por
  estrato), `KPITable` (reparto, tiempos, operación, emisiones, por estrato),
  overlay de curvas de demanda; Theil y distancias al CBD en suelo; 8 métricas
  del reporte del core en acoplado.
- La base es la **primera tarjeta con resultado** (`find(status === "done")`).

## 2. Problemas detectados

### C-02 — Población inconsistente con el Sandbox [P0]

`ComparePage` corre la lente Transporte con `pyodideEngine.simulate(sc.config)`
**sin pasar `land_use`**: la población sale de la ruta core (`densidad_hab_km`
plana, mezcla uniforme). El Sandbox corre `simulateStream(config, …,
landUseConfig, localizacion)`: población desde `H_por_estrato` con la
localización del bid-rent si corrió. Consecuencia: **el «mismo escenario» da
resultados distintos en Sandbox y en Compare**, sin ninguna señal. Tras el
cambio de escala S-03 (densidad 1800 y ΣH 36.000 quedaron en sync) la brecha de
escala se cerró, pero la de **localización** persiste: si el usuario corrió el
bid-rent, el Sandbox usa la ciudad de equilibrio y Compare la mezcla uniforme.

**Propuesta**: la lente Transporte debe llamar al motor con el `landUse` de la
tarjeta (que ya viaja en el `.ttrq.json` v2) y la misma regla de localización
del Sandbox. Es la corrección de mayor prioridad de este documento.

### C-01 — Base implícita [P1]

La base es la primera tarjeta que termina — depende del orden de corrida y no se
puede cambiar. Pedagógicamente la base ES la pregunta («¿contra qué comparo?»).
**Propuesta**: selector de base explícito (radio en la tarjeta), default A.

### C-03 — Sin staleness [P1]

Editar la config del Sandbox no marca la tarjeta que la copió; `setScenario`
invalida resultados pero renombrar no; no hay banner equivalente al del Sandbox.
**Propuesta**: reutilizar el patrón `configUsed`/`isResultStale` por tarjeta.

### C-04 — Sin export CSV [P0]

`lib/csv.ts` existe (lo usa `TransportMetricsTable`) pero la comparación — la
tabla que un docente quiere llevarse a planilla — no exporta. **Propuesta**:
botón «Exportar CSV» por lente (filas = métrica, columnas = escenarios + deltas),
reutilizando `toCsv`/`downloadCsv` tal cual.

### C-05 — Sin cancelar ni cola visible [P2]

«Correr todos» encola hasta 4 corridas en un único worker serial sin posición de
cola ni botón de cancelar; la única señal es la barra indeterminada de cada
tarjeta. **Propuesta**: AbortController por tarjeta + texto «en cola (2/4)».

### C-06 — `outer_max_iter` incoherente [P2]

El export de tarjeta escribe `coupled.outer_max_iter: 12` (hardcodeado) pero la
lente acoplada corre con `COMPARE_OUTER_MAX = 8`: el archivo declara una
configuración que la corrida no usa. **Propuesta**: una sola constante
compartida, y que el export refleje lo que se corre.

### C-07 — Colores fuera del tema [P2]

`ScenarioFlowComparison` usa 4 hex fijos (`#0ea5e9`…) que no responden al tema
paper/ink. **Propuesta**: variables CSS de escenario (--esc-a…--esc-d) en el
sistema de temas.

## 3. Propuesta de métricas pedagógicas de comparación

Hoy cada lente muestra métricas razonables pero heterogéneas y sin las de
congestión. Set propuesto por lente (columnas = escenarios, base explícita,
deltas coloreados con `lowerIsBetter` como ya hace `KPITable`):

**Transporte** (jerarquía: sistema → congestión → equidad):

| Grupo | Métrica | Fuente | Nota |
|---|---|---|---|
| Sistema | reparto modal (5), tiempo medio por modo, viajes físicos | `computeKPIs` | ya existe |
| Congestión | **v/c máx auto y bici** (flujo corredor/capacidad), frecuencia metro | `flujos_*_veh_h` del trace (S-01) | **nueva — recién posible** |
| Ambiente | CO₂ total/auto/metro | trace | ya existe |
| Equidad | tiempo medio y % por modo por estrato | `computeKPIs` | ya existe; añadir Δ bajo−alto |
| Bienestar | ΔCS por estrato vs red vacía | portar `_tiempos_red_vacia`/logsum de `coupled_metrics` a la lente V1 | nueva; ojo D-30: declarar el baseline usado |

**Uso de suelo**: Theil, distancia media al CBD por estrato (ya existen) +
precio implícito relativo en el CBD y gradiente centro-periferia (de `p[]`).

**Ciudad en equilibrio**: las 8 del reporte actual (Theil, tiempo, %auto, carga
costo/ingreso del bajo, ratio bajo/alto, Δbienestar, CO₂, iteraciones) + v/c del
equilibrio final. Mantener el sufijo «⚠ sin converger».

Reglas transversales:

- **Un solo baseline declarado por métrica** (D-30 documenta tres «sin
  congestión» distintos — la tabla debe decir cuál usa cada fila).
- Deltas en unidades naturales (pp, min, kg/h, $) y no solo porcentajes.
- Toda métrica visible debe ser **sensible**: no mostrar filas que los
  parámetros de la UI no pueden mover (criterio de ANALISIS_SENSIBILIDAD).

## 4. Flujo rediseñado (propuesta iteración 3)

- P0: corrección C-02 (land_use en la lente Transporte) + export CSV (C-04) +
  fila de congestión v/c en la KPITable (habilitada por S-01).
- P1: base seleccionable (C-01), staleness por tarjeta (C-03), y «duplicar
  escenario» (hoy solo se puede partir de cero, del Sandbox o de archivo — para
  el patrón docente «igual que A pero con X» falta el clon).
- P2: cancelación/cola (C-05), constante única del acoplado (C-06), colores de
  tema (C-07), ΔCS en la lente V1.

## 5. Criterios de aceptación (iteración 3)

- C-02: exportar un escenario del Sandbox, importarlo en Compare y correr la
  lente Transporte reproduce el reparto modal del Sandbox a <0.1 pp (e2e).
- C-04: el CSV exportado abre en Excel es-CL (BOM UTF-8, ya resuelto en
  `csv.ts`) con una columna por escenario y filas por métrica.
- C-01: cambiar la base recalcula todos los deltas sin recorrer.
- Congestión: la fila v/c aparece en la lente Transporte y cambia al variar
  `num_pistas` con la escala default (verificable tras S-03).
