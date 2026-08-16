"""Entry point FastAPI — capa delgada sobre `titirilquen_core`.

  - GET  /health           chequeo de vida (Fly.io)
  - POST /simulate         equilibrio de transporte, corrida completa
  - POST /land-use/solve   equilibrio de uso de suelo, sin transporte
  - POST /coupled/solve    loop acoplado suelo↔transporte, corrida completa
  - POST /coupled/stream   ídem, SSE con una iteración exterior por evento

La API es OPCIONAL: el frontend corre el mismo núcleo en el navegador vía
Pyodide y ése es su motor por defecto. Estos endpoints existen para el modo
`engine="api"`.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

from titirilquen_core import (
    LandUseCity,
    LandUseConfig,
    SimulationConfig,
    run_coupled,
    run_msa,
)
from titirilquen_core.coupled import iter_coupled

from titirilquen_core.serializacion import (
    coupled_result_to_dict,
    land_use_city_to_dict,
    outer_iteration_to_dict,
    trace_to_dict,
)

app = FastAPI(
    title="Titirilquen API",
    version="0.1.0",
    description="Simulador de transporte educativo — ciudad lineal monocéntrica",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Acá vivían `GET /presets` y `POST /simulate/stream`. Se retiraron por no
# tener clientes: el frontend nunca llamó a `/presets` (usa su propio espejo de
# los presets) y el cliente TS del stream de transporte no se importaba en
# ninguna página. El streaming en vivo del MSA lo hace el worker de Pyodide,
# que es el motor por defecto; con `engine="api"` la comparación de escenarios
# usa `/simulate`, que es bloqueante. Si alguna vez hace falta streaming por
# HTTP, el patrón sigue vivo en `/coupled/stream`.


@app.post("/simulate")
def simulate(config: SimulationConfig) -> dict[str, object]:
    trace = run_msa(config)
    return trace_to_dict(trace)


# ---------------------------------------------------------------------------
# V2: Uso de suelo + loop acoplado suelo↔transporte
# ---------------------------------------------------------------------------


class LandUseOnlyRequest(BaseModel):
    """Request para resolver sólo el uso de suelo (sin transporte)."""

    L: int = Field(default=201, ge=11)
    CBD: int = Field(default=100, ge=0)
    largo_km: float = Field(default=20.0, gt=0, description="Largo físico de la ciudad")
    land_use: LandUseConfig


@app.post("/land-use/solve")
def land_use_solve(req: LandUseOnlyRequest) -> dict[str, object]:
    """Resuelve el equilibrio de uso de suelo con T = tiempo a flujo libre (min)."""
    city = LandUseCity.build(
        L=req.L, CBD=req.CBD, cfg=req.land_use, ancho_celda_km=req.largo_km / req.L
    )
    return land_use_city_to_dict(city)


class CoupledRequest(BaseModel):
    """Request para el loop acoplado suelo↔transporte."""

    sim: SimulationConfig
    land_use: LandUseConfig
    outer_max_iter: int = Field(default=3, ge=1, le=10)
    outer_tol: float = Field(default=1.0, ge=0, description="minutos")


@app.post("/coupled/solve")
def coupled_solve(req: CoupledRequest) -> dict[str, object]:
    """Resuelve el loop acoplado suelo↔transporte.

    Warning: iteraciones exteriores son costosas. Usar `outer_max_iter ≤ 5`
    para feedback razonable en una sesión educativa.
    """
    result = run_coupled(
        sim=req.sim,
        land_use_config=req.land_use,
        outer_max_iter=req.outer_max_iter,
        outer_tol=req.outer_tol,
    )
    return coupled_result_to_dict(result)


@app.post("/coupled/stream")
async def coupled_stream(req: CoupledRequest) -> StreamingResponse:
    """SSE: emite una OuterIteration por evento. Evita bloquear la UI ~30s."""

    async def event_gen() -> AsyncGenerator[str, None]:
        for outer in iter_coupled(
            sim=req.sim,
            land_use_config=req.land_use,
            outer_max_iter=req.outer_max_iter,
            outer_tol=req.outer_tol,
        ):
            payload = outer_iteration_to_dict(outer)
            yield f"data: {json.dumps(payload)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
