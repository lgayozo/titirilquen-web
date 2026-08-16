"""Fixtures compartidas de la suite del core.

Dos familias, y conviene no confundirlas:

* `demanda_sintetica` — betas INVENTADOS, chicos y redondos, para tests que
  solo necesitan "una demanda cualquiera". **No son la calibración del
  simulador**: el estrato alto de verdad tiene un valor del tiempo de
  $6.200/h, no estos números redondos.
* `demanda_calibrada` — esa sí, la vigente (`DEFAULT_STRATA`), sin copiarla.

La misma demanda sintética está hoy copiada literal en `test_equilibrium_smoke`,
`test_coupled` y `test_coupled_metrics` (y con otras probabilidades en
`test_demand`). Migrarlos cambia la firma de ~10 tests, así que se hace en la
fase de saneo; estas fixtures existen para que los tests NUEVOS no agreguen una
quinta copia.

La configuración real de la aplicación no vive acá sino en `test_linea_base`,
con sus valores hardcodeados y comentados: es su objeto de estudio, no una
fixture compartida.
"""

from __future__ import annotations

import pytest

from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    PhysicalPenalties,
    SimulationConfig,
    StratumBetas,
    StratumConfig,
    SupplyConfig,
)
from titirilquen_core.presets import DEFAULT_STRATA


def _demanda_sintetica(prob_teletrabajo: float = 0.2, prob_auto: float = 0.6) -> DemandConfig:
    penal = PhysicalPenalties(
        bici_10=-0.09,
        bici_20=-0.15,
        bici_30=-0.5,
        walk_5=-0.09,
        walk_15=-0.18,
        walk_25=-0.4,
    )
    betas = StratumBetas(
        asc_auto=1.5,
        asc_metro=-0.2,
        asc_bici=-0.9,
        asc_caminata=-0.5,
        b_tiempo_viaje=-0.055,
        b_costo=-0.00008,
        b_tiempo_espera=-0.05,
        b_tiempo_acceso=-0.15,
        b_tiempo_caminata=-0.15,
        penalizaciones_fisicas=penal,
    )
    s = StratumConfig(prob_teletrabajo=prob_teletrabajo, prob_auto=prob_auto, betas=betas)
    return DemandConfig(estratos={1: s, 2: s, 3: s})


@pytest.fixture
def demanda_sintetica() -> DemandConfig:
    """Demanda de juguete: los tres estratos idénticos, betas redondos."""
    return _demanda_sintetica()


@pytest.fixture(scope="module")
def demanda_sintetica_modulo() -> DemandConfig:
    """La misma, con alcance de módulo — para fixtures que corren una
    simulación una sola vez y la comparten entre tests."""
    return _demanda_sintetica()


@pytest.fixture
def hacer_demanda_sintetica():
    """La misma, parametrizable — para los tests que mueven las probabilidades."""
    return _demanda_sintetica


@pytest.fixture
def demanda_calibrada() -> DemandConfig:
    """La calibración VIGENTE del simulador (`DEFAULT_STRATA`), no una copia."""
    return DemandConfig.model_validate({"estratos": DEFAULT_STRATA})


@pytest.fixture
def sim_liviana(demanda_sintetica: DemandConfig) -> SimulationConfig:
    """Config chica y rápida: para ejercitar caminos, no para medir números."""
    return SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=10, densidad_hab_km=400),
        supply=SupplyConfig(),
        demand=demanda_sintetica,
        max_iter=3,
        tolerance=0.0,
        seed=7,
    )
