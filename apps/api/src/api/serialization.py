"""Serialización de resultados del núcleo a JSON.

Los dataclasses de `titirilquen_core` contienen `numpy.ndarray` que no son
JSON-serializables por defecto. Esta capa convierte a listas de Python.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from titirilquen_core.coupled import CoupledResult, OuterIteration
from titirilquen_core.equilibrium.msa import ConvergenceTrace, IterationSnapshot
from titirilquen_core.land_use.equilibrium import LandUseResult


def _to_list(arr: np.ndarray | None) -> list[float] | None:
    if arr is None:
        return None
    return arr.tolist()


def iteration_to_dict(snap: IterationSnapshot) -> dict[str, Any]:
    return {
        "iter": snap.iter,
        "f_msa": snap.f_msa,
        "modal_split": snap.modal_split,
        "demanda_auto": _to_list(snap.demanda_auto),
        "demanda_metro": _to_list(snap.demanda_metro),
        "demanda_bici": _to_list(snap.demanda_bici),
        "t_auto": _to_list(snap.t_auto),
        "t_bici": _to_list(snap.t_bici),
        "t_tren_acceso": _to_list(snap.t_tren_acceso),
        "t_tren_espera": _to_list(snap.t_tren_espera),
        "t_tren_viaje": _to_list(snap.t_tren_viaje),
        "frecuencia_metro": snap.frecuencia_metro,
        "residuo": snap.residuo if snap.residuo != float("inf") else None,
    }


def land_use_result_to_dict(res: LandUseResult) -> dict[str, Any]:
    return {
        "u": res.u.tolist(),
        "p": res.p.tolist(),
        "Q": res.Q.tolist(),
        "converged": res.converged,
        "iterations": res.iterations,
    }


def outer_iteration_to_dict(outer: OuterIteration) -> dict[str, Any]:
    return {
        "outer_iter": outer.outer_iter,
        "land_use": land_use_result_to_dict(outer.land_use),
        "transport": trace_to_dict(outer.transport),
        "T_matrix": outer.T_matrix.tolist(),
        "T_residual": None if outer.T_residual == float("inf") else outer.T_residual,
    }


def coupled_result_to_dict(res: CoupledResult) -> dict[str, Any]:
    return {
        "converged": res.converged,
        "iterations": [outer_iteration_to_dict(it) for it in res.iterations],
        "final_parcelas": (
            res.final_city.parcelas if res.final_city is not None else []
        ),
        "S": _to_list(
            np.asarray(res.final_city.S) if res.final_city is not None else None
        ),
    }


def trace_to_dict(trace: ConvergenceTrace) -> dict[str, Any]:
    return {
        "converged": trace.converged,
        "capacidad_auto": trace.capacidad_auto,
        "v_libre_auto": trace.v_libre_auto,
        "alpha_auto_bpr": trace.alpha_auto_bpr,
        "beta_auto_bpr": trace.beta_auto_bpr,
        "carga_metro": _to_list(trace.carga_metro),
        "estaciones_km": _to_list(trace.estaciones_km),
        "iteraciones": [iteration_to_dict(s) for s in trace.iteraciones],
        "agentes": [
            {
                "id": a.id,
                "celda_origen": a.celda_origen,
                "estrato": a.estrato,
                "teletrabaja": a.teletrabaja,
                "tiene_auto": a.tiene_auto,
                "modo_elegido": a.modo_elegido,
                "utilidad_elegida": a.utilidad_elegida,
            }
            for a in trace.agentes
        ],
    }
