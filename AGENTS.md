# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Qué es

Simulador educativo de transporte urbano sobre una **ciudad lineal monocéntrica** (modelos de oferta, demanda y equilibrio). Monorepo con un único núcleo científico en Python que corre en **dos runtimes**: FastAPI (servidor) y Pyodide (navegador). El frontend funciona sin backend gracias a Pyodide.

Idioma del código y la documentación: **español** (comentarios, docs, mensajes de commit). Mantén esa convención.

## Estructura (workspaces)

- `apps/web/` — frontend Vite + React 18 + TypeScript (`@titirilquen/web`)
- `apps/api/` — wrapper FastAPI opcional (`titirilquen_api`)
- `packages/titirilquen_core/` — núcleo científico Python (oferta · demanda · equilibrio · uso de suelo · emisiones)

## Comandos

Gestor de paquetes JS: **npm** (hay `package-lock.json`; el `README` menciona pnpm pero los scripts raíz usan `npm --workspace`). Node ≥ 20, Python ≥ 3.11.

Desde la raíz:
- `npm run dev` — levanta el frontend (delegado a `@titirilquen/web`)
- `npm run build` / `npm run typecheck` — sobre todos los workspaces
- `npm run format` — Prettier

Desde `apps/web/`:
- `npm run dev` — Vite en `:5173`; proxea `/api` → `http://localhost:8000`
- `npm run build` — `tsc -b && vite build`
- `npm run build:core-wheel` — recompila el wheel de `titirilquen_core` en `public/pyodide/` (ver gotcha abajo)
- `npm run lint` — ESLint · `npm run typecheck` — `tsc --noEmit` · `npm run preview`

Python (`packages/titirilquen_core/` y `apps/api/`):
- Tests: `pytest` (configurado con `testpaths = ["tests"]` en el core)
- Un solo test: `pytest tests/test_demand.py::test_logit -q`
- Lint/format: `ruff` · tipos del core: `mypy`
- El API instala el core como dependencia editable (`[tool.uv.sources]`).

Frontend E2E (Playwright, en `apps/web/`):
- `npm run test:e2e` — toda la suite (levanta Vite solo) · `npm run test:e2e:fast` — excluye `@slow` · `npm run test:e2e:ui` — modo UI
- Specs en `apps/web/e2e/`. El test `@slow` (`simulation.spec.ts`) corre el MSA real en Pyodide y necesita red (CDN); el resto es determinista y rápido.
- No hay tests unitarios/de componente todavía.

## Arquitectura

**Un núcleo Python, dos motores.** `titirilquen_core` es Python puro (numpy · scipy · pydantic). Se reutiliza idéntico en:
- **FastAPI** (`apps/api`): instalado en el venv del servidor.
- **Pyodide** (navegador): el **mismo wheel** se sirve como asset estático desde `apps/web/public/pyodide/titirilquen_core-*.whl` y `micropip` lo instala en un Web Worker (`apps/web/src/workers/pyodide.worker.ts`).

**Abstracción de motor.** Los stores no saben qué motor corre detrás. `engine: "api" | "local"` (default `"local"`) elige entre:
- `src/lib/api.ts` / `api-v2.ts` — REST + SSE contra FastAPI (`/simulate`, `/simulate/stream`, `/land-use/solve`, `/coupled/*`).
- `src/lib/pyodide-engine.ts` — wrapper sobre el worker, con la **misma firma** (`simulateStream(config, onIteration)`).

Ambos emiten una iteración a la vez (SSE en el server, `postMessage` en el worker) para mostrar **en vivo** la convergencia del MSA. El flujo: ajuste de parámetros → `SimulationConfig` (Zustand) → `startRun` → `pushIteration(snap)` por iteración → `finishRun(result)`.

**Estado serializable.** `SimulationConfig` es Pydantic en Python y tiene un **espejo TS escrito a mano** en `src/lib/types.ts` / `types-v2.ts`; la lógica de utilidad/serialización está duplicada en `src/lib/utility.ts` + `serialization.ts` y en `apps/api/src/api/serialization.py`. Export a archivo `.ttrq.json` y share por `?s=` (base64url), sin DB.

**Frontend.** React Router (`createBrowserRouter` en `src/main.tsx`) con `RootLayout` y páginas: Tutorial (`/`, `/tutorial`, `/tutorial/:slug`), Sandbox, LandUse, Coupled, Compare, About. Estado con Zustand (`src/store/`). Estilos Tailwind 3 + primitivas tipo shadcn (Radix + `class-variance-authority`). Visualizaciones en `src/components/viz/` (Recharts + D3); ecuaciones con KaTeX. Alias `@` → `src/`.

**i18n.** `react-i18next`, default `es`, soportados `["es","en"]`, namespaces `common` y `simulator`, recursos importados estáticamente en `src/i18n/index.ts` (sin fetch). Las ecuaciones LaTeX no se traducen.

**Tutoriales = MDX por idioma.** `src/tutorials/{es,en}/NN-*.mdx`, autodescubiertos con `import.meta.glob` (lazy / code-split) y ordenados por el prefijo `NN-`. Para añadir una sección hay que crear el MDX en **ambos** idiomas y agregar la entrada en `TUTORIAL_TOC_ES`/`TUTORIAL_TOC_EN` de `src/tutorials/manifest.ts`.

## Gotchas

- **Tras tocar `titirilquen_core`, recompila el wheel** (`cd apps/web && npm run build:core-wheel`) o el motor Pyodide seguirá ejecutando código viejo. El `dev`/`build` del web no lo regenera solo (en Vercel lo hace el `buildCommand` de `vercel.json`).
- **El núcleo matemático vive solo en Python.** No reimplementes la matemática en TS; los archivos `src/lib/types*.ts`, `utility.ts` y `serialization.ts` son espejos y deben mantenerse en sync con el core y con `api/serialization.py`.
- **Para el motor `api` necesitas la API corriendo** en `:8000` (el proxy de Vite mapea `/api`). Con `VITE_API_BASE="disabled"` el frontend es 100% estático (solo Pyodide).
- Deploy: `apps/web` → Vercel/GitHub Pages, `apps/api` → Fly.io (`/health`). Detalles en `docs/DEPLOY.md`; diseño en `docs/ARCHITECTURE.md`.
- Licencia **GPL-3.0-or-later** (heredada); ver `NOTICE.md` para la atribución a los autores originales.
