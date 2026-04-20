# Deploy

Dos piezas desplegables independientes:

- **`apps/web`** → Vercel (estático Vite)
- **`apps/api`** → Fly.io (FastAPI en contenedor)

El frontend funciona **sin backend** gracias a Pyodide — para una clase sin
servidor, basta con desplegar el web a Vercel o GitHub Pages.

## Frontend a Vercel

### Opción A — CLI

```bash
cd apps/web
npm install -g vercel
vercel          # primer deploy, configura el proyecto
vercel --prod   # deploy a producción
```

Vercel detecta `vercel.json` y ejecuta `npm run build:core-wheel && npm run build`. El wheel de `titirilquen_core` se compila durante el build (requiere Python en el runner — Vercel lo tiene disponible por defecto en imágenes recientes).

> ⚠️ Si Vercel no tiene Python disponible, pre-compila el wheel localmente y comitéalo:
> ```bash
> cd apps/web && npm run build:core-wheel
> git add public/pyodide/*.whl && git commit -m "chore: pin core wheel"
> ```
> y cambia `buildCommand` a sólo `npm run build`.

### Opción B — Import desde GitHub

1. En Vercel Dashboard → New Project → Importar el repo.
2. Root Directory: `apps/web`.
3. Build command: `npm run build:core-wheel && npm run build` (o sólo `npm run build` si pre-compilaste).
4. Output Directory: `dist`.
5. Environment Variables:
   - `VITE_API_BASE` = URL de tu API en Fly.io (ej: `https://titirilquen-api.fly.dev`). Déjalo vacío si sólo quieres el motor local (Pyodide).

## Backend a Fly.io

```bash
cd apps/api
fly launch --no-deploy          # crea la app si no existe
fly deploy --dockerfile Dockerfile --config fly.toml
```

El `fly.toml` tiene `auto_stop_machines = "stop"` y `min_machines_running = 0` para que no consuma cuando nadie la usa (suspende a ~1 min inactiva, despierta en ~2s).

### CORS

`apps/api/src/api/main.py` incluye orígenes `localhost:5173` y `localhost:4173` por defecto. Añade el dominio de producción de Vercel:

```python
allow_origins=[
    "http://localhost:5173",
    "http://localhost:4173",
    "https://titirilquen.vercel.app",
]
```

O usar una variable de entorno para no hardcodear.

## Despliegue 100% estático (GitHub Pages)

Sin backend, sólo Pyodide:

```bash
cd apps/web
npm run build:core-wheel
VITE_API_BASE="disabled" npm run build
# Publica `dist/` en gh-pages
```

En el UI, oculta/deshabilita el toggle "FastAPI" cuando `VITE_API_BASE=disabled`.

## Limitaciones conocidas

- **Pyodide tarda 10–20s en el primer load** (descarga numpy, scipy, pydantic). Cachea agresivamente — ver headers en `vercel.json`.
- **Simulaciones con `n_celdas ≥ 1001` y densidad alta** tardan varios segundos en Pyodide (single-threaded). Para aulas grandes, preferir FastAPI.
- **Health check de Fly.io** usa `/health` (ya implementado).
