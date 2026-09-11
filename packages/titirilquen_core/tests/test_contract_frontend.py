"""Contrato core ↔ frontend (Fase 5, anti-drift).

Los fixtures golden en `apps/web/e2e/fixtures/` pinean el comportamiento del
core que el frontend espeja (formas de oferta en `citySupply.ts`) y los
defaults Pydantic que `defaults.ts` debe seguir (salvo divergencias
intencionales listadas en `e2e/contract.spec.ts`).

- Si ESTOS tests fallan: el core cambió → regenerar los fixtures (script al
  final de este archivo) y revisar que el spec TS siga pasando.
- Si el SPEC TS falla con fixtures vigentes: el espejo TS driftó → corregirlo.

Regenerar:  uv run --extra dev python tests/test_contract_frontend.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    GlobalConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.supply import generar_oferta
from titirilquen_core.presets import DEFAULT_STRATA

FIXTURES = Path(__file__).resolve().parents[3] / "apps" / "web" / "e2e" / "fixtures"

SUPPLY_CASES = [
    (L, CBD, N, sigma, param)
    for L, CBD, N, sigma, param in [
        (201, 100, 10000, 0.5, 0.5),
        (101, 50, 5000, 0.32, 0.3),
        (201, 100, 10000, 0.85, 0.7),
    ]
]
FORMAS = ("normal", "uniforme", "exponencial", "meseta", "bimodal", "valle")


def _supply_cases() -> list[dict]:
    cases = []
    for forma in FORMAS:
        for L, CBD, N, sigma, param in SUPPLY_CASES:
            S = generar_oferta(forma=forma, I=L, N=N, CBD=CBD, sigma_frac=sigma, forma_param=param)
            cases.append(
                {
                    "forma": forma,
                    "L": L,
                    "CBD": CBD,
                    "N": N,
                    "sigma_frac": sigma,
                    "forma_param": param,
                    "S": [int(x) for x in S],
                }
            )
    return cases


def _defaults() -> dict:
    sim_fields = {
        k: f.default
        for k, f in SimulationConfig.model_fields.items()
        if k in ("max_iter", "tolerance", "seed", "assignment", "modos_habilitados")
    }
    return {
        "city": CityConfig().model_dump(),
        "supply": SupplyConfig().model_dump(),
        "globales": GlobalConfig().model_dump(),
        "sim": sim_fields,
        "land_use": LandUseConfig().model_dump(by_alias=True),
    }


def _load(name: str) -> dict:
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f"fixture {name} no disponible (paquete fuera del monorepo)")
    return json.loads(path.read_text(encoding="utf-8"))


def test_supply_golden_vigente() -> None:
    """El core reproduce el fixture golden de las formas de oferta. Si falla,
    el core cambió: regenerar el fixture y verificar el espejo TS."""
    golden = _load("supply-golden.json")["cases"]
    live = _supply_cases()
    assert len(golden) == len(live)
    for g, vivo in zip(golden, live, strict=True):
        assert g == vivo, f"forma={vivo['forma']} L={vivo['L']} σ={vivo['sigma_frac']}"


def test_defaults_golden_vigente() -> None:
    """Los defaults Pydantic coinciden con el fixture golden (lado Python del
    contrato de paridad con defaults.ts)."""
    golden = _load("defaults-golden.json")["defaults"]
    live = json.loads(json.dumps(_defaults(), default=list))
    assert live == golden


# ---------------------------------------------------------------------------
# Utilidad: el último espejo de LÓGICA que queda en el frontend
# ---------------------------------------------------------------------------
#
# `lib/utility.ts` reimplementa `demand/utility.py` a mano. No se pudo eliminar
# como los demás espejos: el inspector de utilidad se redibuja mientras el
# usuario mueve un slider, y cruzar al worker de Pyodide por cada movimiento
# significaría rondas asíncronas y un estado de "motor cargando" en un widget
# didáctico. Se protege pineando la función.
#
# La rejilla busca los bordes, no el caso feliz: distancias a ambos lados de
# los cortes de factibilidad (caminata 30 min ≈ 2,4 km; bici 45 min ≈ 10,5 km),
# con y sin auto, y una celda pegada al CBD donde el metro no tiene tramo en
# tren y queda infactible.

UTILIDAD_CASOS = [
    # (celda, tiene_auto) sobre una ciudad de 201 celdas / 20 km: el CBD es la
    # 100, así que la celda 100 está a 0 km y la 0 a 10 km.
    (100, True),
    (99, True),
    (95, False),
    (88, True),
    (88, False),
    (75, True),
    (60, False),
    (30, True),
    (0, False),
]


def _utilidad_casos() -> list[dict]:
    ciudad = CiudadLineal(n_celdas=201, largo_total_km=20)
    demanda = DemandConfig.model_validate({"estratos": DEFAULT_STRATA})
    casos = []
    for celda, tiene_auto in UTILIDAD_CASOS:
        dist_km = abs(ciudad.cbd_index - celda) * ciudad.ancho_celda_km
        # Tiempos plausibles para esa distancia, con algo de congestión en el
        # auto y una espera de metro típica del default (f_op ≈ 6 tph).
        tiempos = TiemposObservados(
            auto_total=dist_km * 2.4 + 2,
            bici_total=dist_km * 4.3,
            tren_acceso=6.0,
            tren_espera=5.0,
            tren_viaje=dist_km * 1.7,
        )
        for estrato in (1, 2, 3):
            utils = calcular_utilidades(
                estrato=estrato,
                celda_origen=celda,
                tiene_auto=tiene_auto,
                ciudad=ciudad,
                config=demanda,
                tiempos_observados=tiempos,
            )
            casos.append(
                {
                    "estrato": estrato,
                    "celda": celda,
                    "dist_km": dist_km,
                    "tiene_auto": tiene_auto,
                    "tiempos": {
                        "auto_total": tiempos.auto_total,
                        "bici_total": tiempos.bici_total,
                        "tren_acceso": tiempos.tren_acceso,
                        "tren_espera": tiempos.tren_espera,
                        "tren_viaje": tiempos.tren_viaje,
                    },
                    "utilidades": {
                        modo: {"valor": u.valor, "feasible": u.feasible}
                        for modo, u in utils.items()
                    },
                }
            )
    return casos


def test_utilidad_golden_vigente() -> None:
    """El core reproduce el fixture de utilidades. Si falla, la función de
    utilidad cambió: regenerar y verificar que el espejo TS la siga."""
    golden = _load("utility-golden.json")["cases"]
    live = json.loads(json.dumps(_utilidad_casos()))
    assert len(golden) == len(live)
    for g, vivo in zip(golden, live, strict=True):
        assert g == vivo, (
            f"estrato={vivo['estrato']} celda={vivo['celda']} auto={vivo['tiene_auto']}"
        )


if __name__ == "__main__":
    # Regenera los fixtures (correr tras un cambio DELIBERADO del core).
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / "supply-golden.json").write_text(
        json.dumps(
            {
                "_": "Generado por el core Python (fuente de verdad). NO editar a mano; "
                "regenerar con: uv run --extra dev python tests/test_contract_frontend.py",
                "cases": _supply_cases(),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    (FIXTURES / "utility-golden.json").write_text(
        json.dumps(
            {
                "_": "Generado por el core Python (fuente de verdad). NO editar a mano; "
                "regenerar con: npm run sync:core",
                "cases": _utilidad_casos(),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    (FIXTURES / "defaults-golden.json").write_text(
        json.dumps(
            {"_": "Defaults Pydantic del core. NO editar a mano.", "defaults": _defaults()},
            indent=1,
            default=list,
        )
        + "\n",
        encoding="utf-8",
    )
    print("fixtures regenerados en", FIXTURES)
