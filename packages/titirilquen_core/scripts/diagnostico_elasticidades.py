"""Diagnostico cuantitativo del modulo de transporte.

Responde con numeros tres preguntas de calibracion que la auditoria dejo
abiertas:

1. ELASTICIDADES. Elasticidad arco del reparto modal respecto de precios y de
   oferta, con perturbaciones de +-20% alrededor del default:

       e = (dq / q_medio) / (dp / p_medio)

   Permite contrastar contra los ordenes de magnitud de la literatura y decidir
   si la infraestructura tiene el peso que se espera.

2. BICI. Donde muerde el techo de caminata. El tiempo por tramo es
   `min(BPR, tiempo de caminar el tramo)`, asi que existe un v/c UMBRAL a partir
   del cual la BPR deja de operar y alpha/beta dejan de significar algo:

       t0*(1 + alpha*x^beta) = t_walk   =>   x = ((v_bici/v_caminata - 1)/alpha)^(1/beta)

3. TREN. `capacidad_tren` es el divisor de la frecuencia (f = carga/K), asi que
   subirla BAJA la frecuencia. Se compara contra la politica realista «mas
   capacidad Y mas frecuencia» (subir K y frec_max juntos).

Correr desde packages/titirilquen_core:

    uv run python scripts/diagnostico_elasticidades.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from auditoria_transporte import base_lu, base_sim, corre

from titirilquen_core.config import SimulationConfig

PCT = 0.20  # perturbacion +-20% para la elasticidad arco


def con_glob(s: SimulationConfig, **kw) -> SimulationConfig:
    return s.model_copy(
        update={
            "demand": s.demand.model_copy(
                update={"globales": s.demand.globales.model_copy(update=kw)}
            )
        }
    )


def con_car(s: SimulationConfig, **kw) -> SimulationConfig:
    return s.model_copy(
        update={"supply": s.supply.model_copy(update={"car": s.supply.car.model_copy(update=kw)})}
    )


def con_bike(s: SimulationConfig, **kw) -> SimulationConfig:
    return s.model_copy(
        update={"supply": s.supply.model_copy(update={"bike": s.supply.bike.model_copy(update=kw)})}
    )


def con_train(s: SimulationConfig, **kw) -> SimulationConfig:
    return s.model_copy(
        update={
            "supply": s.supply.model_copy(update={"train": s.supply.train.model_copy(update=kw)})
        }
    )


def elasticidad(valor_base: float, aplicar, modo: str) -> tuple[float, float, float]:
    """Elasticidad arco de `modo` respecto de un parametro, con +-PCT."""
    lo, hi = valor_base * (1 - PCT), valor_base * (1 + PCT)
    q_lo = corre(aplicar(base_sim(), lo))[modo]
    q_hi = corre(aplicar(base_sim(), hi))[modo]
    q_med, p_med = (q_lo + q_hi) / 2, (lo + hi) / 2
    if q_med == 0 or p_med == 0:
        return 0.0, q_lo, q_hi
    return ((q_hi - q_lo) / q_med) / ((hi - lo) / p_med), q_lo, q_hi


def bloque_elasticidades() -> None:
    print("\n### 1. Elasticidades arco del reparto modal (+-20% sobre el default)")
    print(f"{'parametro':<26} {'modo':<9} {'-20%':>8} {'+20%':>8} {'elasticidad':>12}")
    print("-" * 68)

    # Los valores base se LEEN del config: fijarlos a mano hace que el barrido
    # mida alrededor de un punto que ya no es el default (paso al recalibrar el
    # parking de 6000 a 2500, y la fila siguio reportando la elasticidad vieja).
    s0 = base_sim()
    g0, c0, b0, t0 = s0.demand.globales, s0.supply.car, s0.supply.bike, s0.supply.train

    casos = [
        ("costo_parking", g0.costo_parking, lambda s, v: con_glob(s, costo_parking=v), "Auto"),
        (
            "costo_combustible_km",
            g0.costo_combustible_km,
            lambda s, v: con_glob(s, costo_combustible_km=v),
            "Auto",
        ),
        (
            "costo_tarifa_metro",
            g0.costo_tarifa_metro,
            lambda s, v: con_glob(s, costo_tarifa_metro=v),
            "Metro",
        ),
        (
            "costo_tarifa_metro (cruz.)",
            g0.costo_tarifa_metro,
            lambda s, v: con_glob(s, costo_tarifa_metro=v),
            "Auto",
        ),
        (
            "num_pistas",
            float(c0.num_pistas),
            lambda s, v: con_car(s, num_pistas=max(1, round(v))),
            "Auto",
        ),
        ("v_max_kmh", c0.v_max_kmh, lambda s, v: con_car(s, v_max_kmh=v), "Auto"),
        (
            "capacidad_pista bici",
            float(b0.capacidad_pista),
            lambda s, v: con_bike(s, capacidad_pista=round(v)),
            "Bici",
        ),
        (
            "num_estaciones",
            float(t0.num_estaciones),
            lambda s, v: con_train(s, num_estaciones=round(v)),
            "Metro",
        ),
    ]
    for nombre, base, aplicar, modo in casos:
        e, q_lo, q_hi = elasticidad(base, aplicar, modo)
        print(f"{nombre:<26} {modo:<9} {q_lo:>8.2f} {q_hi:>8.2f} {e:>+12.3f}")

    print("\n  NOTA: `num_pistas` se redondea (1.6->2, 2.4->2), asi que su fila mide")
    print("  el efecto de 2 vs 2 pistas = 0 por construccion. Ver el barrido discreto.")


def bloque_pistas_discreto() -> None:
    print("\n### 1b. Oferta vial en pasos ENTEROS (la elasticidad arco no aplica)")
    print(f"{'pistas':<10} {'auto%':>8} {'metro%':>8} {'v/c':>8} {'t_auto':>8}")
    print("-" * 46)
    for n in (1, 2, 3, 4, 6):
        r = corre(con_car(base_sim(), num_pistas=n))
        print(f"{n:<10} {r['Auto']:>8.2f} {r['Metro']:>8.2f} {r['vc']:>8.2f} {r['t_auto']:>8.1f}")


def bloque_bici() -> None:
    s = base_sim()
    v_bici = s.supply.bike.v_media_kmh
    v_walk = s.demand.globales.v_caminata
    a, b = s.supply.bike.alpha_bpr, s.supply.bike.beta_bpr
    umbral = ((v_bici / v_walk - 1) / a) ** (1 / b)

    print("\n### 2. Bici: donde muerde el techo de caminata")
    print(f"  v_bici={v_bici} km/h · v_caminata={v_walk} km/h · alpha={a} · beta={b}")
    print(f"  => el techo se activa sobre v/c = {umbral:.2f}")
    print("     (sobre ese punto la BPR deja de operar: alpha/beta dejan de mover el tiempo)")
    print(f"\n{'cap_bici':<12} {'bici%':>8} {'v/c':>8} {'t_bici':>9} {'techo?':>8}")
    print("-" * 50)
    for cap in (800, 1500, 2500, 4000, 6000):
        sim = con_bike(base_sim(), capacidad_pista=cap)
        tr_vc = _vc_bici(sim)
        r = corre(sim)
        print(
            f"{cap:<12} {r['Bici']:>8.2f} {tr_vc:>8.2f} {r['t_bici']:>9.1f} "
            f"{'SI' if tr_vc > umbral else 'no':>8}"
        )


def _vc_bici(sim: SimulationConfig) -> float:
    from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo

    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, base_lu(), tr, localizacion="equilibrio"):
        pass
    if tr.flujos_bici_veh_h is None:
        return 0.0
    return float(tr.flujos_bici_veh_h.max()) / sim.supply.bike.capacidad_pista


def bloque_tren() -> None:
    print("\n### 3. Tren: capacidad sola vs capacidad + frecuencia")
    print("  `capacidad_tren` es el DIVISOR de la frecuencia (f = carga/K).")
    print(f"\n{'escenario':<28} {'metro%':>8} {'f_op':>8} {'frec_max':>9} {'auto%':>8}")
    print("-" * 64)

    base = base_sim()
    k0, fmax0 = base.supply.train.capacidad_tren, base.supply.train.frec_max

    for k in (100, 300, 600, 1000):
        r = corre(con_train(base_sim(), capacidad_tren=k))
        etiqueta = f"solo K={k}"
        print(
            f"{etiqueta:<28} {r['Metro']:>8.2f} {r['f_op']:>8.1f} {fmax0:>9.0f} {r['Auto']:>8.2f}"
        )

    print()
    for mult in (1, 2, 3):
        k, fmax = k0 * mult, fmax0 * mult
        r = corre(con_train(base_sim(), capacidad_tren=k, frec_max=fmax))
        etiqueta = f"K={k} y frec_max={fmax:.0f}"
        print(f"{etiqueta:<28} {r['Metro']:>8.2f} {r['f_op']:>8.1f} {fmax:>9.0f} {r['Auto']:>8.2f}")


def main() -> None:
    print("DIAGNOSTICO DE TRANSPORTE — elasticidades, bici y tren")
    print("Base: 201 celdas · 20 km · SumaH=36.000 · expected · seed 42 · tol 0.1")
    bloque_elasticidades()
    bloque_pistas_discreto()
    bloque_bici()
    bloque_tren()


if __name__ == "__main__":
    main()
