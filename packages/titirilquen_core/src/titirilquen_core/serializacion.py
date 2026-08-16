"""Forma JSON de los resultados del núcleo — **la única**.

Los dataclasses del core llevan `numpy.ndarray`, que no es JSON-serializable.
Esta capa los convierte a listas de Python, y define con `TypedDict` la forma
exacta de cada objeto que cruza al frontend.

Por qué vive en el core y no en la API
--------------------------------------
Este contrato lo consumen **dos runtimes**: el servidor FastAPI y el worker de
Pyodide dentro del navegador. Hasta agosto de 2026 estaba escrito dos veces —
una en `apps/api/src/api/serialization.py` y otra como texto Python embebido en
un string de `apps/web/src/workers/pyodide.worker.ts`. Esa segunda copia no la
revisaba **ninguna** herramienta: ni ruff, ni mypy, ni pytest, ni el typecheck
de TypeScript.

Divergieron, por supuesto. A `trace_to_dict` le faltaba `demanda_estrato`, así
que con `engine="api"` el frontend recibía `undefined` y mostraba todos los KPI
de bienestar en cero, sin error visible. Poner la función acá es lo que hace
que esa clase de bug deje de ser posible: ambos importan lo mismo.

Los `TypedDict` no son decorativos. Son la fuente desde la que se generan los
tipos TypeScript del trace, porque los dataclasses del core no son modelos
Pydantic y no emiten JSON Schema por sí solos.
"""

from __future__ import annotations

from typing import Any, TypedDict

import numpy as np

from titirilquen_core.config import ModoElegido
from titirilquen_core.coupled import CoupledResult, OuterIteration
from titirilquen_core.coupled_metrics import equilibrium_metrics_to_dict
from titirilquen_core.equilibrium.msa import ConvergenceTrace, IterationSnapshot
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.equilibrium import LandUseResult

# ---------------------------------------------------------------------------
# La forma del contrato
# ---------------------------------------------------------------------------


class AgenteDict(TypedDict):
    """Un viajero, tal como lo ve el frontend."""

    id: int
    celda_origen: int
    estrato: int
    teletrabaja: bool
    tiene_auto: bool
    #: `None` para un agente varado: ninguno de sus modos resultó factible.
    modo_elegido: ModoElegido | None
    #: Nunca falta — arranca en 0.0 y el teletrabajador se queda en 0.0.
    utilidad_elegida: float


class SnapshotDict(TypedDict):
    """Estado de la red al final de una iteración del MSA.

    Es lo que viaja *en vivo* mientras la simulación corre: por SSE desde la
    API, por `postMessage` desde el worker.
    """

    iter: int
    f_msa: float
    modal_split: dict[str, float]
    demanda_auto: list[float]
    demanda_metro: list[float]
    demanda_bici: list[float]
    demanda_caminata: list[float]
    t_auto: list[float]
    t_bici: list[float]
    t_tren_acceso: list[float]
    t_tren_espera: list[float]
    t_tren_viaje: list[float]
    frecuencia_metro: float
    frecuencia_teorica_metro: float
    #: `None` en la primera iteración, donde el residuo es infinito.
    residuo: float | None


class TraceDict(TypedDict):
    """Resultado completo de una corrida de transporte."""

    converged: bool
    capacidad_auto: float
    v_libre_auto: float
    alpha_auto_bpr: float
    beta_auto_bpr: float
    carga_metro: list[float] | None
    estaciones_km: list[float] | None
    flujos_auto_veh_h: list[float] | None
    flujos_bici_veh_h: list[float] | None
    emisiones_total_kg: float
    emisiones_auto_kg: float
    emisiones_metro_kg: float
    emisiones_perfil_kg: list[float] | None
    #: Demanda esperada por [estrato, modo, celda] — el cubo que alimenta el
    #: reparto modal espacial por estrato y los agregados de bienestar.
    demanda_estrato: list[list[list[float]]] | None
    iteraciones: list[SnapshotDict]
    agentes: list[AgenteDict]


class LandUseResultDict(TypedDict):
    """Equilibrio de pujas: utilidades, precios y composición por celda."""

    u: list[float]
    p: list[float]
    Q: list[list[float]]
    converged: bool
    iterations: int


class LandUseSolveDict(TypedDict):
    """Respuesta de resolver el uso de suelo aislado (con su geometría)."""

    L: int
    CBD: int
    S: list[int]
    parcelas: Any
    densidad_celda: list[float]
    result: LandUseResultDict


class OuterIterationDict(TypedDict):
    """Una vuelta del loop exterior suelo ↔ transporte."""

    outer_iter: int
    land_use: LandUseResultDict
    transport: TraceDict
    T_matrix: list[list[float]]
    T_residual: float | None
    metrics: dict[str, Any]


class CoupledResultDict(TypedDict):
    """Resultado completo del loop acoplado."""

    converged: bool
    iterations: list[OuterIterationDict]
    final_parcelas: Any
    S: list[int] | None


# ---------------------------------------------------------------------------
# Conversión
# ---------------------------------------------------------------------------


def _lista(arr: np.ndarray | None) -> Any:
    """`tolist()` es recursivo: sirve igual para el perfil 1-D de emisiones que
    para el cubo 3-D de `demanda_estrato`."""
    if arr is None:
        return None
    return arr.tolist()


def _finito(x: float) -> float | None:
    """El residuo arranca en infinito, que no es JSON válido."""
    return None if x == float("inf") else x


def agente_to_dict(a: Any) -> AgenteDict:
    return {
        "id": a.id,
        "celda_origen": a.celda_origen,
        "estrato": a.estrato,
        "teletrabaja": a.teletrabaja,
        "tiene_auto": a.tiene_auto,
        "modo_elegido": a.modo_elegido,
        "utilidad_elegida": a.utilidad_elegida,
    }


def iteration_to_dict(snap: IterationSnapshot) -> SnapshotDict:
    return {
        "iter": snap.iter,
        "f_msa": snap.f_msa,
        "modal_split": snap.modal_split,
        "demanda_auto": _lista(snap.demanda_auto),
        "demanda_metro": _lista(snap.demanda_metro),
        "demanda_bici": _lista(snap.demanda_bici),
        "demanda_caminata": _lista(snap.demanda_caminata),
        "t_auto": _lista(snap.t_auto),
        "t_bici": _lista(snap.t_bici),
        "t_tren_acceso": _lista(snap.t_tren_acceso),
        "t_tren_espera": _lista(snap.t_tren_espera),
        "t_tren_viaje": _lista(snap.t_tren_viaje),
        "frecuencia_metro": snap.frecuencia_metro,
        "frecuencia_teorica_metro": snap.frecuencia_teorica_metro,
        "residuo": _finito(snap.residuo),
    }


def trace_to_dict(trace: ConvergenceTrace) -> TraceDict:
    return {
        "converged": trace.converged,
        "capacidad_auto": trace.capacidad_auto,
        "v_libre_auto": trace.v_libre_auto,
        "alpha_auto_bpr": trace.alpha_auto_bpr,
        "beta_auto_bpr": trace.beta_auto_bpr,
        "carga_metro": _lista(trace.carga_metro),
        "estaciones_km": _lista(trace.estaciones_km),
        "flujos_auto_veh_h": _lista(trace.flujos_auto_veh_h),
        "flujos_bici_veh_h": _lista(trace.flujos_bici_veh_h),
        "emisiones_total_kg": trace.emisiones_total_kg,
        "emisiones_auto_kg": trace.emisiones_auto_kg,
        "emisiones_metro_kg": trace.emisiones_metro_kg,
        "emisiones_perfil_kg": _lista(trace.emisiones_perfil_kg),
        "demanda_estrato": _lista(trace.demanda_estrato),
        "iteraciones": [iteration_to_dict(s) for s in trace.iteraciones],
        "agentes": [agente_to_dict(a) for a in trace.agentes],
    }


def land_use_result_to_dict(res: LandUseResult) -> LandUseResultDict:
    return {
        "u": res.u.tolist(),
        "p": res.p.tolist(),
        "Q": res.Q.tolist(),
        "converged": res.converged,
        "iterations": res.iterations,
    }


def land_use_city_to_dict(city: LandUseCity) -> LandUseSolveDict:
    """La ciudad resuelta con su geometría — respuesta de `/land-use/solve`."""
    assert city.result is not None, "la ciudad no tiene equilibrio resuelto"
    return {
        "L": city.L,
        "CBD": city.cbd_index,
        "S": city.S.tolist(),
        "parcelas": city.parcelas,
        "densidad_celda": city.densidad_por_celda().tolist(),
        "result": land_use_result_to_dict(city.result),
    }


def outer_iteration_to_dict(outer: OuterIteration) -> OuterIterationDict:
    return {
        "outer_iter": outer.outer_iter,
        "land_use": land_use_result_to_dict(outer.land_use),
        "transport": trace_to_dict(outer.transport),
        "T_matrix": outer.T_matrix.tolist(),
        "T_residual": _finito(outer.T_residual),
        "metrics": equilibrium_metrics_to_dict(outer.metrics),
    }


def coupled_result_to_dict(res: CoupledResult) -> CoupledResultDict:
    return {
        "converged": res.converged,
        "iterations": [outer_iteration_to_dict(it) for it in res.iterations],
        "final_parcelas": (res.final_city.parcelas if res.final_city is not None else []),
        "S": _lista(np.asarray(res.final_city.S) if res.final_city is not None else None),
    }
