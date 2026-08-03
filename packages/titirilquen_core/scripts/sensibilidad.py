"""Verificación reproducible de la sensibilidad de la oferta de auto.

Barre densidad x num_pistas y reporta el reparto modal del auto y el v/c del
corredor. Evidencia de docs/ANALISIS_SENSIBILIDAD.md (S-01/S-03) y test de
regresión manual: con la escala liviana (500 hab/km) la BPR del auto no muerde
(Δpp < 0.5 entre 1 y 6 pistas); con la escala del preset Base (1800 hab/km)
sí (Δpp > 1.5, v/c > 0.8).

Correr desde packages/titirilquen_core:

    uv run python scripts/sensibilidad.py

Nota de equivalencia: usa `run_msa` con densidad plana (ruta core). La app usa
`iter_msa_desde_suelo` con ΣH = densidad·largo de LandUseConfig — misma escala
de población, distinta localización inicial; los v/c difieren en ~5%.
"""

from __future__ import annotations

import sys

from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    PhysicalPenalties,
    SimulationConfig,
    StratumBetas,
    StratumConfig,
    SupplyConfig,
)
from titirilquen_core.equilibrium.msa import run_msa

DENSIDADES = (500.0, 1800.0)
PISTAS = (1, 2, 3, 4, 5, 6)

# Espejo de los betas de apps/web/src/lib/defaults.ts (baseBetas). El core no
# trae defaults de demanda; para reproducir lo que ve el usuario hay que
# replicarlos aquí. Si defaults.ts cambia, actualizar este bloque.
_BETAS_UI = {
    1: {
        "prob_teletrabajo": 0.4,
        "prob_auto": 0.9,
        "asc_auto": 1.5,
        "asc_metro": -0.2,
        "asc_bici": -0.9,
        "asc_caminata": -0.5,
        "b_tiempo_viaje": -0.055,
        "b_costo": -0.00008,
        "b_tiempo_espera": -0.05,
        "b_tiempo_caminata": -0.15,
        "penal": {
            "bici_10": -0.09,
            "bici_20": -0.15,
            "bici_30": -0.5,
            "walk_5": -0.09,
            "walk_15": -0.18,
            "walk_25": -0.4,
        },
    },
    2: {
        "prob_teletrabajo": 0.2,
        "prob_auto": 0.6,
        "asc_auto": 0.7889,
        "asc_metro": 0.104,
        "asc_bici": -0.6818,
        "asc_caminata": 0.1,
        "b_tiempo_viaje": -0.0331,
        "b_costo": -0.0002,
        "b_tiempo_espera": -0.0243,
        "b_tiempo_caminata": -0.044,
        "penal": {
            "bici_10": -0.0634,
            "bici_20": -0.1,
            "bici_30": -0.4,
            "walk_5": -0.05,
            "walk_15": -0.09,
            "walk_25": -0.2,
        },
    },
    3: {
        "prob_teletrabajo": 0.05,
        "prob_auto": 0.3,
        "asc_auto": 0.2,
        "asc_metro": 0.25,
        "asc_bici": -0.4,
        "asc_caminata": 0.4,
        "b_tiempo_viaje": -0.015,
        "b_costo": -0.0006,
        "b_tiempo_espera": -0.015,
        "b_tiempo_caminata": -0.025,
        "penal": {
            "bici_10": -0.03,
            "bici_20": -0.05,
            "bici_30": -0.7,
            "walk_5": -0.025,
            "walk_15": -0.04,
            "walk_25": -0.08,
        },
    },
}


def _demanda_ui() -> DemandConfig:
    estratos = {}
    for h, b in _BETAS_UI.items():
        estratos[h] = StratumConfig(
            prob_teletrabajo=b["prob_teletrabajo"],
            prob_auto=b["prob_auto"],
            betas=StratumBetas(
                asc_auto=b["asc_auto"],
                asc_metro=b["asc_metro"],
                asc_bici=b["asc_bici"],
                asc_caminata=b["asc_caminata"],
                b_tiempo_viaje=b["b_tiempo_viaje"],
                b_costo=b["b_costo"],
                b_tiempo_espera=b["b_tiempo_espera"],
                b_tiempo_caminata=b["b_tiempo_caminata"],
                penalizaciones_fisicas=PhysicalPenalties(**b["penal"]),
            ),
        )
    return DemandConfig(estratos=estratos)


def _config(densidad: float, pistas: int) -> SimulationConfig:
    """Config con los defaults que ve el usuario de la web (no los del core):
    201 celdas, 20 km, expected, tolerancia 0.1, seed fija."""
    cfg = SimulationConfig(
        city=CityConfig(n_celdas=201, largo_ciudad_km=20, densidad_hab_km=densidad),
        supply=SupplyConfig(),
        demand=_demanda_ui(),
        max_iter=20,
        tolerance=0.1,
        seed=42,
        assignment="expected",
    )
    return cfg.model_copy(
        update={
            "supply": cfg.supply.model_copy(
                update={"car": cfg.supply.car.model_copy(update={"num_pistas": pistas})}
            ),
        }
    )


def _fila(densidad: float, pistas: int) -> dict:
    trace = run_msa(_config(densidad, pistas))
    last = trace.iteraciones[-1]
    total = sum(last.modal_split.values())
    pct_auto = 100.0 * last.modal_split.get("Auto", 0) / total
    assert trace.flujos_auto_veh_h is not None
    vc = float(trace.flujos_auto_veh_h.max()) / trace.capacidad_auto
    return {
        "densidad": densidad,
        "pistas": pistas,
        "pct_auto": pct_auto,
        "vc": vc,
        "t_auto_max": float(last.t_auto.max()),
        "convergio": trace.converged,
    }


def main() -> int:
    filas = [_fila(d, p) for d in DENSIDADES for p in PISTAS]

    print("| densidad (hab/km) | pistas | % auto | v/c corredor | t_auto máx (min) | convergió |")
    print("|---|---|---|---|---|---|")
    for f in filas:
        print(
            f"| {f['densidad']:.0f} | {f['pistas']} | {f['pct_auto']:.2f} "
            f"| {f['vc']:.2f} | {f['t_auto_max']:.1f} | {'sí' if f['convergio'] else 'NO'} |"
        )

    ok = True
    for d in DENSIDADES:
        sub = [f for f in filas if f["densidad"] == d]
        delta_pp = max(f["pct_auto"] for f in sub) - min(f["pct_auto"] for f in sub)
        vc_1pista = next(f["vc"] for f in sub if f["pistas"] == 1)
        print(
            f"\ndensidad {d:.0f}: Δ% auto (pistas 1→6) = {delta_pp:.2f} pp"
            f" · v/c con 1 pista = {vc_1pista:.2f}"
        )
        if d == 500.0 and delta_pp >= 0.5:
            print("  FALLO: con 500 hab/km la oferta no debería mover el reparto (Δpp < 0.5)")
            ok = False
        if d == 1800.0 and (delta_pp <= 1.5 or vc_1pista <= 0.8):
            print("  FALLO: con 1800 hab/km la BPR debería morder (Δpp > 1.5 y v/c > 0.8)")
            ok = False

    print(
        "\nOK: sensibilidad conforme a lo esperado" if ok else "\nFALLO en los umbrales esperados"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
