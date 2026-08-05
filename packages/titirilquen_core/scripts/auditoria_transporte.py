"""Auditoría de sensibilidad del módulo de TRANSPORTE.

Barre cada parámetro de `SimulationConfig` por la MISMA ruta que usa la app
(`iter_msa_desde_suelo`) y reporta dirección y magnitud del efecto, para
verificar que el modelo responde como la teoría predice.

Correr desde packages/titirilquen_core:

    uv run python scripts/auditoria_transporte.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sensibilidad import _demanda_ui

from titirilquen_core.config import CityConfig, SimulationConfig, SupplyConfig
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.config import LandUseConfig

SUMA_H = 36000
# 20/50/30, en sync con `defaults.ts::defaultLandUseConfig.H_por_estrato` (la
# poblacion que ve la app). OJO: quedo atras en la recalibracion de la mezcla
# (ago-2026) y las auditorias midieron 10/40/50 un buen rato sin avisar — las
# lineas base reportadas en esos commits son de la ciudad ANTIGUA.
H = (int(SUMA_H * 0.20), int(SUMA_H * 0.50), int(SUMA_H * 0.30))


def base_sim() -> SimulationConfig:
    return SimulationConfig(
        city=CityConfig(n_celdas=201, largo_ciudad_km=20, densidad_hab_km=1800),
        supply=SupplyConfig(),
        demand=_demanda_ui(),
        max_iter=20,
        tolerance=0.1,
        seed=42,
        assignment="expected",
    )


def base_lu() -> LandUseConfig:
    return LandUseConfig(H_por_estrato=H, forma="normal", oferta_sigma_frac=0.5)


def corre(sim: SimulationConfig, lu: LandUseConfig | None = None) -> dict:
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu or base_lu(), tr, localizacion="equilibrio"):
        pass
    last = tr.iteraciones[-1]
    total = sum(last.modal_split.values()) or 1
    pct = {
        m: 100 * last.modal_split.get(m, 0) / total
        for m in ("Auto", "Metro", "Bici", "Caminata", "Teletrabajo")
    }
    vc_auto = (
        float(tr.flujos_auto_veh_h.max()) / tr.capacidad_auto
        if tr.flujos_auto_veh_h is not None and tr.capacidad_auto
        else 0.0
    )
    return {
        **pct,
        "vc": vc_auto,
        "t_auto": float(last.t_auto.max()),
        "t_bici": float(last.t_bici.max()),
        "f_op": last.frecuencia_metro,
        "co2": tr.emisiones_total_kg,
        "iters": len(tr.iteraciones),
        "conv": tr.converged,
    }


def encabezado(titulo: str) -> None:
    print(f"\n### {titulo}")
    print(
        f"{'escenario':<24} {'auto':>6} {'metro':>6} {'bici':>6} {'camin':>6} "
        f"{'tele':>6} {'v/c':>5} {'t_auto':>7} {'f_op':>6} {'CO2':>7} {'it':>3}"
    )
    print("-" * 100)


def fila(etiqueta: str, r: dict) -> None:
    print(
        f"{etiqueta:<24} {r['Auto']:>6.2f} {r['Metro']:>6.2f} {r['Bici']:>6.2f} "
        f"{r['Caminata']:>6.2f} {r['Teletrabajo']:>6.2f} {r['vc']:>5.2f} "
        f"{r['t_auto']:>7.1f} {r['f_op']:>6.1f} {r['co2']:>7.0f} {r['iters']:>3}"
        f"{'' if r['conv'] else '  SIN CONVERGER'}"
    )


def barrer(titulo: str, casos) -> None:
    encabezado(titulo)
    for etiqueta, sim, lu in casos:
        try:
            fila(etiqueta, corre(sim, lu))
        except Exception as e:
            print(f"{etiqueta:<24} ERROR {type(e).__name__}: {e}")


def _valida(modelo, kw: dict) -> dict:
    """`model_copy(update=...)` de Pydantic NO valida: una clave inexistente se
    cuela como atributo suelto y el barrido reporta «inerte» un parametro que en
    realidad no se esta moviendo. Paso de verdad dos veces (el `solver` de suelo
    y `factor_emision_auto` tras renombrarlo a `factor_flota_auto`)."""
    desconocidas = set(kw) - set(type(modelo).model_fields)
    if desconocidas:
        raise ValueError(f"no son campos de {type(modelo).__name__}: {sorted(desconocidas)}")
    return kw


def con_car(**kw):
    s = base_sim()
    return s.model_copy(
        update={
            "supply": s.supply.model_copy(
                update={"car": s.supply.car.model_copy(update=_valida(s.supply.car, kw))}
            )
        }
    ), None


def con_bike(**kw):
    s = base_sim()
    return s.model_copy(
        update={
            "supply": s.supply.model_copy(
                update={"bike": s.supply.bike.model_copy(update=_valida(s.supply.bike, kw))}
            )
        }
    ), None


def con_train(**kw):
    s = base_sim()
    return s.model_copy(
        update={
            "supply": s.supply.model_copy(
                update={"train": s.supply.train.model_copy(update=_valida(s.supply.train, kw))}
            )
        }
    ), None


def con_glob(**kw):
    s = base_sim()
    return s.model_copy(
        update={
            "demand": s.demand.model_copy(
                update={
                    "globales": s.demand.globales.model_copy(update=_valida(s.demand.globales, kw))
                }
            )
        }
    ), None


def con_city(**kw):
    s = base_sim()
    return s.model_copy(update={"city": s.city.model_copy(update=_valida(s.city, kw))}), None


def con_raiz(**kw):
    return base_sim().model_copy(update=kw), None


def main() -> None:
    print("AUDITORÍA — MÓDULO DE TRANSPORTE")
    print(f"Base: 201 celdas · 20 km · ΣH={SUMA_H} · expected · seed 42 · tol 0.1")

    b = base_sim()
    barrer("0. baseline", [("default", b, None)])

    barrer(
        "1. OFERTA AUTO",
        [(f"v_max {v}", *con_car(v_max_kmh=v)) for v in (15, 31, 50, 80)]
        + [(f"pistas {n}", *con_car(num_pistas=n)) for n in (1, 2, 4, 6)]
        + [(f"ancho {a}", *con_car(ancho_pista_m=a)) for a in (2.5, 3.0, 3.5, 4.0)]
        + [(f"alpha_bpr {a}", *con_car(alpha_bpr=a)) for a in (0.0, 0.8, 3.0)]
        + [(f"beta_bpr {a}", *con_car(beta_bpr=a)) for a in (1.0, 2.0, 5.0)]
        + [(f"cap_pista {c}", *con_car(capacidad_pista=c)) for c in (600, 1107, 2500)],
    )

    barrer(
        "2. OFERTA BICI",
        [(f"v_media {v}", *con_bike(v_media_kmh=v)) for v in (8, 14, 25)]
        + [(f"capacidad {c}", *con_bike(capacidad_pista=c)) for c in (400, 800, 2500, 6000)]
        + [(f"alpha_bpr {a}", *con_bike(alpha_bpr=a)) for a in (0.0, 0.5, 3.0)]
        + [(f"beta_bpr {a}", *con_bike(beta_bpr=a)) for a in (1.0, 2.0, 5.0)],
    )

    barrer(
        "3. OFERTA METRO",
        [(f"estaciones {n}", *con_train(num_estaciones=n)) for n in (3, 10, 20, 30)]
        + [(f"v_tren {v}", *con_train(v_tren_kmh=v)) for v in (15, 35, 70)]
        + [(f"cap_tren {c}", *con_train(capacidad_tren=c)) for c in (100, 300, 1000)]
        + [(f"frec_min {f}", *con_train(frec_min=f)) for f in (2, 6, 15)]
        + [(f"frec_max {f}", *con_train(frec_max=f)) for f in (10, 30, 60)]
        + [(f"anden_alpha {a}", *con_train(anden_alpha=a)) for a in (0.0, 0.5, 3.0)]
        + [(f"anden_beta {a}", *con_train(anden_beta=a)) for a in (1.0, 4.0, 8.0)]
        + [(f"tasa_carga {c}", *con_train(tasa_carga=c)) for c in (6, 100)],
    )

    barrer(
        "4. ECONOMÍA / GLOBALES",
        [(f"parking {p}", *con_glob(costo_parking=p)) for p in (0, 3000, 6000, 15000, 30000)]
        + [(f"bencina {c}", *con_glob(costo_combustible_km=c)) for c in (50, 120, 300)]
        + [(f"tarifa {t}", *con_glob(costo_tarifa_metro=t)) for t in (0, 800, 2000)]
        + [(f"v_caminata {v}", *con_glob(v_caminata=v)) for v in (3.5, 4.8, 7.0)]
        + [(f"v_auto glob {v}", *con_glob(v_auto=v)) for v in (31, 80)]
        + [(f"factor_flota {f}", *con_glob(factor_flota_auto=f)) for f in (0.15, 1.0, 2.0)]
        + [(f"em_metro {f}", *con_glob(factor_emision_metro_tren_km=f)) for f in (2.5, 10.0)],
    )

    barrer(
        "5. CIUDAD",
        [(f"largo {k}", *con_city(largo_ciudad_km=k)) for k in (8, 20, 40)]
        + [(f"celdas {n}", *con_city(n_celdas=n)) for n in (51, 201, 501)]
        + [(f"pendiente {p}", *con_city(pendiente_porcentaje=p)) for p in (-8, 0, 8)]
        + [(f"tele_factor {f}", *con_city(teletrabajo_factor=f)) for f in (0, 1, 2)]
        + [(f"densidad {d}", *con_city(densidad_hab_km=d)) for d in (500, 1800, 5000)],
    )

    barrer(
        "6. EQUILIBRIO / RAÍZ",
        [(f"max_iter {n}", *con_raiz(max_iter=n)) for n in (3, 20, 50)]
        + [(f"tolerance {t}", *con_raiz(tolerance=t)) for t in (0.0, 0.1, 1.0)]
        + [
            ("assignment montecarlo", *con_raiz(assignment="montecarlo")),
            ("modos sin bici", *con_raiz(modos_habilitados=["Auto", "Metro", "Caminata"])),
            ("modos sin auto", *con_raiz(modos_habilitados=["Metro", "Bici", "Caminata"])),
        ],
    )

    barrer(
        "7. ESCALA DE POBLACIÓN (ΣH del suelo)",
        [
            (
                f"ΣH={n}",
                base_sim(),
                LandUseConfig(
                    H_por_estrato=(int(n * 0.1), int(n * 0.4), int(n * 0.5)),
                    forma="normal",
                    oferta_sigma_frac=0.5,
                ),
            )
            for n in (9000, 36000, 72000)
        ],
    )


if __name__ == "__main__":
    main()
