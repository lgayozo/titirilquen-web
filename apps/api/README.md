# titirilquen_api

FastAPI que envuelve `titirilquen_core`. Endpoints:

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/presets` | Presets de ciudad/políticas + estratos por defecto |
| POST | `/simulate` | Corrida completa (JSON con `ConvergenceTrace`) |
| POST | `/simulate/stream` | SSE: una iteración por evento |

## Desarrollo

```bash
pip install -e "[dev]"
uvicorn api.main:app --reload --port 8000
```

Docs OpenAPI automáticas en `http://localhost:8000/docs`.
