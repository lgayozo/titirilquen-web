# Titirilquen Web — Documento de continuidad

> Documento de handoff para retomar el trabajo desde otra máquina o tras una pausa.
> Captura decisiones, estado actual, y lo que queda por hacer.

## 1. Qué es esto

**Titirilquen** es un simulador educativo de transporte urbano sobre una **ciudad lineal monocéntrica**, pensado para enseñanza universitaria. Implementa:

- **Modelos de oferta**: BPR + Greenshields (auto), BPR + pendiente (bici), sistema cíclico con frecuencia endógena (metro).
- **Modelo de demanda**: logit multinomial con 3 estratos socioeconómicos, utilidad descompuesta por modo.
- **Equilibrio**: Método de Promedios Sucesivos (MSA).
- **Uso de suelo** (V2): Alonso-Muth-Mills monocéntrico, con loop acoplado suelo↔transporte.

**Autores del modelo original**: Sebastian Acevedo, Pablo Alvarez, Fernando Castillo, Angelo Guevara (Facultad de Ciencias Físicas y Matemáticas, Universidad de Chile).

**Repositorio fuente del modelo (Streamlit)**: `github.com/lehyt2163/Titirilquen`

**Este repositorio**: re-implementación moderna React/FastAPI con foco en UX académica.

## 2. Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                         titirilquen-web                          │
│                                                                  │
│  ┌─────────────────────┐      ┌──────────────────────────────┐  │
│  │  apps/web (Vite)    │──┬──▶│ apps/api (FastAPI)           │  │
│  │  React · TS · D3    │  │   │ /simulate /coupled           │  │
│  │  Recharts · KaTeX   │  │   │ SSE streaming                │  │
│  │  Pyodide worker     │  │   └──────────────────────────────┘  │
│  └─────────────────────┘  │                                     │
│           │               │   REST + SSE                        │
│           ▼               ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ packages/titirilquen_core (Python puro)                    │ │
│  │ supply · demand · equilibrium · land_use · emissions       │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**Stack**:

| Capa | Tecnología |
|---|---|
| Frontend | Vite 5 · React 18 · TypeScript · Tailwind · Zustand · react-router |
| Tutorials | MDX (`@mdx-js/rollup`) · KaTeX · remark-math/gfm/frontmatter |
| Visualización | D3.js · Recharts · SVG nativo |
| Compute cliente | Pyodide 0.26 (Web Worker) — mismo wheel Python que el API |
| Backend | FastAPI · Pydantic v2 · NumPy · SciPy |
| Persistencia | `.ttrq.json` import/export + URL-encoded state (`?s=<b64>`) |
| i18n | `react-i18next` ES/EN con namespaces `common` y `simulator` |
| Deploy | Vercel (web) · Fly.io (api) · GH Pages (Pyodide-only) |

## 3. Decisiones clave (cronológicas)

| # | Decisión | Por qué |
|---|---|---|
| D1 | **Código es fuente de verdad** ante divergencias con el Overleaf | El código original funciona; el Overleaf tiene typos. Ver [`docs/DISCREPANCIES.md`](docs/DISCREPANCIES.md). |
| D2 | **Monorepo con npm workspaces** (no pnpm) | Corepack requería admin en la máquina del usuario. Npm funciona sin privilegios elevados. `pnpm-workspace.yaml` permanece por compatibilidad futura. |
| D3 | **Un solo paquete Python** (`titirilquen_core`) reutilizable | Evita duplicar matemática entre cliente y servidor. El mismo `.whl` se instala en FastAPI y se sirve a Pyodide. |
| D4 | **Dos motores de cómputo intercambiables**: FastAPI (servidor) y Pyodide (navegador) | FastAPI para simulaciones grandes, Pyodide para aulas sin infra. Toggle en UI. |
| D5 | **V1 sólo transporte; V2 añade uso de suelo** | Scope V1 manejable. V2 introduce `LandUseCity` y loop acoplado sin modificar V1. |
| D6 | **Persistencia por archivo `.ttrq.json` + URL-state** (no DB) | Evita complejidad de backend stateful. Los escenarios son compartibles por link. |
| D7 | **i18n ES/EN desde el inicio** con namespaces | Uso académico en Chile + publicable internacionalmente. |
| D8 | **darkMode: "class"** en Tailwind con toggle manual | Usuario puede forzar light/dark/system. Se persiste en `localStorage`. |
| D9 | **Streaming (SSE/postMessage) para iteraciones** | UX viva: el residuo y modal split se ven convergiendo en tiempo real en lugar de bloquear 20-30s. |
| D10 | **MDX real para tutoriales** (no TSX hardcoded) | Contenido editable por no-programadores (académicos). Cada sección es un chunk lazy-loaded. |
| D11 | **ExportableFigure con inlining de computed styles** | Los SVG exportados preservan colores/estilos Tailwind para uso en clases (LaTeX/Word). |
| D12 | **Accesibilidad desde V4** | Skip link, ARIA completo, `prefers-reduced-motion`, sliders con `aria-valuetext`. |

## 4. Estructura de directorios

```
titirilquen-web/
├── apps/
│   ├── api/                       FastAPI + Dockerfile + fly.toml
│   │   ├── src/api/main.py        Endpoints: /simulate /coupled /land-use
│   │   ├── src/api/serialization.py
│   │   └── tests/
│   └── web/                       Vite + React
│       ├── src/
│       │   ├── assets/fcfm.png    Logo Universidad de Chile
│       │   ├── components/
│       │   │   ├── CityStrip.tsx  Visualización lineal de la ciudad
│       │   │   ├── LanguageSwitcher.tsx
│       │   │   ├── ThemeSwitcher.tsx
│       │   │   ├── ScenarioToolbar.tsx  Import/Export/Share
│       │   │   ├── RootLayout.tsx
│       │   │   ├── Equation.tsx   KaTeX wrapper
│       │   │   ├── compare/       ScenarioCard · KPITable · FlowComparison
│       │   │   ├── modules/       CityBuilder · SupplyBuilder · DemandInspector · LandUseBuilder
│       │   │   ├── ui/            Section · LabeledSlider · PresetSelector · ExportableFigure
│       │   │   └── viz/           BPRCurve · FlowProfile · UtilityBreakdown · ConvergenceTrace
│       │   │                      · ModeShareByLocation · StratumDistribution · BidPriceCurve
│       │   │                      · OuterTrajectory
│       │   ├── pages/
│       │   │   ├── TutorialPage.tsx     Lee MDX con TOC + prev/next
│       │   │   ├── SandboxPage.tsx      App principal
│       │   │   ├── LandUsePage.tsx      V2: uso de suelo + loop acoplado
│       │   │   └── ComparePage.tsx      Slots comparativos + KPIs con deltas
│       │   ├── tutorials/
│       │   │   ├── components.tsx       Callout · NextStep · DocLink + mapping MDX
│       │   │   ├── manifest.ts          import.meta.glob para lazy-load
│       │   │   ├── es/01..06-*.mdx      6 secciones en español
│       │   │   └── en/01..06-*.mdx      6 secciones en inglés
│       │   ├── workers/pyodide.worker.ts  Web Worker con Pyodide + core wheel
│       │   ├── lib/
│       │   │   ├── api.ts               Cliente REST V1
│       │   │   ├── api-v2.ts            Cliente V2 (land-use + coupled + stream)
│       │   │   ├── pyodide-engine.ts    Wrapper del worker
│       │   │   ├── utility.ts           Espejo TS de calcular_utilidades (para live preview)
│       │   │   ├── theme.ts             light/dark/system helpers
│       │   │   ├── svg-export.ts        Serialización SVG + PNG
│       │   │   ├── serialization.ts     .ttrq.json import/export + URL-state
│       │   │   ├── types.ts             V1 types (espejo Pydantic)
│       │   │   ├── types-v2.ts          V2 types (LandUse + Coupled)
│       │   │   ├── presets.ts           Presets de ciudad/política
│       │   │   ├── defaults.ts          Config inicial del simulador
│       │   │   ├── kpis.ts              Cálculo de KPIs para Compare
│       │   │   └── cn.ts                Utility Tailwind
│       │   ├── store/                   Zustand stores
│       │   │   ├── simulationStore.ts   V1
│       │   │   ├── landUseStore.ts      V2
│       │   │   ├── compareStore.ts      Compare
│       │   │   └── themeStore.ts        Light/dark/system
│       │   ├── i18n/
│       │   │   ├── index.ts
│       │   │   └── locales/{es,en}/{common,simulator}.json  ~130 claves × 2 idiomas
│       │   ├── main.tsx                 Entry + router + theme bootstrap
│       │   ├── index.css                Tailwind + focus-visible + reduced-motion
│       │   └── mdx.d.ts                 Tipos MDX
│       ├── public/
│       │   └── pyodide/titirilquen_core-*.whl  Wheel servido al navegador
│       ├── scripts/build-core-wheel.mjs Compila el wheel para Pyodide
│       ├── vite.config.ts               Plugins MDX + manualChunks
│       ├── tailwind.config.js           darkMode: "class"
│       └── vercel.json                  Rewrites + cache headers
├── packages/
│   └── titirilquen_core/          Python puro (27 tests)
│       ├── src/titirilquen_core/
│       │   ├── city.py            CiudadLineal
│       │   ├── config.py          Pydantic schemas (fuente única)
│       │   ├── population.py      Generador de agentes (sintético o desde uso de suelo)
│       │   ├── presets.py         Presets de ciudad/política
│       │   ├── emissions.py       CO2 por velocidad local
│       │   ├── coupled.py         Loop acoplado suelo↔transporte (run_coupled + iter_coupled)
│       │   ├── supply/{bike,car,train}.py
│       │   ├── demand/{utility,choice}.py
│       │   ├── equilibrium/msa.py MSA + iter_msa (streaming)
│       │   └── land_use/
│       │       ├── config.py
│       │       ├── ciudad.py      LandUseCity
│       │       ├── equilibrium.py solve_logit + solve_frechet
│       │       ├── allocation.py  asignar_hogares_simple
│       │       └── supply.py      generar_oferta_normal
│       └── tests/
└── docs/
    ├── DISCREPANCIES.md           11 discrepancias código↔Overleaf
    ├── ARCHITECTURE.md            Diagrama y decisiones de diseño
    └── DEPLOY.md                  Guía Vercel + Fly.io + GH Pages
```

## 5. Cómo correr localmente

### Prerequisitos

- **Node.js ≥ 20**
- **Python ≥ 3.11**
- **npm** (viene con Node)

### Setup desde cero (máquina nueva)

```bash
# 1. Clonar
git clone <url-del-repo>
cd titirilquen-web

# 2. Instalar dependencias frontend
npm install

# 3. Instalar paquetes Python en modo editable
python -m pip install -e "packages/titirilquen_core[dev]"
python -m pip install -e "apps/api[dev]"

# 4. Compilar el wheel Pyodide (se guarda en apps/web/public/pyodide/)
npm run build:core-wheel --workspace @titirilquen/web

# 5. (Opcional) Clonar el repo original de referencia
git clone https://github.com/lehyt2163/Titirilquen.git ../titirilquen-repo
```

### Dev servers

```bash
# Terminal 1 — API
cd apps/api
uvicorn api.main:app --reload --port 8001

# Terminal 2 — Web
cd apps/web
VITE_API_BASE=http://127.0.0.1:8001 npm run dev
# → http://localhost:5173
```

### Tests

```bash
# Python core
cd packages/titirilquen_core && python -m pytest -q
# → 27 tests

# API
cd apps/api && python -m pytest -q
# → 6 tests

# Frontend typecheck
cd apps/web && npx tsc --noEmit

# Frontend build (verifica bundle)
cd apps/web && npm run build
```

## 6. Resumen de los modelos

### Oferta

- **Auto** — Greenshields para capacidad por pista + BPR con congestión.
- **Bicicleta** — BPR con ajuste por pendiente (dos velocidades distintas según el lado del CBD).
- **Metro** — Sistema cíclico con frecuencia endógena dimensionada al tramo crítico, tiempo de espera con penalización si la estación satura.

### Demanda

Logit multinomial con utilidad descompuesta:

```
V_m^s = ASC_m^s + β_t^s·T + β_c^s·C + Σ 1{T>τ_k}·π_k^s
```

Penalizaciones `π_k` son **aditivas escalonadas**, no multiplicativas (ver D-02).

### Equilibrio MSA

```
T^(n+1) = f_n · T_obs^(n) + (1 − f_n) · T^(n),   f_n = 1/(n+1)
```

### Uso de suelo (V2)

Alonso-Muth-Mills: fixed point logit sobre utilidades normalizadas `ū`, deriva precios `p` y probabilidades de subasta `Q[h, i]`. Hogares se asignan a parcelas respetando `Q` y `S`.

### Loop acoplado

```
for outer = 1..N:
    población = generar_desde_land_use(city)
    transport_trace = run_msa(config, población)
    T_new[h,i] = media de tiempos de viaje por (estrato, celda)
    city.update(T_new)
    if ||ΔT|| < tol: break
```

### Discrepancias con el Overleaf

Ver [`docs/DISCREPANCIES.md`](docs/DISCREPANCIES.md). Principales:

- **D-01**: factor pendiente bici `0.9992` en código vs `0.09992` (typo) en Overleaf.
- **D-02**: penalizaciones bici/caminata aditivas escalonadas, no multiplicativas.
- **D-03**: caminata usa `b_tiempo_caminata`, no `b_tiempo_viaje`.
- **D-05**: caminata habilitada en código (Overleaf decía deshabilitada).
- **D-06**: módulo de emisiones no documentado en Overleaf.
- **D-09**: parámetros hardcodeados en el repo original, expuestos como sliders en V1.
- **D-10**: criterio de convergencia real agregado en V1 (antes sólo `MAX_ITER`).

## 7. Deploy

Tres opciones en [`docs/DEPLOY.md`](docs/DEPLOY.md):

1. **Vercel + Fly.io** (separado): frontend estático en Vercel + API en Fly.io con auto-suspend.
2. **GitHub Pages** (sólo frontend con Pyodide): cero servidor, ideal para aulas sin internet.
3. **Docker**: `apps/api/Dockerfile` produce imagen auto-contenida.

## 8. Estado actual — lo que funciona

- ✅ **V1** (transporte): City Builder, Supply Builder, Demand Inspector, MSA equilibrium, convergence viz, flow profiles, mode share by location, import/export/share.
- ✅ **V2** (uso de suelo): LandUseBuilder, StratumDistribution, BidPriceCurve, modo standalone, modo acoplado con streaming SSE, OuterTrajectory con slider.
- ✅ **V3** (comparación): /compare con hasta 4 slots, KPI table con deltas coloreados, ScenarioFlowComparison overlay.
- ✅ **V4** (pulido): Tutorial MDX real con TOC + prev/next, accesibilidad (ARIA + skip link + reduced-motion + focus-visible), export SVG/PNG por figura, theme switcher light/dark/system.
- ✅ Logo FCFM · Universidad de Chile en header.
- ✅ i18n ES/EN completo (~130 claves × 2 idiomas).
- ✅ Tests: 27 Python core + 6 API, typecheck + build limpios.

## 9. Pendientes / ideas para próximas sesiones

**Técnicas**:

- [ ] Tests E2E con Playwright (la UI creció, conviene snapshot testing)
- [ ] Snapshot de SVG exportados para detectar regresiones visuales
- [ ] Cache de resultados pesados en IndexedDB (Pyodide es lento para n_celdas > 500)
- [ ] CI/CD: GitHub Actions para ejecutar tests + build en cada push
- [ ] Mejorar performance de Pyodide en simulaciones grandes (workers paralelos? WASM threading?)

**Modelo / contenido**:

- [ ] Activar las jornadas laborales (dead-path D-07): elección de hora endógena.
- [ ] Añadir módulo de emisiones a la UI (está en `titirilquen_core.emissions` pero no expuesto).
- [ ] Incluir el solver Frechét en ComparePage para pedagogía (mostrar la divergencia vs logit).
- [ ] Micro-simulador de un agente individual (trazar su decisión paso a paso).

**UX**:

- [ ] Modo presentación (pantalla completa, fuentes grandes, proyector).
- [ ] Panel "¿qué pasaría si…?" con preguntas guiadas antes de simular.
- [ ] Integrar DiscrepanciesViewer en la UI (cargar el MD y mostrarlo).
- [ ] Botón "reset al preset base" cuando el usuario toca parámetros y se pierde.
- [ ] Persistir resultados (no sólo config) por escenario.

**Documentación**:

- [ ] Traducir completo los tutoriales EN (actualmente son resúmenes).
- [ ] Video/GIF de 30s mostrando el flujo completo en el README.

## 10. Cómo continuar con Claude Code en otra máquina

Al abrir este proyecto en otra máquina con Claude Code instalado:

1. **Clonar el repo** (asumimos que vas a pushear a GitHub primero — ver sección 11).
2. **Leer este archivo primero**: `cat HANDOFF.md` o abrir en editor.
3. **Referenciar memorias previas**: si usas Claude Code, las memorias globales viven en `~/.claude/` y no viajan con el repo. En la sesión nueva, puedes arrancar diciendo algo como:
   > "Estoy retomando el proyecto Titirilquen. Lee `HANDOFF.md` en la raíz. El código es fuente de verdad sobre el Overleaf. Quiero seguir con [X]."
4. **Estado mínimo viable**: con sólo clonar el repo + seguir la sección 5 tienes ambiente de desarrollo.

**Memorias útiles que tenías en la máquina anterior** (si quieres replicarlas en la nueva):

```
~/.claude/projects/<project-hash>/memory/titirilquen_project.md
```

Contiene contexto del proyecto que puedes copiar manualmente o dejar que Claude reconstruya leyendo este HANDOFF.md.

## 11. Setup para pushear a GitHub

Desde la raíz del monorepo:

```bash
cd titirilquen-web

# Inicializar git si aún no lo está
git init
git branch -M main

# Configurar user (una vez)
git config user.name "Tu nombre"
git config user.email "tu@email.com"

# Añadir todo
git add .
git commit -m "Initial commit: Titirilquen Web V1–V4"

# Crear repo en GitHub (vía web o gh CLI)
gh repo create titirilquen-web --private --source=. --remote=origin

# O manualmente:
# git remote add origin https://github.com/<tu-usuario>/titirilquen-web.git

git push -u origin main
```

**Qué NO subir** (ya está en `.gitignore`):

- `node_modules/`
- `apps/web/dist/`
- `apps/web/public/pyodide/*.whl` (se regenera con `npm run build:core-wheel`)
- `**/__pycache__/`, `**/.venv/`, `**/*.egg-info/`
- `.env.local`, `.env.*.local`

**Qué sí subir**:

- Todo el código fuente (`.py`, `.ts`, `.tsx`, `.mdx`, `.json`, `.css`)
- `docs/`
- `package.json`, `pnpm-workspace.yaml`, `tsconfig*.json`
- `pyproject.toml`
- Este `HANDOFF.md`
- `README.md` (raíz + por app)
- `apps/web/src/assets/fcfm.png` (el logo)

## 12. Referencias rápidas

| Archivo | Para qué |
|---|---|
| `docs/DISCREPANCIES.md` | Las 11 divergencias doc↔código |
| `docs/ARCHITECTURE.md` | Diagrama + decisiones de diseño |
| `docs/DEPLOY.md` | Guía de despliegue |
| `packages/titirilquen_core/README.md` | API del núcleo científico |
| `apps/web/README.md` | Estructura frontend |
| `apps/api/README.md` | Endpoints FastAPI |
| `HANDOFF.md` (este archivo) | Documento de continuidad |

---

**Última actualización de este documento**: 2026-04-20

Cualquier cosa no documentada aquí pero relevante, debería añadirse a este archivo en la misma sesión en que se decida, para que futuros yo (o futuros colaboradores) lo encuentren.
