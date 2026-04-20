"""Entry point FastAPI.

Dos endpoints:
  - POST /simulate           corrida completa
  - POST /simulate/stream    SSE, una iteración por evento (para UI viva)

Ambos reciben `SimulationConfig` de `titirilquen_core`.
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
from titirilquen_core.equilibrium.msa import iter_msa
from titirilquen_core.presets import CITY_PRESETS, DEFAULT_STRATA, POLICY_PRESETS

from api.serialization import (
    coupled_result_to_dict,
    iteration_to_dict,
    land_use_result_to_dict,
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


@app.get("/presets")
def presets() -> dict[str, object]:
    return {
        "city": CITY_PRESETS,
        "policy": POLICY_PRESETS,
        "strata_default": DEFAULT_STRATA,
    }


@app.post("/simulate")
def simulate(config: SimulationConfig) -> dict[str, object]:
    trace = run_msa(config)
    return trace_to_dict(trace)


@app.post("/simulate/stream")
async def simulate_stream(config: SimulationConfig) -> StreamingResponse:
    async def event_gen() -> AsyncGenerator[str, None]:
        for snap in iter_msa(config):
            payload = iteration_to_dict(snap)
            yield f"data: {json.dumps(payload)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# V2: Uso de suelo + loop acoplado suelo↔transporte
# ---------------------------------------------------------------------------


class LandUseOnlyRequest(BaseModel):
    """Request para resolver sólo el uso de suelo (sin transporte)."""

    L: int = Field(default=201, ge=11)
    CBD: int = Field(default=100, ge=0)
    land_use: LandUseConfig


@app.post("/land-use/solve")
def land_use_solve(req: LandUseOnlyRequest) -> dict[str, object]:
    """Resuelve el equilibrio de uso de suelo con T = distancia al CBD."""
    city = LandUseCity.build(L=req.L, CBD=req.CBD, cfg=req.land_use)
    assert city.result is not None
    return {
        "L": city.L,
        "CBD": city.cbd_index,
        "S": city.S.tolist(),
        "parcelas": city.parcelas,
        "result": land_use_result_to_dict(city.result),
    }


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
