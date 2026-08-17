# CLAUDE.md

Guía para agentes de código (Claude Code, Codex y equivalentes) que trabajen en
este repositorio. Es el documento **canónico**: `AGENTS.md` sólo apunta acá.

## Qué es

Simulador educativo de transporte urbano sobre una **ciudad lineal monocéntrica**
(modelos de oferta, demanda y equilibrio). Monorepo con un único núcleo
científico en Python que corre en **dos runtimes**: FastAPI (servidor) y Pyodide
(navegador). El frontend funciona sin backend gracias a Pyodide.

Idioma del código y la documentación: **español** (comentarios, docs, mensajes de
commit). Mantén esa convención.

## Comandos

Gestor de paquetes JS: **npm** (hay `package-lock.json` y los scripts raíz usan
`npm --workspace`). No uses pnpm ni yarn. Gestor de Python: **uv**, único — no
uses `pip install` ni crees venvs a mano.

```bash
npm run dev                                                  # frontend (Pyodide, sin backend)
cd packages/titirilquen_core && uv run --extra dev pytest    # 105 tests del núcleo
cd apps/web && npm run typecheck && npm run test:e2e:fast    # 58 e2e
npm run format:check                                         # prettier, desde la raíz
```

E2E con Playwright, specs en `apps/web/e2e/`: `test:e2e` corre la suite completa,
`test:e2e:fast` excluye `@slow` y `test:e2e:ui` abre el modo interactivo. El test
`@slow` (`simulation.spec.ts`) corre el MSA real en Pyodide y necesita red (CDN);
el resto es determinista y rápido. No hay tests unitarios/de componente del
frontend: la red que protege la matemática es pytest, y la que protege el
contrato Python↔TS son los goldens de `contract.spec.ts`.

## Arquitectura

**Un núcleo Python, dos motores.** `titirilquen_core` es Python puro (numpy ·
scipy · pydantic). Se reutiliza idéntico en:

- **FastAPI** (`apps/api`): instalado en el venv del servidor.
- **Pyodide** (navegador): el **mismo wheel** se sirve como asset estático desde
  `apps/web/public/pyodide/titirilquen_core-0.2.0-py3-none-any.whl` y `micropip`
  lo instala en un Web Worker (`apps/web/src/workers/pyodide.worker.ts`).

**Una sola puerta al motor.** Ninguna página decide contra qué motor corre:
`src/lib/api.ts` es el único punto de entrada y encapsula
`engine: "api" | "local"` (default `"local"`). Expone `simularTransporte`,
`resolverUsoDeSuelo`, `resolverAcoplado` y `resolverAcopladoStream`. Detrás:
REST + SSE contra FastAPI (`/simulate`, `/land-use/solve`, `/coupled/*`) o
`src/lib/pyodide-engine.ts` sobre el worker. No llames al worker directo desde
una página.

Ambos motores emiten una iteración a la vez (SSE en el server, `postMessage` en
el worker) para mostrar **en vivo** la convergencia del MSA. El flujo: ajuste de
parámetros → `SimulationConfig` (Zustand) → `startRun` → `pushIteration(snap)`
por iteración → `finishRun(result)`.

**El contrato Python→TS es generado, no escrito a mano.**
`packages/titirilquen_core/tools/genera_contrato.py` emite
`apps/web/src/lib/gen/*.gen.ts` (tipos, defaults, presets, constantes y la forma
del trace) desde el schema Pydantic y los `TypedDict` del núcleo. **No edites
`src/lib/gen/`**: se sobreescribe. `types.ts`, `defaults.ts` y `presets.ts` son
shims que re-exportan de ahí. Las divergencias **intencionales** entre el default
del núcleo y el de la web viven declaradas y comentadas en `src/lib/overrides.ts`.

**La forma JSON es una sola.** `titirilquen_core/serializacion.py` produce los
diccionarios que consumen tanto FastAPI como el worker; `bienestar.py` calcula
los agregados de bienestar. Esa lógica ya no está duplicada en TypeScript.

**Lo que sigue siendo espejo.** `src/lib/utility.ts` reimplementa el cálculo de
utilidad para el inspector didáctico (necesita ser síncrono). Es el único espejo
que queda, y está pineado con `e2e/fixtures/utility-golden.json`: si divergen, el
test falla. Lo mismo `citySupply.ts` con su golden de oferta.

**Estado serializable.** Export a archivo `.ttrq.json` (`$schema:
"titirilquen-scenario/v3"`) y share por `?s=` (base64url), sin DB. No hay
migraciones: un archivo de un schema anterior falla con un error explícito.

**i18n.** Las ecuaciones LaTeX no se traducen. Ojo al borrar claves: varias se
construyen por interpolación (`` t(`equilibrium.modo_${m.toLowerCase()}`) ``), así
que un grep de la clave literal da cero y **miente**.

**Tutoriales = MDX por idioma.** `src/tutorials/{es,en}/NN-*.mdx`, autodescubiertos
con `import.meta.glob` (lazy / code-split) y ordenados por el prefijo `NN-`. Para
añadir una sección hay que crear el MDX en **ambos** idiomas y agregar la entrada
en `TUTORIAL_TOC_ES`/`TUTORIAL_TOC_EN` de `src/tutorials/manifest.ts`.

## Gotchas

- **Tras tocar `titirilquen_core`, corre `npm run sync:core --workspace @titirilquen/web`.**
  Recompila el wheel, regenera `src/lib/gen/` y los goldens. Si no lo haces,
  Pyodide sigue ejecutando código viejo. **Nadie lo hace por ti**: ni el `dev`,
  ni el `build`, ni Vercel (su `buildCommand` es `npm run build` a secas). El
  wheel va versionado en el repo justamente por eso. El CI tiene un job
  (`contrato`) que corre `sync:core` y falla si el diff no está vacío.
- **La línea base es la red de seguridad de la matemática.** La corrida por
  defecto de la app da **auto 16,95 · metro 32,79 · bici 22,84 · caminata 7,98**
  (seed 42, tol 0,1) y está pineada en `tests/test_linea_base.py`. Si un cambio
  la mueve más de 0,1 pp, no era refactor: es un cambio de modelo. Decláralo.
- **El piso de pydantic del núcleo es `>=2.7` y no se puede subir.** Pyodide
  0.26.4 trae pydantic 2.7.0 precompilado; pedir `>=2.8` hace que `micropip`
  aborte con `already installed` y el motor por defecto deja de arrancar. Ningún
  test lo detecta: todos corren en CPython.
- **El núcleo matemático vive solo en Python.** No reimplementes la matemática en
  TS. Si necesitas un número nuevo en la UI, calcúlalo en el núcleo y expóntelo
  por `serializacion.py`.
- **Para el motor `api` necesitas la API corriendo** en `:8000` (el proxy de Vite
  mapea `/api`). Con `VITE_API_BASE="disabled"` el frontend es 100% estático
  (sólo Pyodide). Ojo: por la ruta `/simulate` la población es la de densidad
  plana, porque ese endpoint no recibe uso de suelo (C-02, anotado en `api.ts`).
- Deploy: `apps/web` → Vercel/GitHub Pages, `apps/api` → Fly.io (`/health`).
  Detalles en `docs/DEPLOY.md`; el mapa del código en `docs/arquitectura.html`.
- Licencia **GPL-3.0-or-later** (heredada); ver `NOTICE.md` para la atribución a
  los autores originales.
