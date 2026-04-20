# Arquitectura

## Visión general

```
┌──────────────────────────────────────────────────────────────────┐
│                         titirilquen-web                          │
│                                                                  │
│  ┌─────────────────────┐      ┌──────────────────────────────┐  │
│  │  apps/web (Vite)    │──┬──▶│ apps/api (FastAPI)           │  │
│  │  React · TS · D3    │  │   │ /health · /presets           │  │
│  │  Recharts · KaTeX   │  │   │ /simulate · /simulate/stream │  │
│  └─────────────────────┘  │   └──────────────────────────────┘  │
│           │                │                                     │
│           │ Pyodide        │  REST + SSE                         │
│           ▼                ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ packages/titirilquen_core (Python)                         │ │
│  │ supply · demand · equilibrium · emissions · presets        │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Decisiones clave

### Un solo paquete Python, dos runtimes

`titirilquen_core` es un paquete Python puro (numpy + pydantic + scipy). Se
reutiliza tal cual en:

- **FastAPI** (`apps/api`): instalado en el venv del servidor
- **Pyodide** (navegador): el mismo wheel se sirve como asset estático desde
  `apps/web/public/pyodide/titirilquen_core-*.whl` y `micropip` lo instala en
  el worker

Beneficio: un solo camino de tests, un solo código matemático.

### Streaming de iteraciones

El endpoint `POST /simulate/stream` emite eventos SSE; Pyodide hace lo mismo
mediante `postMessage` desde el worker. El frontend consume ambos con la
misma función `onIteration(snap) => void`.

Esto permite mostrar en vivo la convergencia del MSA.

### Estado → archivo / URL

El `SimulationConfig` completo es serializable (Pydantic) y:
- **Export**: archivo `.ttrq.json` con `$schema: "titirilquen-scenario/v1"`
- **Share**: base64url en `?s=` — sin DB, sin backend obligatorio

### i18n sin build step

`react-i18next` carga JSON estáticos por namespace. Las ecuaciones LaTeX son
independientes del idioma (se renderizan con KaTeX, que no traduce).

## Flujo de una simulación

1. Usuario ajusta parámetros → `SimulationConfig` cambia (Zustand)
2. Click "Simular" → según `engine`:
   - `api`: `fetch` SSE a `/simulate/stream`
   - `local`: `postMessage` al worker Pyodide
3. Cada iteración llega al store vía `pushIteration(snap)`
4. Vistas (CityStrip, FlowProfile, ConvergenceTrace) se rerender reactivamente
5. Al terminar: `finishRun(result)` guarda el trace completo (incluye agentes)

## Módulos frontend

| Carpeta | Propósito |
|---|---|
| `src/components/ui/` | Primitivas (LabeledSlider, Section, PresetSelector) |
| `src/components/modules/` | CityBuilder · SupplyBuilder · DemandInspector |
| `src/components/viz/` | BPRCurve · FlowProfile · UtilityBreakdown · ConvergenceTrace · ModeShareByLocation |
| `src/pages/` | Tutorial · Sandbox · Compare |
| `src/lib/` | api (REST) · pyodide-engine · utility (espejo TS) · serialization |
| `src/store/` | Zustand — config + engine + live iterations |
| `src/workers/` | pyodide.worker.ts (web worker) |
| `src/i18n/` | ES/EN, namespaces `common` y `simulator` |

## Extender con V2 (uso de suelo)

El paquete `titirilquen_core.land_use` (a crear) envolverá `Ciudad2.py`.
El loop de equilibrio pasaría a ser anidado:

```
repeat:
  uso_de_suelo(T) → distribución de hogares
  repeat:
    transporte() → nuevos T_{auto,metro,bici}
  until MSA converge
until redistribución converja
```

El frontend añadiría un módulo `LandUseBuilder` análogo a los actuales.
