# Titirilquen Web — Handoff de continuidad

> Documento para retomar el trabajo desde otra sesión. Captura TODO lo hecho hasta ahora, decisiones arquitectónicas, estado actual del código y qué falta.

---

## 1. Qué es esto

**Titirilquen** es un simulador educativo de transporte urbano sobre **ciudad lineal monocéntrica**, para enseñanza universitaria en FCFM · Universidad de Chile.

- **Autores originales del modelo**: Sebastian Acevedo, Pablo Alvarez, Fernando Castillo, Angelo Guevara.
- **Repo original (Streamlit, GPLv3)**: `github.com/lehyt2163/Titirilquen`
- **Este repo**: `github.com/lgayozo/titirilquen-web` — re-implementación moderna React/FastAPI, también GPLv3 (hereda por copyleft).
- **Usuario**: Leandro Gayozo (`leangayozo@gmail.com`, `@lgayozo`).

## 2. Arquitectura

```
titirilquen-web/                    (monorepo npm workspaces)
├── apps/
│   ├── web/                        Vite + React 18 + TypeScript
│   │   ├── src/
│   │   │   ├── components/         RootLayout, Theme/Lang/Scenario toolbars, RunStatus, SimulationSkeleton
│   │   │   ├── components/ui/      Panel, KPIStrip, SidebarSection, LabeledSlider, PresetSelector, ExportableFigure, Section
│   │   │   ├── components/modules/ CityBuilder, SupplyBuilder, DemandInspector, LandUseBuilder
│   │   │   ├── components/viz/     CityStrip, FlowProfile, ModeShareByLocation, UtilityBreakdown, BPRCurve, ConvergenceTrace, StratumDistribution, BidPriceCurve, OuterTrajectory
│   │   │   ├── components/compare/ ScenarioCard, KPITable, ScenarioFlowComparison
│   │   │   ├── pages/              TutorialPage (MDX loader), SandboxPage, LandUsePage, ComparePage
│   │   │   ├── tutorials/          6 MDX ES + 6 MDX EN + components.tsx (Callout/NextStep/DocLink) + manifest.ts
│   │   │   ├── workers/            pyodide.worker.ts
│   │   │   ├── lib/                api.ts, api-v2.ts, pyodide-engine.ts, utility.ts, types.ts, types-v2.ts, defaults.ts, presets.ts, serialization.ts, svg-export.ts, theme.ts, kpis.ts, cn.ts
│   │   │   ├── store/              simulationStore, landUseStore, compareStore, themeStore (Zustand)
│   │   │   ├── i18n/               ES/EN × {common.json, simulator.json}
│   │   │   ├── assets/             fcfm.png (logo Universidad de Chile)
│   │   │   ├── index.css           Sistema editorial (paper palette, tipografías, animaciones)
│   │   │   └── main.tsx            Router + applyTheme() + expone stores en window.__stores (dev)
│   │   ├── public/pyodide/*.whl   wheel de titirilquen_core para motor Pyodide
│   │   ├── scripts/build-core-wheel.mjs  regenera el wheel
│   │   └── tailwind.config.js      darkMode: ['selector', '[data-theme="dark"]'], paleta editorial
│   └── api/                        FastAPI + uvicorn
│       ├── src/api/main.py         /health /presets /simulate /simulate/stream /land-use/solve /coupled/solve /coupled/stream
│       ├── src/api/serialization.py NumPy→JSON
│       ├── Dockerfile
│       └── fly.toml
└── packages/
    └── titirilquen_core/          Python puro (import desde FastAPI y desde Pyodide)
        ├── src/titirilquen_core/
        │   ├── supply/            bike.py, car.py, train.py
        │   ├── demand/            utility.py, choice.py
        │   ├── equilibrium/msa.py iter_msa() streaming + run_msa()
        │   ├── land_use/          config, supply, allocation, equilibrium (logit + frechet), ciudad
        │   ├── coupled.py         iter_coupled() + run_coupled()
        │   ├── city.py, config.py, population.py, presets.py, emissions.py
        └── tests/                 27 tests
```

## 3. Stack tecnológico

- **Frontend**: Vite 5 + React 18 + TS 5 + Tailwind + KaTeX + Recharts + D3 + Zustand + react-router + react-i18next
- **MDX**: `@mdx-js/rollup` + `@mdx-js/react` + `remark-gfm` + `remark-math` + `rehype-katex` + `remark-frontmatter` + `remark-mdx-frontmatter`
- **Backend**: FastAPI + Pydantic v2 + NumPy + SciPy
- **Navegador**: Pyodide 0.26 (Web Worker) — mismo wheel del core Python
- **Build**: npm workspaces (no pnpm: corepack requiere admin en Windows del usuario)
- **Tests**: pytest (backend), no tests front aún
- **Deploy**: Vercel (web) + Fly.io (API). Archivos listos: `vercel.json`, `Dockerfile`, `fly.toml`.

## 4. Sistema de diseño "editorial paper"

Implementado desde un handoff de Claude Design (`https://api.anthropic.com/v1/design/h/BDbo_Oxds2o71QE3cllyxQ`). Archivos del diseño original descomprimidos en `../design-dump/titirilquen/` (fuera del repo).

### Paleta (tres temas)

Todos los colores via CSS variables en `:root` con variantes `[data-theme="dark"]` y `[data-theme="journal"]`:

| Var | paper (default) | dark | journal |
|---|---|---|---|
| `--paper` | `#f4f1e8` (beige cálido) | `#0e0d0b` | `#fafaf7` |
| `--ink` | `#1a1814` | `#f0ebe0` | `#0a0a0a` |
| `--muted` | `#6b655a` | `#7d7667` | `#6a6a6a` |
| `--rule` | `#c9c2af` | `#2b2822` | `#d4d4d0` |
| `--accent` | `#b2431a` (terracota) | `#e67545` | `#1a4d8f` |
| `--auto` / `--metro` / `--bici` / `--walk` / `--tele` | tonos tierra/sangre/verde/azul/gris | tonos más saturados | tonos sobrios |
| `--s1` / `--s2` / `--s3` | estratos | | |

### Tipografías (Google Fonts, cargadas en index.html)

- **Display**: `Source Serif 4` — títulos (H1 hero, panel titles)
- **Body**: `Inter` — texto
- **Fig/mono**: `JetBrains Mono` — labels, números tabulares, navegación con tracking wide

### Convenciones

- **Radius 0** en todo (estética "periódico impreso")
- Seg controls con border-divider entre botones, `.active` invierte colores
- Panels con `FIG. NN` en accent + título serif + meta mono
- KPI strip 6-col con divisores verticales
- Hint-row 3 cards pedagógicos

## 5. Estado del código por versión

### V1 · Transporte
- Módulos `supply/{bike,car,train}.py` portados verbatim de `app.py` original, con tipado + dataclasses
- `demand/{utility,choice}.py` + `population.py`
- MSA con streaming (`iter_msa`) + criterio de convergencia (antes sólo MAX_ITER)
- FastAPI `POST /simulate` y `POST /simulate/stream` (SSE)
- Pyodide worker con mismo wheel

### V2 · Uso de suelo
- `land_use/{config,supply,equilibrium,allocation,ciudad}.py` — `Ciudad2.py` portado con `solve_logit` + `solve_frechet`
- `coupled.py` — loop acoplado suelo↔transporte con streaming (`iter_coupled`)
- API: `POST /land-use/solve`, `POST /coupled/solve`, `POST /coupled/stream`

### V3 · Comparación
- Página `/compare` con hasta 4 escenarios paralelos
- `KPITable` con deltas coloreados
- `ScenarioFlowComparison` overlay de perfiles
- Persistencia localStorage + import/export `.ttrq.json` + URL-state comprimido

### V4 · Pulido
- Tutorial MDX real ES/EN × 6 secciones + `<Callout>` `<NextStep>` `<DocLink>`
- Accesibilidad: skip link, ARIA, `prefers-reduced-motion`, focus-visible
- Export SVG/PNG de figuras (inline computed styles)
- Theme switcher (paper/dark/journal/system)
- Animaciones: `iteration-flash`, `skeleton-pulse`, `pulse-dot`, CityStrip transitions 400ms
- `RunStatus` (fase textual + barra progreso + modal split en vivo) + `SimulationSkeleton` pre-primera-iter

### Rediseño editorial (Claude Design handoff)
- CSS completo reemplazado con sistema paper/ink (`index.css` ~720 líneas)
- Layout editorial: topbar con logo FCFM + nav underline + seg controls
- Hero con título serif grande + ribbon SVG
- KPI strip 6-col, hint-row 3 cards
- Grid 12-col de Panels con `FIG. NN`
- Footer académico

### Ajustes recientes (sesión actual, antes del reinicio)
1. **Fix scroll sidebar**: `height: 100%` + `overflow-y: auto` + run-btn `position: sticky; bottom: 0`
2. **Sidebar desplegable**: componente `<SidebarSection>` con `<details>`/`<summary>` nativo, muestra meta info al costado (ej. `20 km · 201 celdas`). Aplicado en CityBuilder, SupplyBuilder, LandUseBuilder, SandboxPage (Equilibrium, Engine).
3. **FIG. 2-4 (FlowProfiles) con escala Y compartida**: `yMax` global max entre los 3 modos, no mezcla con capacidad del corredor (unidades distintas); capacidad ahora es pill textual (`capacityHint`), no línea en escala.
4. **FIG. 6 (ModeShareByLocation) normalizado 100%**: colores editoriales, 48 bins, Y-axis labels, gap entre barras, orden apilado Tele→Walk→Bici→Metro→Auto.
5. **FIG. 5 (DemandInspector + UtilityBreakdown)**:
   - Controles en una sola fila: `[Estrato 140-170px] [Origen slider 1fr] [Checkbox auto]`
   - Normalización simétrica: `maxAbsSide = max(sumPos_modo, sumNeg_modo)` → nunca desborda
   - V y P en **misma tipografía mono** (JetBrains Mono tabular): V 12px, P 13px bold
   - Filas compactas 32px, separadores entre filas
   - Grid: `64px modo · 1fr barra · 52px V · 56px P`

## 6. Tests y builds

```
packages/titirilquen_core:  27/27 tests ✓
apps/api:                    6/6 tests ✓
apps/web:                    typecheck limpio
                             vite build OK (~700KB gz ~215KB incluyendo recharts + router)
```

Comandos:
```bash
# Backend (desde apps/api)
python -m pytest -q
uvicorn api.main:app --host 127.0.0.1 --port 8001

# Core (desde packages/titirilquen_core)
python -m pytest -q

# Frontend (desde apps/web)
npx tsc --noEmit
npx vite build
npx vite    # dev en http://localhost:5173
```

## 7. Arranque local

1. **API** (terminal 1): `cd apps/api && uvicorn api.main:app --port 8001`
2. **Web** (terminal 2): `cd apps/web && VITE_API_BASE=http://127.0.0.1:8001 npm run dev`
3. Abre `http://localhost:5173`

Si usas Claude Code preview: ya existe `.claude/launch.json` en la raíz del proyecto con la configuración.

## 8. Git y commits

- Repo: `https://github.com/lgayozo/titirilquen-web` (público, GPLv3)
- Autor de commits: `Leandro Gayozo <leangayozo@gmail.com>`
- Commits llevan `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` (por transparencia)
- Repo NO se commitea automáticamente — cada sesión hay que pushear manualmente cuando se decida. Credenciales: PAT en Git Credential Manager de Windows.

### Archivos ignored
- `node_modules/`, `dist/`, `__pycache__/`, `.venv/`, `*.log`
- `.claude/` (config local de Claude Code preview)

## 9. Lo que falta / próximos pasos sugeridos

Ordenados por valor pedagógico + esfuerzo:

### A. Commit + deploy real (rápido)
1. Commit los cambios de esta sesión con mensaje "Rediseño editorial + ajustes UX sidebar/figuras"
2. Push a GitHub
3. Deploy a Vercel desde el repo (usa `vercel.json` existente, buildCommand ya configurado)
4. Deploy API a Fly.io: `cd apps/api && fly launch --no-deploy && fly deploy`
5. Actualizar CORS en `apps/api/src/api/main.py` con URL pública de Vercel

### B. Contenido didáctico (medio)
- Tutorial MDX aún es genérico — personalizarlo con ejemplos concretos
- Actividades pre-armadas: 5 `.ttrq.json` con preguntas guiadas compartibles via URL-state (Parking, Pro-Bici, Alonso α, etc.)
- Hints-row en Sandbox podrían tener MDX con ecuaciones KaTeX inline

### C. Visualizaciones pendientes del diseño Claude (medio)
El diseño original del handoff (`../design-dump/titirilquen/project/dashboard/charts.jsx`) tiene varias figuras que aún no migré:
- **CityRibbon** stacked areas (mode share por ubicación) — el hero actual usa el `CityStrip` de V1. El diseño tiene una "cinta" con áreas apiladas de auto/metro/bici/walk por km. Es más rica visualmente que el heatmap actual.
- **MetroLoad** con perfil de carga vs capacidad + frecuencia
- **BPRCurve** con operating point (ya existe, pero el original tiene más decoración)
- **Residential** (para V2 uso de suelo — similar a StratumDistribution pero con rent-curve superpuesta)
- **TimesChart** — curvas de tiempo por ubicación (alternativo al heatmap)

### D. Detalles pendientes de UX (bajo)
- **`FIG. 1 Equilibrio alcanzado`** ahora es col-12 con subgráficos de Recharts → debería adoptar estilo SVG custom editorial (Recharts tiene colores slate por default, se ven incongruentes)
- **Panels responsive**: en viewport < 1100px todo pasa a col-12. Probar en mobile.
- **Modo presentación**: full-screen para proyector, con tamaños fuente mayores
- **Share URL long**: el compressed state del scenario puede ser largo. Considerar lz-string para reducir.

### E. Profesionalización (medio-alto)
- **CI GitHub Actions**: workflow que corre `pytest` + `tsc` + `vite build` en cada PR
- **Badges README**: tests passing, license, deploy status
- **Tests frontend**: vitest + testing-library para componentes críticos (CityBuilder, DemandInspector)
- **Snapshots de SVG**: fixtures comparando exportedSVG vs golden para detectar regresiones visuales

### F. V3 matemático (alto)
- Loop acoplado completo con visualización de trayectoria (ya existe OuterTrajectory básico)
- Métrica de bienestar agregado (utilidad media por estrato)
- Sensibilidad paramétrica automática: dado un escenario base, variar α_h ± 20% y plotear respuesta

## 10. Cómo retomar en otra sesión

1. **Lee este archivo** — es la fuente única del contexto
2. Abre el repo: `git clone https://github.com/lgayozo/titirilquen-web && cd titirilquen-web`
3. Ve también `../design-dump/titirilquen/` si existe (archivos del diseño editorial de referencia)
4. `npm install` + instalar Python en `packages/titirilquen_core` y `apps/api` con `pip install -e ".[dev]"`
5. Correr tests para verificar que todo verde: `pytest` en cada paquete + `npx tsc --noEmit` + `npx vite build`
6. Usar los stores expuestos en `window.__stores` (dev only) para debug rápido desde consola del navegador

### Atajos útiles en la consola dev
```js
// Cambiar theme
window.__stores.simulation.getState()  // ver config actual
document.documentElement.dataset.theme = 'dark'  // paper / dark / journal

// Cargar preset policy
window.__stores.simulation.getState().replaceConfig({ ...configBase, /* policy overrides */ })
```

## 11. Decisiones arquitectónicas registradas

Para evitar revisitar estas decisiones en otra sesión:

1. **Un solo paquete Python** (`titirilquen_core`) reutilizado por FastAPI Y Pyodide → una fuente de verdad matemática.
2. **npm workspaces, NO pnpm** — corepack requería admin en Windows del usuario. `pnpm-workspace.yaml` existe por compatibilidad pero `npm install` es el path bendecido.
3. **CSS variables para theming**, `data-theme` en `<html>` — NO class `.dark` de Tailwind porque hay 3 temas.
4. **Tailwind `darkMode: ['selector', '[data-theme="dark"]']`** — así los utilities `dark:` funcionan con nuestro sistema de data-theme.
5. **Código original es fuente de verdad** sobre el Overleaf ante discrepancias. Ver `docs/DISCREPANCIES.md` (11 casos documentados: D-01 a D-11).
6. **V1 sólo transporte**, V2 añade uso de suelo con feature flag implícito (toggle en LandUsePage).
7. **i18n ES/EN** con namespaces `common` y `simulator`. Texto académico/ecuaciones en MDX son independientes del idioma (KaTeX no traduce).
8. **Persistencia sin DB**: `.ttrq.json` drag-drop + URL-encoded state + localStorage para temas y escenarios guardados.
9. **Logo FCFM preservado** en topbar (no se eliminó con el rediseño editorial).
10. **Animaciones preservadas** durante rediseño: `iteration-flash` en CityStrip, `skeleton-pulse` en SimulationSkeleton, `pulse-dot` en hero status, transitions 400ms en barras del CityStrip.

---

**Última actualización**: sesión del 2026-04-23, justo antes de reinicio de contexto por llegada al 90%.

**Próximo movimiento recomendado para arrancar la próxima sesión**:
> Commit los cambios actuales ("Rediseño editorial + fixes FIG. 5/6 + sidebar desplegable") y push a GitHub. Luego seguir con **A. Deploy real** para tener URL pública.
