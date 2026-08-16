"""TEST PROVISIONAL — muere en la fase F2, cuando haya un solo serializador.

Hoy la forma del resultado está escrita DOS veces: acá en
`api/serialization.py` y otra vez como texto Python dentro de un string de
`apps/web/src/workers/pyodide.worker.ts`. Ese segundo no lo revisa ninguna
herramienta —ni ruff, ni mypy, ni pytest, ni el typecheck de TS— y por eso
divergieron sin que nadie se enterara: a `trace_to_dict` le faltaba
`demanda_estrato`, y con el motor `api` el frontend mostraba todos los KPIs de
bienestar en cero.

Este test copia a mano la lista de claves del worker para cerrar el hueco
mientras tanto. Es deliberadamente tonto y desechable: la solución de verdad es
que ambos importen la misma función del core, y entonces este archivo se borra.
"""

from __future__ import annotations

from api.serialization import iteration_to_dict, trace_to_dict
from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa
from titirilquen_core.presets import DEFAULT_STRATA

#: Claves que emite `_trace_to_py` en pyodide.worker.ts (verificado a mano el
#: 2026-08-15). Si el worker cambia, esta lista hay que moverla — o mejor,
#: llegar a F2 y borrar el archivo.
CLAVES_TRACE_WORKER = {
    "converged",
    "capacidad_auto",
    "v_libre_auto",
    "alpha_auto_bpr",
    "beta_auto_bpr",
    "carga_metro",
    "estaciones_km",
    "flujos_auto_veh_h",
    "flujos_bici_veh_h",
    "emisiones_total_kg",
    "emisiones_auto_kg",
    "emisiones_metro_kg",
    "emisiones_perfil_kg",
    "demanda_estrato",
    "iteraciones",
    "agentes",
}

#: Ídem para `_snap_to_py`.
CLAVES_SNAPSHOT_WORKER = {
    "iter",
    "f_msa",
    "modal_split",
    "demanda_auto",
    "demanda_metro",
    "demanda_bici",
    "demanda_caminata",
    "t_auto",
    "t_bici",
    "t_tren_acceso",
    "t_tren_espera",
    "t_tren_viaje",
    "frecuencia_metro",
    "frecuencia_teorica_metro",
    "residuo",
}


def _trace_chico() -> ConvergenceTrace:
    cfg = SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=10, densidad_hab_km=400),
        supply=SupplyConfig(),
        demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}),
        max_iter=2,
        seed=7,
        assignment="expected",
    )
    trace = ConvergenceTrace()
    for _ in iter_msa(cfg, trace):
        pass
    return trace


def test_trace_emite_las_mismas_claves_que_el_worker() -> None:
    obtenidas = set(trace_to_dict(_trace_chico()))
    assert obtenidas == CLAVES_TRACE_WORKER, (
        "los dos serializadores divergieron.\n"
        f"  solo en la API:    {sorted(obtenidas - CLAVES_TRACE_WORKER)}\n"
        f"  solo en el worker: {sorted(CLAVES_TRACE_WORKER - obtenidas)}"
    )


def test_snapshot_emite_las_mismas_claves_que_el_worker() -> None:
    obtenidas = set(iteration_to_dict(_trace_chico().iteraciones[0]))
    assert obtenidas == CLAVES_SNAPSHOT_WORKER


def test_demanda_estrato_llega_con_forma_de_cubo() -> None:
    """La regresión concreta: 3 estratos x 4 modos x n_celdas, no `None`."""
    demanda = trace_to_dict(_trace_chico())["demanda_estrato"]
    assert demanda is not None, "sin esto, agregados.ts devuelve bienestar 0"
    assert len(demanda) == 3
    assert len(demanda[0]) == 4
    assert len(demanda[0][0]) == 51
