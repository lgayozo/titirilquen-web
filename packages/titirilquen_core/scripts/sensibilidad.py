"""Verificación reproducible de la sensibilidad de la oferta de auto.

Barre densidad x num_pistas y reporta el reparto modal del auto y el v/c del
corredor. Evidencia de docs/ANALISIS_SENSIBILIDAD.md (S-01/S-03) y test de
regresión manual.

Lo que verifica: **la respuesta del reparto a la oferta vial depende del v/c,
no de la densidad**. Con el corredor descongestionado (v/c < 0.5 con 1 pista)
agregar pistas no mueve el reparto (Δpp < 0.5 entre 1 y 6 pistas); con el
corredor en o sobre capacidad (v/c > 1.0) sí lo mueve (Δpp > 1.5). Entre medio
hay zona gris sin umbral, porque la rodilla de la BPR no tiene un corte nítido.

Las densidades del barrido son solo la forma de LLEGAR a esos regímenes; el
umbral se evalúa contra el v/c medido. Antes estaba atado a densidades fijas y
caducó al recalibrar la motorización (ver el comentario de VC_LIBRE).

Correr desde packages/titirilquen_core:

    uv run python scripts/sensibilidad.py

Nota de equivalencia: usa `run_msa` con densidad plana (ruta core). La app usa
`iter_msa_desde_suelo` con ΣH = densidad·largo de LandUseConfig — misma escala
de población, distinta localización inicial; los v/c difieren en ~5%.
"""

from __future__ import annotations

import sys

from _comun import demanda_ui

from titirilquen_core.config import (
    CityConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.equilibrium.msa import run_msa

DENSIDADES = (200.0, 500.0, 1800.0)
PISTAS = (1, 2, 3, 4, 5, 6)

# El invariante que este script verifica es FÍSICO y depende del v/c, no de la
# densidad: bajo la rodilla de la BPR agregar pistas no mueve el reparto, sobre
# ella sí. Atarlo a "500 hab/km" lo hizo caducar en cuanto cambió la
# calibración: 9854f6d subió la motorización (prob_auto 0,90/0,60/0,30 →
# 0,95/0,75/0,45) y corrió la mezcla de estratos a (0,20/0,50/0,30), con lo que
# esa misma densidad pasó de v/c 0,60 a 0,92 — de flujo libre a la rodilla. El
# umbral marcaba "falla" cuando en realidad la premisa del test había caducado.
#
# Medido (v/c con 1 pista → Δpp entre 1 y 6 pistas): 0,28 → 0,08 · 0,37 → 0,15
# · 0,54 → 0,36 · 0,71 → 0,61 · 0,87 → 0,92 · 2,16 → 5,97. Monótono, que es
# justamente lo que justifica indexar por v/c.
VC_LIBRE = 0.5
"""Bajo este v/c el corredor está descongestionado: la oferta no debería mover
el reparto."""
VC_SATURADO = 1.0
"""Sobre este v/c el corredor opera en o sobre capacidad: la oferta sí debería
moverlo."""
DELTA_PLANO = 0.5
"""pp de %auto entre 1 y 6 pistas que se consideran "no mover el reparto"."""
DELTA_MUERDE = 1.5
"""pp de %auto que se consideran una respuesta clara a la oferta."""

# La calibracion sale de `presets.DEFAULT_STRATA`. Este modulo llego a llevar
# una TERCERA copia de los 42 betas que quedo desincronizada en la
# recalibracion de ago-2026: las auditorias midieron la calibracion vieja sin
# avisar.
#
# Un comentario aca afirmaba que la paridad con el espejo TS estaba "verificada
# por el test de contrato". Era FALSO: el golden solo cubria city, supply,
# globales, sim y land_use — los betas quedaban afuera, que es justo el bloque
# que habia driftado. Desde ago-2026 el lado TS se GENERA desde este mismo
# dict (tools/genera_contrato.py), asi que ya no hay paridad que verificar.


def _config(densidad: float, pistas: int) -> SimulationConfig:
    """Config equivalente a la que ve el usuario de la web:
    201 celdas, 20 km, expected, tolerancia 0.1, seed fija."""
    cfg = SimulationConfig(
        city=CityConfig(n_celdas=201, largo_ciudad_km=20, densidad_hab_km=densidad),
        supply=SupplyConfig(),
        demand=demanda_ui(),
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
    cubre_libre = False
    cubre_saturado = False
    for d in DENSIDADES:
        sub = [f for f in filas if f["densidad"] == d]
        delta_pp = max(f["pct_auto"] for f in sub) - min(f["pct_auto"] for f in sub)
        vc_1pista = next(f["vc"] for f in sub if f["pistas"] == 1)
        print(
            f"\ndensidad {d:.0f}: Δ% auto (pistas 1→6) = {delta_pp:.2f} pp"
            f" · v/c con 1 pista = {vc_1pista:.2f}"
        )
        # El régimen lo decide el v/c MEDIDO, no la densidad con la que se
        # generó: así el test sobrevive a recalibraciones de motorización.
        if vc_1pista < VC_LIBRE:
            cubre_libre = True
            if delta_pp >= DELTA_PLANO:
                print(
                    f"  FALLO: con v/c {vc_1pista:.2f} < {VC_LIBRE} el corredor está libre"
                    f" y la oferta no debería mover el reparto (Δpp < {DELTA_PLANO})"
                )
                ok = False
        elif vc_1pista > VC_SATURADO:
            cubre_saturado = True
            if delta_pp <= DELTA_MUERDE:
                print(
                    f"  FALLO: con v/c {vc_1pista:.2f} > {VC_SATURADO} la BPR debería morder"
                    f" (Δpp > {DELTA_MUERDE})"
                )
                ok = False
        else:
            print(
                f"  (zona gris: {VC_LIBRE} ≤ v/c ≤ {VC_SATURADO}, sin umbral —"
                " la rodilla de la BPR no tiene un corte nítido)"
            )

    # Sin esto el test podría quedar verde sin verificar nada: si una
    # recalibración empuja TODAS las densidades a la zona gris, no se evalúa
    # ningún umbral y el silencio se leería como éxito.
    if not cubre_libre:
        print(
            f"\nFALLO: ninguna densidad del barrido queda bajo v/c {VC_LIBRE};"
            " el régimen de flujo libre dejó de estar cubierto. Bajá DENSIDADES."
        )
        ok = False
    if not cubre_saturado:
        print(
            f"\nFALLO: ninguna densidad del barrido supera v/c {VC_SATURADO};"
            " el régimen saturado dejó de estar cubierto. Subí DENSIDADES."
        )
        ok = False

    print(
        "\nOK: sensibilidad conforme a lo esperado" if ok else "\nFALLO en los umbrales esperados"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
