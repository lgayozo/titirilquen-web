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

from titirilquen_core.config import CityConfig, GlobalConfig, SimulationConfig, SupplyConfig
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.supply import generar_oferta

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
    for g, l in zip(golden, live):
        assert g == l, f"forma={l['forma']} L={l['L']} σ={l['sigma_frac']}"


def test_defaults_golden_vigente() -> None:
    """Los defaults Pydantic coinciden con el fixture golden (lado Python del
    contrato de paridad con defaults.ts)."""
    golden = _load("defaults-golden.json")["defaults"]
    live = json.loads(json.dumps(_defaults(), default=list))
    assert live == golden


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
