# Módulo "Ciudad en equilibrio" (loop acoplado suelo ↔ transporte)

Resumen del módulo, los cambios de esta tanda de trabajo (jun-2026) y lo que
queda pendiente. Para el contexto general del repo ver `CLAUDE.md` y
`docs/ARCHITECTURE.md`; las decisiones de modelo están en `docs/DISCREPANCIES.md`.

## Qué es

Página `/coupled` (`CoupledPage.tsx`). Reconcilia **uso de suelo** (dónde vive
cada estrato, vía bid-rent) y **transporte** (cómo y cuánto tarda en viajar al
CBD) iterando hasta un equilibrio mutuo:

```
iter 0: suelo con accesibilidad a flujo libre (baseline "sin feedback")
para n = 1..N:
    1. población determinista desde el suelo (Q · S)
    2. MSA de transporte → tiempos por modo/celda
    3. accesibilidad T(i) esperada (común por ubicación, en minutos)
    4. el suelo se re-resuelve con T
    5. corta si ‖ΔT‖∞ < tolerancia
```

El núcleo vive en Python (`packages/titirilquen_core/`) y corre idéntico en
FastAPI y en Pyodide (navegador). **Tras tocar el core hay que recompilar el
wheel** (`apps/web/public/pyodide/*.whl`); en este entorno `npm run
build:core-wheel` falla por PEP 668 → usar `uv build` y copiar (ver más abajo).

## Arquitectura

**Core (`titirilquen_core/`)**
- `coupled.py` — `iter_coupled` (streaming) y `run_coupled`. Baseline a flujo
  libre (`_freeflow_T`), accesibilidad esperada común (`_aggregate_T_expected`),
  amortiguación MSA del loop externo.
- `coupled_metrics.py` — todas las métricas del equilibrio (por estrato + del
  sistema): localización, tiempo, reparto modal, costo, excedente del
  consumidor, carga costo/ingreso, Theil, emisiones, regresividad. La matemática
  vive acá; el frontend solo renderiza.
- `population.py` — `generar_poblacion_desde_land_use_det` (determinista, sin
  rng, por mayor residuo) para que el loop sea reproducible y converja.

**Frontend (`apps/web/src/`)**
- `pages/CoupledPage.tsx` — layout `.page`/`.sidebar`/`.main`.
- `lib/joint-presets.ts` — presets conjuntos (ciudad+política+suelo) + parámetros
  visibles + población por escenario.
- `lib/citySupply.ts` — oferta S(i) para visualización (espejo de
  `generar_oferta`); fuente única de la forma.
- `components/viz/` — `CityShapePreview` (forma), `EquilibriumMetricsTable`
  (métricas), `ModalShareBars` (reparto modal), `OuterTrajectory` (curva de
  convergencia), `StratumDistribution` (distribución espacial).

## Cambios de esta tanda (jun-2026)

### Modelo (core)
- **Métricas de equilibrio centralizadas** en `coupled_metrics.py` (+ tests).
  Cada `OuterIteration` lleva su `metrics`, que viaja por el streaming (SSE y
  worker Pyodide) sin recomputar.
- **Loop determinista**: población por mayor residuo + asignación esperada →
  el equilibrio es reproducible y converge sin el piso estocástico (D-14).
- **D-22 — accesibilidad común por ubicación** (no por estrato): arregla la
  inversión del bid-rent (ricos quedaban en la periferia).
- **D-23 — baseline "sin feedback" en minutos a flujo libre** (no índices de
  celda): elimina el artefacto de unidades que inflaba el efecto del feedback.
- **D-24 — población por escenario**: el corredor monocéntrico gridlockea con
  demanda alta; cada preset trae su `poblacionDefault`.

### Frontend (UI)
- **Rediseño** al patrón de los otros módulos: escenarios en sidebar izquierdo
  ("Mi configuración" por defecto + presets de prueba rápida), imagen de la
  ciudad arriba.
- **Escenario custom por defecto**: corre con la config de los módulos
  Transporte (Sandbox) y Uso de Suelo (stores compartidos).
- **Presets transparentes**: muestran las palancas que los definen (largo,
  población, compacidad σ, pistas, frecuencia, tarifa, parking, combustible…) +
  vista previa de la forma.
- **Palanca de población** (escala de demanda) reemplaza a `densidad` (que no
  afectaba el acoplado).
- **Tabla de métricas** clara: hogares marcado como *input* (sin Δ), nota "Δ vs
  iter 0", reparto modal en barras anchas legibles (`ModalShareBars`).
- **Curva de convergencia** del residuo ‖ΔT‖∞ (figura 03), antes ausente.
- **Oferta S consistente**: el resultado se dibuja como `S × Q` → respeta la
  forma elegida; la figura de la forma y el resultado comparten envolvente.
- **Figuras sin redundancia**: la distribución espacial vive solo en los paneles
  Sin/Con feedback; Convergencia es solo la curva; la figura de la forma es
  preview pre-run.
- **Iteraciones**: control 2–50, default 12.

## Estado actual

Funciona y los escenarios diferencian de forma coherente (con su población por
defecto): ordenamiento bid-rent correcto (alto<medio<bajo), compacta→cerca /
dispersa→lejos, toll→menos auto, pro-bici→más bici, metro responde, compact-metro
los menores tiempos. `tsc`, `eslint` y los tests del core en verde.

**Lectura honesta del modelo**: el canal **suelo→transporte** y la respuesta del
**lado transporte** (congestión, frecuencia, reparto modal) funcionan bien. El
canal **transporte→suelo sobre la localización es genuinamente modesto** (el
bid-rent lo domina el gradiente de distancia); antes parecía grande por el
artefacto de unidades (D-23).

## Pendientes

- **Estabilidad del loop externo** (D-24): damping adaptativo / relajación para
  admitir demanda alta en ciudades grandes sin acotar por población.
- **Amplificar el feedback transporte→suelo** si se quiere mayor efecto
  pedagógico (p. ej. α de accesibilidad más separados, o calibrar a minutos) —
  decisión de modelado pendiente.
- **Frecuencia de metro** queda en el piso con demanda baja (no es bug, es
  escala); revisar si conviene recalibrar capacidad/umbral.
- Edición inline de parámetros en la página acoplada (hoy se editan en los otros
  módulos).

## Recompilar el wheel (gotcha del entorno)

`npm run build:core-wheel` falla por PEP 668. Alternativa:

```bash
cd packages/titirilquen_core
uv build --wheel --out-dir /tmp/ttrq-wheel
cp /tmp/ttrq-wheel/titirilquen_core-0.1.0-py3-none-any.whl ../../apps/web/public/pyodide/
```

Tests del core: `uv run --with pytest pytest -q` (no hay `python`/`pytest`
globales; sí `uv`).
