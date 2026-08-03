# Titirilquen Web

Simulador educativo de transporte urbano sobre una **ciudad lineal monocéntrica**, orientado a la enseñanza universitaria de modelos de oferta y demanda de transporte.

Proyecto hermano de [`titirilquen-repo`](../titirilquen-repo) (implementación Streamlit original de Sebastian Acevedo, Pablo Alvarez, Fernando Castillo, Angelo Guevara).

## Arquitectura

```
titirilquen-web/
├── apps/
│   ├── web/              Vite + React 18 + TypeScript (frontend)
│   └── api/              FastAPI (backend opcional)
├── packages/
│   └── titirilquen_core/ Núcleo científico Python (compartido por Pyodide y API)
└── docs/                 Documentación viva (discrepancias, modelo, tutoriales)
```

**Dos motores de cómputo, una sola fuente de verdad** (`titirilquen_core`):

- **Pyodide** (en el navegador) — ideal para aula sin servidor
- **FastAPI** (servidor) — ideal para simulaciones grandes o persistencia

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | Vite · React 18 · TypeScript · Tailwind · shadcn/ui |
| Visualización | D3.js · Recharts · KaTeX |
| Estado | Zustand · i18next (ES/EN) · MDX |
| Backend | FastAPI · Pydantic v2 · NumPy |
| Navegador | Pyodide (mismo paquete Python) |
| Persistencia | Archivo `.ttrq.json` + URL-encoded state |

## Requisitos

- Node.js ≥ 20, npm ≥ 10
- Python ≥ 3.11 (solo para el backend opcional y los tests del núcleo; el
  frontend corre el mismo núcleo en el navegador vía Pyodide)

## Inicio rápido

```bash
npm install
npm run dev
```

> El gestor de paquetes del monorepo es **npm** (hay `package-lock.json` y los
> scripts raíz usan `npm --workspace`). No uses pnpm ni yarn.

## Documentación

- [`docs/DISCREPANCIES.md`](docs/DISCREPANCIES.md) — Divergencias código↔Overleaf
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Diseño y decisiones
- [`docs/MATHEMATICAL_MODEL.md`](docs/MATHEMATICAL_MODEL.md) — Fuente única del modelo matemático

## Licencia

**GNU General Public License v3.0 or later** — ver [`LICENSE`](LICENSE).

Heredada del [repositorio original](https://github.com/lehyt2163/Titirilquen) por
la cláusula copyleft de GPL. Ver [`NOTICE.md`](NOTICE.md) para la atribución
completa a los autores originales.
