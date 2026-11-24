# Titirilquen Web

Simulador educativo de transporte urbano sobre una **ciudad lineal monocéntrica**, orientado a la enseñanza universitaria de modelos de oferta y demanda de transporte.

Trabajo derivado del simulador [Titirilquen](https://github.com/lehyt2163/Titirilquen) (implementación Streamlit original de Sebastian Acevedo, Pablo Alvarez, Fernando Castillo, Angelo Guevara).

## Arquitectura

```
titirilquen-web/
├── apps/
│   ├── web/              Vite + React 18 + TypeScript (frontend)
│   └── api/              FastAPI (backend opcional)
├── packages/
│   └── titirilquen_core/ Núcleo científico Python (compartido por Pyodide y API)
└── docs/                 Documentación (discrepancias, modelo, auditorías) · archivo/ para lo caduco
```

**Dos motores de cómputo, una sola fuente de verdad** (`titirilquen_core`):

- **Pyodide** (en el navegador) — ideal para aula sin servidor
- **FastAPI** (servidor) — ideal para simulaciones grandes o persistencia

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | Vite · React 18 · TypeScript · Tailwind · Radix UI (primitivas) |
| Visualización | D3.js · Recharts · KaTeX |
| Estado | Zustand · i18next (ES/EN) · MDX |
| Backend | FastAPI · Pydantic v2 · NumPy · SciPy |
| Navegador | Pyodide (mismo paquete Python) |
| Persistencia | Archivo `.ttrq.json` + URL-encoded state |

## Requisitos

- Node.js ≥ 20, npm ≥ 10
- Python ≥ 3.11 y [`uv`](https://docs.astral.sh/uv/) (solo para el backend
  opcional, los tests del núcleo y recompilar el wheel; el frontend corre el
  mismo núcleo en el navegador vía Pyodide)

## Inicio rápido

```bash
npm install
npm run dev
```

> El gestor de paquetes del monorepo es **npm** (hay `package-lock.json` y los
> scripts raíz usan `npm --workspace`). No uses pnpm ni yarn. Del lado de Python
> el gestor es **uv**, único.

**Si tocas `packages/titirilquen_core`**, hay que recompilar el wheel y regenerar
el contrato TypeScript, o el navegador seguirá ejecutando código viejo:

```bash
npm run sync:core --workspace @titirilquen/web
```

## Verificación

```bash
cd packages/titirilquen_core && uv run --extra dev pytest    # núcleo científico
cd apps/web && npm run typecheck && npm run test:e2e:fast    # frontend
```

## Documentación

Vigente:

- [`docs/CONTINUAR.md`](docs/CONTINUAR.md) — **Empieza acá**: estado del proyecto, calibración vigente y qué falta
- [`docs/libro/`](docs/libro/index.html) — **El libro**: un capítulo por módulo con teoría, cotejo contra el código, parámetros, resultados, pruebas, auditorías y discusión. Incluye el mapa navegable del código ([`arquitectura.html`](docs/libro/arquitectura.html))
- [`docs/DISCREPANCIES.md`](docs/DISCREPANCIES.md) — Divergencias código↔Overleaf (`D-xx`), con la justificación de cada una
- [`docs/MATHEMATICAL_MODEL.md`](docs/MATHEMATICAL_MODEL.md) — Fuente única del modelo matemático
- [`docs/ANALISIS_SENSIBILIDAD.md`](docs/ANALISIS_SENSIBILIDAD.md) · [`docs/AUDITORIA_USO_SUELO.md`](docs/AUDITORIA_USO_SUELO.md) — Qué mueve cada parámetro, medido
- [`docs/COMPARACION_ORIGINAL.md`](docs/COMPARACION_ORIGINAL.md) — Contraste con el simulador original
- [`docs/DEPLOY.md`](docs/DEPLOY.md) — Vercel y Fly.io
- [`CLAUDE.md`](CLAUDE.md) — Guía para agentes de código

Los informes en HTML viven ahora dentro del libro
([índice](docs/libro/index.html)), cada uno mapeado al capítulo que lo va a
absorber: [`informe-wardrop.html`](docs/libro/informe-wardrop.html) (auditoría del
método de asignación) ·
[`informe-downs-thomson.html`](docs/libro/informe-downs-thomson.html) ·
[`informe-uso-suelo.html`](docs/libro/informe-uso-suelo.html) ·
[`informe-hev.html`](docs/libro/informe-hev.html) ·
[`hev-cuadratura.html`](docs/libro/hev-cuadratura.html) ·
[`informe-bienestar.html`](docs/libro/informe-bienestar.html) ·
[`diagrama-flujo.html`](docs/libro/diagrama-flujo.html). Varios narran unidades
anteriores a D-34; el índice del libro lo advierte.

[`docs/archivo/`](docs/archivo/) guarda los documentos caducos, cada uno con una
nota al inicio que dice por qué caducó y qué lo reemplaza.

## Licencia

**GNU General Public License v3.0 or later** — ver [`LICENSE`](LICENSE).

Heredada del [repositorio original](https://github.com/lehyt2163/Titirilquen) por
la cláusula copyleft de GPL. Ver [`NOTICE.md`](NOTICE.md) para la atribución
completa a los autores originales.
